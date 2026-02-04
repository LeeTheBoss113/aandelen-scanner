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
sleutels = list(st.secrets.keys())

# Controleer of de benodigde secrets aanwezig zijn
check_user = "GMAIL_USER" in sleutels
check_pass = "GMAIL_PASSWORD" in sleutels

if check_user:
    st.sidebar.success("✅ GMAIL_USER geladen")
else:
    st.sidebar.error("❌ GMAIL_USER mist in Secrets")

if check_pass:
    st.sidebar.success("✅ GMAIL_PASSWORD geladen")
else:
    st.sidebar.error("❌ GMAIL_PASSWORD mist in Secrets")

# Gegevens toewijzen uit de kluis
GMAIL_USER = st.secrets.get("GMAIL_USER")
GMAIL_PASSWORD = st.secrets.get("GMAIL_PASSWORD")
SEND_TO = st.secrets.get("SEND_TO", GMAIL_USER) # Fallback naar user als send_to mist

# --- MAIL FUNCTIE ---
def stuur_mail(ticker, advies, div, rsi, is_test=False):
    if not check_user or not check_pass:
        st.error("Mail versturen afgebroken: Secrets niet correct geconfigureerd.")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = SEND_TO
        
        if is_test:
            msg['Subject'] = "🧪 TEST: Dividend Scanner Verbinding"
            body = "Gefeliciteerd! De verbinding met de Gmail-server via de Secrets is gelukt."
        else:
            msg['Subject'] = f"🚀 ACTIE NODIG: {ticker} is {advies}"
            body = f"Kans gevonden!\n\nAandeel: {ticker}\nStatus: {advies}\nDividend: {div}%\nRSI: {rsi}\n\nCheck je dashboard."
            
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"⚠️ Mail fout: {e}")
        return False

# Testknop in Sidebar
if st.
