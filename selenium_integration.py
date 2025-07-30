import time
import re
import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from twocaptcha import TwoCaptcha

# Load API key from Streamlit secrets
CAPTCHA_API_KEY = st.secrets["CAPTCHA_API_KEY"]

def solve_recaptcha_v2(driver, sitekey, page_url):
    """Solve reCAPTCHA V2 using 2Captcha API and return True if successful"""
    solver = TwoCaptcha(CAPTCHA_API_KEY)
    try:
        st.write(f"🧩 Solving captcha for: {page_url}")
        result = solver.recaptcha(sitekey=sitekey, url=page_url)
        token = result['code']

        # Inject token into the g-recaptcha-response element
        driver.execute_script(
            'document.getElementById("g-recaptcha-response").style.display = "block";'
        )
        driver.execute_script(
            f'document.getElementById("g-recaptcha-response").value="{token}";'
        )
        time.sleep(2)
        return True
    except Exception as e:
        st.error(f"Captcha solving failed: {e}")
        return False

def scrape_youtube_emails(channel_urls, limit=5):
    """
    Scrape emails from YouTube About pages with captcha solving.
    Returns a dict: {channel_url: email}
    """

    # Chrome/Chromium setup for Streamlit Cloud
    chrome_options = Options()
    chrome_options.binary_location = "/usr/bin/chromium"
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--window-size=1920x1080")

    # Point Selenium to pre-installed Chromium driver in Streamlit Cloud
    service = Service("/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)

    wait = WebDriverWait(driver, 10)
    results = {}

    for i, url in enumerate(channel_urls[:limit]):
        email_found = None
        about_url = url.rstrip("/") + "/about"
        st.write(f"[{i+1}/{limit}] Visiting {about_url}")

        try:
            driver.get(about_url)
            time.sleep(3)

            # Look for the "View Email Address" button
            try:
                view_email_btn = wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//yt-formatted-string[contains(text(),'View Email Address')]")
                ))
                view_email_btn.click()
                time.sleep(2)

                # If captcha appears
                if "recaptcha" in driver.page_source.lower():
                    sitekey_match = re.search(r'data-sitekey="(.*?)"', driver.page_source)
                    if sitekey_match:
                        sitekey = sitekey_match.group(1)
                        if solve_recaptcha_v2(driver, sitekey, about_url):
                            try:
                                submit_btn = driver.find_element(By.XPATH, "//button[contains(text(),'Submit')]")
                                submit_btn.click()
                                time.sleep(3)
                            except:
                                pass

                # Extract email after reveal
                page_source = driver.page_source
                matches = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", page_source)
                if matches:
                    email_found = matches[0]

            except:
                st.warning("No 'View Email Address' button found, scanning page directly...")
                page_source = driver.page_source
                matches = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", page_source)
                if matches:
                    email_found = matches[0]

        except Exception as e:
            st.error(f"Error scraping {url}: {e}")

        results[url] = email_found if email_found else "None found"
        time.sleep(2)

    driver.quit()
    return results
