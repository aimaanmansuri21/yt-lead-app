import streamlit as st
import pandas as pd
import datetime
import re
import random
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe
from googleapiclient.discovery import build
from Niche_Keyword_Dictionary_FIXED import niche_keywords

# Load API key from secrets
API_KEY = st.secrets["API_KEY"]

# Load Google credentials from secrets
gspread_secrets = st.secrets["gspread"]
credentials = Credentials.from_service_account_info(gspread_secrets, scopes=[
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
])
client = gspread.authorize(credentials)
sheets_api = build("sheets", "v4", credentials=credentials)

# App title
st.title("📺 YOUTUBE LEAD GENERATOR")

# --- Keyword Input Section ---
st.markdown("### 🎯 Keywords")
col1, col2 = st.columns([4, 1])
if "keyword_input" not in st.session_state:
    st.session_state["keyword_input"] = ""

with col1:
    query = st.text_input("Enter up to 5 keywords (comma-separated)", value=st.session_state["keyword_input"], key="keyword_input")
with col2:
    if st.button("🎲 Randomize Keywords", key="random_btn"):
        random_niche = random.choice(list(niche_keywords.keys()))
        selected_keywords = random.sample(niche_keywords[random_niche], 5)
        st.session_state["keyword_input"] = ", ".join(selected_keywords)
        st.rerun()

# --- Filters ---
st.markdown("### 🔍 Filters")
min_subs = st.number_input("Min Subscribers", value=5000)
max_subs = st.number_input("Max Subscribers", value=65000)
active_years = st.number_input("Only Channels Active in Last Years", value=2)

# Button to run
if st.button("🚀 Run Lead Search"):
    if not query.strip():
        st.warning("Please enter at least 1 keyword.")
    else:
        st.info("Scraping YouTube... Please wait...")

        youtube = build("youtube", "v3", developerKey=API_KEY)
        keywords = [k.strip() for k in query.split(",") if k.strip()]
        all_data = []

        def extract_instagram(text):
            match = re.search(r"(https?://)?(www\.)?instagram\.com/([a-zA-Z0-9_.]+)", text)
            return f"https://instagram.com/{match.group(3)}" if match else "None"

        def extract_emails(text):
            return ", ".join(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}", text))

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
                maxResults=50
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

                last_upload = get_upload_date(item["id"])
                if not last_upload or (datetime.datetime.now(datetime.timezone.utc) - last_upload).days > active_years * 365:
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

            # Send to Google Sheet
            sheet = client.open("YT Leads")
            ws = sheet.sheet1
            ws.clear()
            set_with_dataframe(ws, df)

            # Add checkbox formatting
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

            spreadsheet_id = sheet.id
            sheets_api.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body=checkbox_request
            ).execute()

            st.link_button("📤 Open Google Sheet", f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}")
