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

# --- Custom CSS for YouTube-like Light Theme ---
st.markdown("""
    <style>
        html, body, [class*="css"]  {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Open Sans', 'Helvetica Neue', sans-serif;
            background-color: #ffffff !important;
            color: #000000;
        }
        .stButton>button {
            background-color: #ff0000;
            border: none;
            color: #fff;
            padding: 0.7em 1.5em;
            border-radius: 8px;
            font-weight: 600;
            font-size: 1rem;
            transition: all 0.3s ease;
            white-space: nowrap;
        }
        .stButton>button:hover {
            background-color: #cc0000;
        }
        .stTextInput>div>div>input {
            border-radius: 6px;
            padding: 0.6em;
            font-size: 1rem;
            border: 1px solid #ccc;
        }
        .block-container {
            padding: 2rem 3rem;
        }
    </style>
""", unsafe_allow_html=True)

# --- Title Section ---
st.markdown("""
    <h1 style='font-size: 2.8rem; font-weight: 600;'>📺 YouTube Lead Generator</h1>
    <p style='font-size: 1.1rem; color: #555;'>Find and organize high-potential creators in seconds.</p>
""", unsafe_allow_html=True)

# --- Keyword Input ---
st.markdown("### Keywords")

if "keyword_input" not in st.session_state:
    st.session_state["keyword_input"] = ""

col1, col2 = st.columns([4, 1])
with col2:
    st.markdown("""<div style='display: flex; justify-content: flex-end;'>""", unsafe_allow_html=True)
    if st.button("🎲 Randomize", key="random_btn"):
        random_niche = random.choice(list(niche_keywords.keys()))
        selected_keywords = random.sample(niche_keywords[random_niche], 5)
        st.session_state["keyword_input"] = ", ".join(selected_keywords)
        st.rerun()
    st.markdown("""</div>""", unsafe_allow_html=True)

with col1:
    st.text_input("Enter up to 5 keywords (comma-separated)", value=st.session_state["keyword_input"], key="keyword_input")

# --- Filters ---
st.markdown("### Filters")
col3, col4, col5 = st.columns(3)
with col3:
    min_subs = st.number_input("Min Subscribers", value=5000)
with col4:
    max_subs = st.number_input("Max Subscribers", value=65000)
with col5:
    active_years = st.number_input("Only Channels Active in Last Years", value=2)

# --- Run Button ---
run_button = st.button("Search YouTube for Leads")

# --- (Rest of the logic remains unchanged) ---
