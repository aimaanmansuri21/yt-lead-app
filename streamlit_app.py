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
            padding: 0.75em 1.5em;
            font-size: 0; /* Hide default text */
            font-weight: 600;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: background-color 0.3s ease;
            line-height: 1;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .stButton>button:hover {
            background-color: #cc0000;
        }
        .stButton>button span.emoji {
            font-size: 2rem; /* Enlarged emoji */
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
        if st.button("<span class='emoji'>🎲</span>", key="randomize_btn"):
            niche = random.choice(list(niche_keywords.keys()))
            keywords = random.sample(niche_keywords[niche], min(5, len(niche_keywords[niche])))
            st.session_state["keyword_input"] = ", ".join(keywords)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

# rest of the code remains unchanged
