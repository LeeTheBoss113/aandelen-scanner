import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import numpy as np
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 1. Pagina instellingen
st.set_page_config(page_title="Dividend Trader Pro", layout="wide")

# --- DIAGNOSE & SECRETS CHECK ---
st.sidebar.title("🔐 Systeem Status")

try:
    sleutels = list(st.secrets.keys())
except:
    sleutels = []

check_user = "GMAIL_USER" in sleutels
check_pass = "GMAIL_PASSWORD" in sleutels

if check_user:
    st.sidebar.success("✅ GMAIL_USER geladen")
else:
    st.sidebar.error("❌ GMAIL_USER mist")

if check_pass:
    st.sidebar.success("✅ GMAIL_PASSWORD geladen")
else:
    st.sidebar.error("❌ GMAIL_PASSWORD mist")

GMAIL_USER = st.secrets.get("GMAIL_USER")
GMAIL_PASSWORD = st.secrets.get("GMAIL_PASSWORD")
SEND_TO = st.secrets.get("SEND_TO", GMAIL_USER)

# --- MAIL FUNCTIE ---
def stuur_mail(ticker, advies, div, rsi, is_test=False):
    if not check_user or not check_pass:
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = SEND_TO
        msg['Subject'] = "🧪 TEST" if is_test else f"🚀 ACTIE: {ticker}"
        inhoud = "Verbinding werkt!" if is_test else f"Kans gevonden voor {ticker} ({advies})"
        msg.attach(MIMEText(inhoud, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"Fout: {e}")
        return False

if st.sidebar.button("Stuur Test Mail"):
    if stuur_mail("TEST", "TEST", 0, 0, is_test=True):
        st.sidebar.success("📩 Verzonden!")

# --- HOOFDPROGRAMMA ---
st.title("🛡️ Dividend Trader Dashboard")
st.caption(f"Update: {time.strftime('%H:%M:%S')} - Ververst elke 15 min")

# 2. De 50 Tickers (Netjes gestructureerd om SyntaxErrors te voorkomen)
symbols_dict = {
    '
