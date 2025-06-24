import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe
import pandas as pd
import openai
import time
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- Load secrets ---
# Assumes you store your JSON credentials as a file and API key in Streamlit secrets
SERVICE_ACCOUNT_INFO = st.secrets["gcp_service_account"]
OPENAI_API_KEY = st.secrets["openai_api_key"]

# --- Google Sheets setup ---
scopes = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

credentials = Credentials.from_service_account_info(
    SERVICE_ACCOUNT_INFO, scopes=scopes
)
gc = gspread.authorize(credentials)

# Open your Google Sheet by name
sheet = gc.open("ColabSheetAccess").sheet1

# Load data into pandas DataFrame
data = sheet.get_all_records()
df = pd.DataFrame(data)

# --- OpenAI setup ---
openai.api_key = OPENAI_API_KEY

def generate_email(channel_name, subscribers, bio):
    prompt = f"""
You are a professional video editor with 2 billion+ YouTube views and 4+ years of experience.

Write a simple, friendly outreach email greeting the person by their channel name:

Hey {channel_name},

[Give a genuine compliment about their channel based on this bio: "{bio}"]

Introduce yourself briefly as Aimaan, a video editor.

Offer to edit their first video for free — no catch.

End with a polite closing: "Thanks, Aimaan"

Keep it casual, not salesy or pushy.  
Make it sound natural and personal.

Do NOT include a subject line or signature.
"""
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )
    return response['choices'][0]['message']['content']

def generate_subject(channel_name):
    subjects = [
        f"Hey {channel_name}, quick question",
        f"Loved your channel, {channel_name}",
        f"A quick note for {channel_name}",
        f"Thought you might like this",
        f"Hello {channel_name}!"
    ]
    return random.choice(subjects)

# Gmail sending setup
your_email = "aimaanmansuri2@gmail.com"
your_app_password = "itrl catl mepc iyqs"

def send_email(to_email, subject, body):
    msg = MIMEMultipart("alternative")
    msg["From"] = your_email
    msg["To"] = to_email
    msg["Subject"] = subject

    # Compose HTML email
    html = f"<html><body><p>{body.replace(chr(10), '<br>')}</p></body></html>"
    part = MIMEText(html, "html")
    msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(your_email, your_app_password)
        server.send_message(msg)

# --- Streamlit UI ---

st.title("YouTube Outreach Automation")

if st.button("Send Emails to Unsent Leads"):
    if 'email_sent' not in df.columns:
        df['email_sent'] = ""

    email_signature = """
<br><br>Regards,<br>
Aimaan | Video Editor & Content Curator<br>
<a href='https://aimaanedits.com'>www.aimaanedits.com</a><br>
<a href='https://instagram.com/aimaanedits'>www.instagram.com/aimaanedits</a>
"""

    progress_text = st.empty()
    for i, row in df.iterrows():
        if str(row['email_sent']).strip().lower() == 'yes':
            progress_text.text(f"⏩ Skipping {row['channel_name']} (already emailed)")
            continue

        email = row.get('email', '').strip()
        if not email or '@' not in email:
            progress_text.text(f"⚠️ Skipping {row['channel_name']} due to missing/invalid email")
            continue

        try:
            channel_name = row['channel_name']
            subject = generate_subject(channel_name)
            email_body = generate_email(channel_name, row['subscribers'], row['about_us'])
            email_body += email_signature

            send_email(email, subject, email_body)

            df.at[i, 'email_sent'] = 'Yes'
            progress_text.text(f"✅ Email sent to {email}")

            time.sleep(random.uniform(5, 15))
        except Exception as e:
            progress_text.text(f"❌ Error with {row['channel_name']}: {e}")

    set_with_dataframe(sheet, df)
    st.success("🎉 All leads have been processed and Google Sheet updated!")
