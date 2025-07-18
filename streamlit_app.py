#cell 1
import streamlit as st
import pandas as pd
import datetime
import re
import ast
import gspread
import random
import openai
from openai import OpenAI
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe
from googleapiclient.discovery import build

# --- OpenAI Client ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Trait Extraction Function ---
def extract_traits_from_bio(bio):
    if not bio or len(bio.strip()) < 20:
        return "No bio / too short"

    prompt = f"""
You are an expert at analyzing YouTube channel bios. Based on the bio below, identify 5 descriptive personality or content traits this creator likely has. Traits should be specific, multi-word if helpful, and reflect tone, intent, or style — not just generic adjectives.

Bio:
{bio}

Return traits in a Python list format, like: ["trait1", "trait2", "trait3", "trait4", "trait5"]
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        traits_raw = response.choices[0].message.content
        match = re.findall(r'"(.*?)"', traits_raw)
        if not match:
            raise ValueError(f"No valid traits found. Raw output: {traits_raw}")
        traits_cleaned = [trait.strip().capitalize() for trait in match if len(trait.strip()) > 1]
        return ", ".join(traits_cleaned[:5])
    except Exception as e:
        return "Could not extract traits"

# --- UI Styling ---
st.markdown("""
    <style>
        html, body, [class*='css'] {
            background-color: #ffffff !important;
            color: #000000;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
        }
        .stButton>button {
            background-color: #ff0000;
            color: white;
            padding: 0.75em 2em;
            font-size: 1rem;
            font-weight: 600;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: background-color 0.3s ease;
            line-height: 1.2;
            display: flex;
            align-items: center;
            justify-content: center;
            white-space: nowrap;
        }
        .stButton>button:hover {
            background-color: #cc0000;
        }
        .block-container {
            padding: 2rem 3rem;
        }
        .stNumberInput>div>input {
            text-align: center;
        }
        label[for^='number_input_'] {
            display: block;
            text-align: center;
            margin-top: 0.25rem;
            font-weight: 500;
            font-size: 0.9rem;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <h1 style='font-size: 2.8rem; font-weight: 600;'>📺 YouTube Lead Generator</h1>
    <p style='font-size: 1.1rem; color: #444;'>Find and organize high-potential creators in seconds.</p>
""", unsafe_allow_html=True)

if "keyword_input" not in st.session_state:
    st.session_state["keyword_input"] = ""

with st.container():
    col1, col2 = st.columns([5, 1], gap="medium")
    with col1:
        st.session_state["keyword_input"] = st.text_area(
            "Enter up to 5 keywords (comma-separated)",
            value=st.session_state["keyword_input"],
            key="keyword_input_textbox",
            height=100
        )
    with col2:
        st.markdown("<div style='padding-top: 32px;'>", unsafe_allow_html=True)

        preset_niches = [
            "Tech Reviews", "Mobile App Tutorials", "Smartphone Comparisons", "Personal Finance", "Cryptocurrency & Blockchain",
            "Real Estate Walkthroughs", "Fitness at Home", "Weight Loss Journeys", "Healthy Meal Prep", "Fashion for Men",
            "Streetwear Styling", "Beauty Tutorials", "Skincare Routines", "Minimalist Living", "Home Decor Ideas",
            "Interior Design", "DIY & Crafts", "Productivity Tips", "Study With Me / Pomodoro", "Self-Improvement",
            "Motivation & Mindset", "Book Summaries", "Gaming Walkthroughs", "Live Gaming Commentary", "Esports News",
            "Comedy Sketches", "Reaction Videos", "Try Not To Laugh Challenges", "Unboxing Videos", "Product Reviews",
            "Parenting Tips", "Kids Educational Content", "Toy Reviews", "Educational Animations", "History Explained",
            "Science Experiments", "True Crime Stories", "Storytelling with Animation", "Horror Short Films", "Vlogs",
            "Travel Hacks & Destinations", "Van Life / Tiny Home", "Car Reviews", "Supercar Spotting", "Podcast Clips",
            "Interview Highlights", "AI Tools & Automation", "Software Tutorials", "Small Business Marketing", "Freelancing & Side Hustles"
        ]

        if st.button("🎲", key="randomize_btn"):
            try:
                chosen_niche = random.choice(preset_niches)
                prompt = f"""
You are a YouTube SEO expert. Give me 5 realistic, high-search, and clickable YouTube keyword phrases that creators in the niche \"{chosen_niche}\" are using right now.

Instructions:
- The keywords must be things people would actually search for or use as video titles
- Avoid made-up, vague, or overly generic terms
- Prioritize high engagement and relevance

Return the list in Python format like:
["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
"""
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                text = response.choices[0].message.content
                keywords = ast.literal_eval(re.search(r"\[(.*?)\]", text, re.DOTALL).group(0))
                st.session_state["keyword_input"] = ", ".join(keywords)
                st.toast(f"🎯 Niche: {chosen_niche}")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to generate keywords: {e}")
        st.markdown("</div>", unsafe_allow_html=True)

# --- Lead Filtering UI ---
col3, col4, col5 = st.columns(3)
with col3:
    min_subs = st.number_input("Min Subscribers", value=5000)
with col4:
    max_subs = st.number_input("Max Subscribers", value=65000)
with col5:
    active_years = st.number_input("Only Channels Active in Last Years", value=2)

run_button = st.button("Search YouTube for Leads")

if run_button:
    query = st.session_state["keyword_input"]
    if not query.strip():
        st.warning("Please enter at least 1 keyword.")
    else:
        st.info("Scraping YouTube... Please wait...")

        api_keys = st.secrets["API_KEYS"]
        youtube = None
        for key in api_keys:
            try:
                youtube = build("youtube", "v3", developerKey=key)
                break
            except Exception:
                continue

        if not youtube:
            st.error("❌ All API keys have exceeded their quota. Try again tomorrow.")
            st.stop()

        gspread_secrets = st.secrets["gspread"]
        credentials = Credentials.from_service_account_info(gspread_secrets, scopes=[
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ])
        client_gs = gspread.authorize(credentials)
        sheets_api = build("sheets", "v4", credentials=credentials)

        keywords = [k.strip() for k in query.split(",") if k.strip()]
        all_data = []

        def extract_instagram(text):
            match = re.search(r"(https?://)?(www\.)?instagram\.com/([a-zA-Z0-9_.]+)", text)
            return f"https://instagram.com/{match.group(3)}" if match else "None"

        def extract_emails(text):
            return ", ".join(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text))

        def get_upload_date(channel_id):
            try:
                uploads_playlist = youtube.channels().list(
                    part="contentDetails", id=channel_id).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
                videos = youtube.playlistItems().list(
                    part="contentDetails", playlistId=uploads_playlist, maxResults=1).execute()
                if not videos["items"]:
                    return None
                date_str = videos["items"][0]["contentDetails"]["videoPublishedAt"]
                return datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except:
                return None

        for keyword in keywords:
            try:
                search_response = youtube.search().list(
                    q=keyword,
                    type="channel",
                    part="snippet",
                    maxResults=50
                ).execute()
                channel_ids = [item['snippet']['channelId'] for item in search_response['items'] if 'channelId' in item['snippet']]
                if not channel_ids:
                    continue

                details = youtube.channels().list(
                    part="snippet,statistics",
                    id=",".join(channel_ids)
                ).execute()

                for item in details['items']:
                    subs = int(item['statistics'].get('subscriberCount', 0))
                    if not (min_subs <= subs <= max_subs):
                        continue

                    last_upload = get_upload_date(item["id"])
                    if not last_upload or (datetime.datetime.now(datetime.timezone.utc) - last_upload).days > active_years * 365:
                        continue

                    desc = item['snippet']['description']
                    insta = extract_instagram(desc)
                    emails = extract_emails(desc)
                    traits = extract_traits_from_bio(desc)

                    all_data.append({
                        "Channel Name": item["snippet"]["title"],
                        "Channel URL": f"https://youtube.com/channel/{item['id']}",
                        "Subscribers": subs,
                        "Total Videos": item["statistics"].get("videoCount"),
                        "Last Upload": last_upload.date(),
                        "Instagram": insta,
                        "Email": emails,
                        "Traits": traits,
                        "Status": ""
                    })

            except Exception as e:
                st.error(f"Error with keyword '{keyword}': {e}")

        df = pd.DataFrame(all_data)
        df.drop_duplicates(subset="Channel Name", inplace=True)

        if df.empty:
            st.warning("No leads found. Try changing your filters.")
        else:
            st.success(f"✅ Found {len(df)} leads")
            st.dataframe(df)

            try:
                sheet = client_gs.open("YT Leads")
            except gspread.SpreadsheetNotFound:
                sheet = client_gs.create("YT Leads")
                sheet.share(st.secrets["gspread"]["client_email"], perm_type="user", role="writer")

            ws = sheet.sheet1
            ws.clear()
            set_with_dataframe(ws, df)

            checkbox_request = {
                "requests": [{
                    "repeatCell": {
                        "range": {
                            "sheetId": ws._properties['sheetId'],
                            "startRowIndex": 1,
                            "endRowIndex": len(df) + 1,
                            "startColumnIndex": df.columns.get_loc("Status"),
                            "endColumnIndex": df.columns.get_loc("Status") + 1
                        },
                        "cell": {
                            "dataValidation": {
                                "condition": {"type": "BOOLEAN"},
                                "strict": True,
                                "showCustomUi": True
                            }
                        },
                        "fields": "dataValidation"
                    }
                }]
            }

            sheets_api.spreadsheets().batchUpdate(
                spreadsheetId=sheet.id,
                body=checkbox_request
            ).execute()

            st.link_button("📤 Open Google Sheet", f"https://docs.google.com/spreadsheets/d/{sheet.id}")
