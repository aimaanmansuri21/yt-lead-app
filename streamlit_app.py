import streamlit as st
import pandas as pd
import datetime
import re
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe
from googleapiclient.discovery import build
from langdetect import detect, DetectorFactory
DetectorFactory.seed = 0  # for consistent language detection results

# Load API key from secrets
API_KEY = st.secrets["API_KEY"]

# Load Google credentials from secrets
gspread_secrets = st.secrets["gspread"]
credentials = Credentials.from_service_account_info(gspread_secrets, scopes=[
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
])
client = gspread.authorize(credentials)

# App title
st.title("📺 YouTube Lead Finder")

# Sidebar filters
query = st.text_input("🔍 Keywords (comma separated, e.g. make money, coaching)", value="make money online, side hustle")
min_subs = st.number_input("📉 Min Subscribers", value=5000)
max_subs = st.number_input("📈 Max Subscribers", value=70000)
active_days = st.number_input("📅 Only Channels Active in Last __ Days", value=30)

# New Filters
creation_date_from = st.date_input("📆 Channel Created After", value=datetime.date(2018,1,1))
creation_date_to = st.date_input("📆 Channel Created Before", value=datetime.date.today())

languages = st.multiselect("🌐 Channel Language(s) (detected)", options=['en', 'es', 'fr', 'de', 'it', 'pt', 'ru', 'zh-cn', 'ja'], default=['en'])

niches = st.multiselect("📚 Niche(s)", options=[k.strip() for k in query.split(",")], default=[k.strip() for k in query.split(",")])

monetization_filter = st.checkbox("💰 Only Channels Likely Monetized (mentions sponsor, merch, patreon, etc.)")

sheet_name = st.text_input("📄 Google Sheet Name", value="YT Leads")

# Helper functions
def extract_instagram(text):
    match = re.search(r"(https?://)?(www\.)?instagram\.com/([a-zA-Z0-9_.]+)", text)
    return f"https://instagram.com/{match.group(3)}" if match else "None"

def extract_emails(text):
    return ", ".join(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text))

def get_upload_date(channel_id, youtube):
    uploads_playlist = youtube.channels().list(
        part="contentDetails", id=channel_id).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    videos = youtube.playlistItems().list(
        part="contentDetails", playlistId=uploads_playlist, maxResults=1).execute()
    if not videos["items"]:
        return None
    date_str = videos["items"][0]["contentDetails"]["videoPublishedAt"]
    return datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))

def detect_language(text):
    try:
        return detect(text)
    except:
        return "unknown"

def check_monetization(desc):
    keywords = ["sponsor", "merch", "patreon", "donate", "membership", "affiliate"]
    desc_lower = desc.lower()
    return any(k in desc_lower for k in keywords)

# Button
if st.button("🚀 Run Lead Search"):
    st.info("Scraping YouTube... Please wait...")

    youtube = build("youtube", "v3", developerKey=API_KEY)
    keywords = niches  # use niche filter keywords
    all_data = []

    for keyword in keywords:
        search_response = youtube.search().list(
            q=keyword,
            type="channel",
            part="snippet",
            maxResults=30
        ).execute()

        channel_ids = [item['snippet']['channelId'] for item in search_response['items']]

        details = youtube.channels().list(
            part="snippet,statistics",
            id=",".join(channel_ids)
        ).execute()

        for item in details['items']:
            subs = int(item['statistics'].get('subscriberCount', 0))
            if not (min_subs <= subs <= max_subs):
                continue

            # Channel creation date filter
            created_at = datetime.datetime.fromisoformat(item['snippet']['publishedAt'][:-1]).date()
            if not (creation_date_from <= created_at <= creation_date_to):
                continue

            last_upload = get_upload_date(item["id"], youtube)
            if not last_upload or (datetime.datetime.now(datetime.timezone.utc) - last_upload).days > active_days:
                continue

            desc = item['snippet']['description']

            # Language detection filter
            lang = detect_language(item['snippet']['title'] + " " + desc)
            if lang not in languages:
                continue

            # Monetization filter
            if monetization_filter and not check_monetization(desc):
                continue

            insta = extract_instagram(desc)
            emails = extract_emails(desc)

            all_data.append({
                "Channel Name": item["snippet"]["title"],
                "Channel URL": f"https://youtube.com/channel/{item['id']}",
                "Subscribers": subs,
                "Total Videos": item["statistics"].get("videoCount"),
                "Last Upload": last_upload.date(),
                "Channel Created": created_at,
                "Language": lang,
                "Instagram": insta,
                "Email": emails,
                "Status": ""
            })

    df = pd.DataFrame(all_data)

    if df.empty:
        st.warning("No leads found. Try changing your filters.")
    else:
        st.success(f"✅ Found {len(df)} leads")
        st.dataframe(df)

        # Send to Google Sheet
        sheet = client.open(sheet_name)
        ws = sheet.sheet1
        ws.clear()
        set_with_dataframe(ws, df)

        st.success("📤 Sent to Google Sheet successfully!")
