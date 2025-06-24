import streamlit as st
import pandas as pd
import datetime
import re
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe
from googleapiclient.discovery import build

# App title
st.title("📈 YouTube Lead Generator")

# Load API key from secrets
API_KEY = st.secrets["API_KEY"]

# Load Google credentials from secrets
gspread_secrets = st.secrets["gspread"]
credentials = Credentials.from_service_account_info(gspread_secrets, scopes=[
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
])
client = gspread.authorize(credentials)

# Sidebar filters
query = st.text_input("🔍 Enter up to 5 keywords (comma separated)", value="make money online, side hustle")
min_subs = st.number_input("📉 Min Subscribers", value=5000)
max_subs = st.number_input("📈 Max Subscribers", value=65000)
active_years = st.number_input("📆 Only Channels Active in Last X Years", min_value=0, value=2)

# Button
if st.button("🚀 Run Lead Search"):
    keywords = [k.strip() for k in query.split(",") if k.strip()]

    if not (1 <= len(keywords) <= 5):
        st.error("❌ Please enter between 1 and 5 keywords.")
        st.stop()

    st.info("🔍 Scraping YouTube... Please wait...")

    youtube = build("youtube", "v3", developerKey=API_KEY)
    all_data = []

    def extract_instagram(text):
        match = re.search(r"(https?://)?(www\.)?instagram\.com/([a-zA-Z0-9_.]+)", text)
        return f"https://instagram.com/{match.group(3)}" if match else "None"

    def extract_emails(text):
        return ", ".join(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", text))

    def get_upload_date(channel_id):
        uploads_playlist = youtube.channels().list(
            part="contentDetails", id=channel_id).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
        videos = youtube.playlistItems().list(
            part="contentDetails", playlistId=uploads_playlist, maxResults=1).execute()
        if not videos["items"]:
            return None
        date_str = videos["items"][0]["contentDetails"]["videoPublishedAt"]
        return datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))

    for keyword in keywords:
        search_response = youtube.search().list(
            q=keyword,
            type="channel",
            part="snippet",
            maxResults=30
        ).execute()

        channel_ids = [item['snippet']['channelId'] for item in search_response['items']]
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
            if not last_upload or (datetime.datetime.now(datetime.timezone.utc) - last_upload).days > (active_years * 365):
                continue

            desc = item['snippet']['description']
            insta = extract_instagram(desc)
            emails = extract_emails(desc)

            all_data.append({
                "Channel Name": item["snippet"]["title"],
                "Channel URL": f"https://youtube.com/channel/{item['id']}",
                "Subscribers": subs,
                "Total Videos": item["statistics"].get("videoCount"),
                "Last Upload": last_upload.date(),
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

        # Write to Google Sheet (always named YT Leads)
        sheet = client.open("YT Leads")
        ws = sheet.sheet1
        ws.clear()
        set_with_dataframe(ws, df)

        st.success("📤 Leads sent to Google Sheet!")
