import streamlit as st
import pandas as pd
import datetime
import re
import random
import gspread
import openai
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe
from googleapiclient.discovery import build
from Niche_Keyword_Dictionary_FIXED import niche_keywords

# --- OpenAI Key ---
openai.api_key = st.secrets["OPENAI_API_KEY"]

# --- Trait Extraction Function ---
def extract_traits_from_bio(bio):
    if not bio or len(bio.strip()) < 20:
        st.text("⚠️ Skipping trait extraction: bio too short or missing.")
        return "No bio / too short"

    prompt = f"""
You are an expert at analyzing YouTube channel bios. Based on the bio below, list 5 personality or content traits this creator likely has.

Bio:
{bio}

Return traits in a Python list format, like: ["trait1", "trait2", "trait3", "trait4", "trait5"]
"""
    st.text("🔍 Sending to OpenAI...")

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        traits_raw = response["choices"][0]["message"]["content"]
        st.text(f"✅ Raw traits: {traits_raw}")

        match = re.findall(r'"(.*?)"', traits_raw)
        if not match:
            raise ValueError(f"No valid traits found. Raw output: {traits_raw}")

        traits_cleaned = [trait.strip().capitalize() for trait in match if len(trait.strip()) > 1]
        return ", ".join(traits_cleaned[:5])
    except Exception as e:
        st.warning(f"⚠️ OpenAI error: {e}")
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
        .stButton>button span {
            font-size: 1.5rem;
            line-height: 1;
        }
        .block-container {
            padding: 2rem 3rem;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <h1 style='font-size: 2.8rem; font-weight: 600;'>📺 YouTube Lead Generator</h1>
    <p style='font-size: 1.1rem; color: #444;'>Find and organize high-potential creators in seconds.</p>
""", unsafe_allow_html=True)

# --- Keyword Input ---
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
        if st.button("🎲", key="randomize_btn"):
            niche = random.choice(list(niche_keywords.keys()))
            keywords = random.sample(niche_keywords[niche], min(5, len(niche_keywords[niche])))
            st.session_state["keyword_input"] = ", ".join(keywords)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# --- Filters ---
st.markdown("### Filters")
col3, col4, col5 = st.columns(3)
with col3:
    min_subs = st.number_input("Min Subscribers", value=5000)
with col4:
    max_subs = st.number_input("Max Subscribers", value=65000)
with col5:
    active_years = st.number_input("Only Channels Active in Last Years", value=2)

# --- Search Button ---
run_button = st.button("Search YouTube for Leads")
