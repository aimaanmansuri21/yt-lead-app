import streamlit as st
import pandas as pd
import datetime
import re
import gspread
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe
from googleapiclient.discovery import build
from google.auth.transport.requests import AuthorizedSession
from langdetect import detect

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
st.title("📺 YouTube Lead Generator")

# Sidebar filters
query = st.text_input("🔍 Keywords (comma separated, max 5)", value="", max_chars=200)
min_subs = st.number_input("📉 Min Subscribers", value=5000)
max_subs = st.number_input("📈 Max Subscribers", value=65000)
active_years = st.number_input("📅 Only Channels Active in Last Years", value=2)

# Button
if st.button("🚀 Run Lead Search"):
    if not query:
        st.error("Please enter at least one keyword.")
    else:
        st.info("Scraping YouTube... Please wait...")

        youtube = build("youtube", "v3", developerKey=API_KEY)
        keywords = [k.strip() for k in query.split(",") if k.strip()][:5]
        all_data = []

        def extract_instagram(text):
            match = re.search(r"(https?://)?(www\.)?instagram\.com/([a-zA-Z0-9_.]+)", text)
            return f"https://instagram.com/{match.group(3)}" if match else "None"

        def extract_emails(text):
            return ", ".join(re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}", text))

        def get_upload_date(channel_id):
    try:
        uploads_playlist = youtube.channels().list(
            part="contentDetails", id=channel_id
        ).execute()["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

        videos = youtube.playlistItems().list(
            part="contentDetails", playlistId=uploads_playlist, maxResults=1
        ).execute()

        if not videos["items"]:
            return None

        date_str = videos["items"][0]["contentDetails"]["videoPublishedAt"]
        return datetime.datetime.fromisoformat(date_str.replace("Z", "+00:00"))

    except Exception as e:
        return None  # skip channel if upload date cannot be retrieved

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
                try:
                    lang = detect(desc)
                except:
                    lang = "unknown"

                if lang != "en":
                    continue

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

            # Format "Status" column as checkboxes
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
            authed_session = AuthorizedSession(credentials)
            authed_session.post(
                f"https://sheets.googleapis.com/v4/spreadsheets/{spreadsheet_id}:batchUpdate",
                json=checkbox_request
            )

            sheet_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
            st.markdown(f"[📄 View Sheet in Google Sheets]({sheet_url})", unsafe_allow_html=True)
