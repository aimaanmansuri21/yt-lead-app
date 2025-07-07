#cell 1
import streamlit as st
import pandas as pd
import datetime
import re
import ast
import gspread
import random
import openai
from openai import OpenAI
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe
from googleapiclient.discovery import build

# --- OpenAI Client ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# --- Trait Extraction Function ---
def extract_traits_from_bio(bio):
    if not bio or len(bio.strip()) < 20:
        return "No bio / too short"

    prompt = f"""
You are an expert at analyzing YouTube channel bios. Based on the bio below, identify 5 descriptive personality or content traits this creator likely has. Traits should be specific, multi-word if helpful, and reflect tone, intent, or style — not just generic adjectives.

Bio:
{bio}

Return traits in a Python list format, like: [\"trait1\", \"trait2\", \"trait3\", \"trait4\", \"trait5\"]
"""

    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        traits_raw = response.choices[0].message.content

        match = re.findall(r'\"(.*?)\"', traits_raw)
        if not match:
            raise ValueError(f"No valid traits found. Raw output: {traits_raw}")

        traits_cleaned = [trait.strip().capitalize() for trait in match if len(trait.strip()) > 1]
        return ", ".join(traits_cleaned[:5])
    except Exception as e:
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
        .block-container {
            padding: 2rem 3rem;
        }
        .stNumberInput>div>input {
            text-align: center;
        }
        label[for^='number_input_'] {
            display: block;
            text-align: center;
            margin-top: 0.25rem;
            font-weight: 500;
            font-size: 0.9rem;
        }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <h1 style='font-size: 2.8rem; font-weight: 600;'>📺 YouTube Lead Generator</h1>
    <p style='font-size: 1.1rem; color: #444;'>Find and organize high-potential creators in seconds.</p>
""", unsafe_allow_html=True)

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
            try:
                random_seed = random.randint(10000, 99999)
                prompt = f"""
You are a YouTube SEO strategist. Based on the seed `{random_seed}`, generate a specific and real niche, and give me 5 realistic, high-search, and clickable YouTube keyword phrases that creators in that niche are using right now.

Make sure:
- The niche is specific (not too broad like 'Fitness')
- The keywords should be phrases you'd actually find in video titles or search queries
- Avoid making up weird terms

Use this format exactly:
Niche: <niche>
Keywords: ["keyword1", "keyword2", "keyword3", "keyword4", "keyword5"]
"""
                response = client.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7
                )
                text = response.choices[0].message.content
                niche = re.search(r"Niche:\s*(.+)", text).group(1).strip()
                keywords = ast.literal_eval(re.search(r"Keywords:\s*(\[.*\])", text).group(1))
                st.session_state["keyword_input"] = ", ".join(keywords)
                st.toast(f"🎯 Niche: {niche}")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to generate keywords: {e}")
        st.markdown("</div>", unsafe_allow_html=True)
