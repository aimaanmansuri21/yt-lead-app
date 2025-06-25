import streamlit as st
import pandas as pd
import datetime
import re
import random
import gspread
import openai
from openai import OpenAI
from google.oauth2.service_account import Credentials
from gspread_dataframe import set_with_dataframe
from googleapiclient.discovery import build
from Niche_Keyword_Dictionary_FIXED import niche_keywords

# --- OpenAI Client (new API) ---
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

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
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7
        )
        traits_raw = response.choices[0].message.content
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
...
