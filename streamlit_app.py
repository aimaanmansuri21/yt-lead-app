#cell 1
<everything_above_here_unmodified>

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
