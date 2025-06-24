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

# --- Custom CSS for Clean Red-White UI ---
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
            font-size: 1rem;
            font-weight: 600;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            transition: background-color 0.3s ease;
        }
        .stButton>button:hover {
            background-color: #cc0000;
        }
        .stTextInput>div>div>input {
            border-radius: 8px;
            padding: 1em 1.2em;
            font-size: 1.1rem;
            line-height: 1.6;
            border: 1px solid #ccc;
            height: auto;
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

# --- Keyword Input Section ---
st.markdown("### Keywords")

if "keyword_input" not in st.session_state:
    st.session_state["keyword_input"] = ""

col1, col2 = st.columns([4, 1])
with col1:
    query_value = st.text_input("Enter up to 5 keywords (comma-separated)", value=st.session_state["keyword_input"], key="keyword_input_textbox")
    st.session_state["keyword_input"] = query_value

with col2:
    if st.button("🎲 Randomize"):
        random_niche = random.choice(list(niche_keywords.keys()))
        if len(niche_keywords[random_niche]) >= 5:
            selected_keywords = random.sample(niche_keywords[random_niche], 5)
        else:
            selected_keywords = niche_keywords[random_niche]
        st.session_state["keyword_input"] = ", ".join(selected_keywords)
        st.rerun()

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

# (rest of the code continues unchanged)

# Keep all logic below untouched as it was already working correctly.
