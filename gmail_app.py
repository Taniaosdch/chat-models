import streamlit as st
import base64
import email
from email import policy
from bs4 import BeautifulSoup
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import re

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

st.title("📬 Gmail Unsubscriber")
st.write("This app scans your inbox and shows unsubscribe links from recent emails.")

num_messages = st.slider("Number of emails to scan", min_value=5, max_value=100, value=20)

if st.button("🔍 Scan Gmail"):

    with st.spinner("Authenticating with Gmail..."):
        flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
        creds = flow.run_local_server(port=8080)
        service = build("gmail", "v1", credentials=creds)

    with st.spinner("Fetching and analyzing emails..."):
        results = service.users().messages().list(userId="me", maxResults=num_messages).execute()
        messages = results.get("messages", [])

        unsub_links = []

        for msg in messages:
            try:
                msg_data = service.users().messages().get(userId="me", id=msg["id"], format="raw").execute()
                raw_msg = base64.urlsafe_b64decode(msg_data["raw"].encode("ASCII"))
                msg_obj = email.message_from_bytes(raw_msg, policy=policy.default)

                subject = msg_obj["Subject"] or "(No Subject)"
                list_unsub = msg_obj.get("List-Unsubscribe")

                # Extract from headers
                if list_unsub:
                    links = re.findall(r'<(http[^>]+)>', list_unsub)
                    for link in links:
                        unsub_links.append((subject, link))
                    continue

                # Otherwise try from HTML body
                for part in msg_obj.walk():
                    if part.get_content_type() == "text/html":
                        html = part.get_content()
                        soup = BeautifulSoup(html, "html.parser")
                        a_tags = soup.find_all("a", string=re.compile("unsubscribe", re.I))
                        for tag in a_tags:
                            link = tag.get("href")
                            if link:
                                unsub_links.append((subject, link))
                        break
            except Exception as e:
                print(f"Error reading email: {e}")

    if unsub_links:
        st.success(f"Found {len(unsub_links)} unsubscribe links!")
        for subject, link in unsub_links:
            st.markdown(f"**📌 {subject}** – [Unsubscribe]({link})", unsafe_allow_html=True)
    else:
        st.warning("No unsubscribe links found in these emails.")
