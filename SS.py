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

# --- SECRETS & STATUS ---
st.sidebar.title("🔐 Systeem Status")

# Flexibele check voor secrets (pakt zowel 'email' als 'GMAIL_USER')
GMAIL_USER = st.secrets.get("GMAIL_USER") or st.secrets.get("email")
GMAIL_PASSWORD = st.secrets.get("GMAIL_PASSWORD") or st.secrets.get("password")
SEND_TO = st.secrets.get("SEND_TO") or GMAIL_USER

if GMAIL_USER:
    st.sidebar.success("✅ Gebruiker gevonden")
else:
    st.sidebar.error("❌ Geen email gevonden in Secrets")

if GMAIL_PASSWORD:
    st.sidebar.success("✅ Wachtwoord gevonden")
else:
    st.sidebar.error("❌ Geen password gevonden in Secrets")

# --- MAIL FUNCTIE ---
def stuur_mail(ticker, advies):
    if not GMAIL_USER or not GMAIL_PASSWORD:
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = SEND_TO
        msg['Subject'] = f"🚀 Dividend Signaal: {ticker}"
        msg.attach(MIMEText(f"Het systeem ziet een kans voor {ticker}: {advies}", 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.sidebar.error(f"Mail fout: {e}")
        return False

if st.sidebar.button("Stuur Test Mail"):
    if stuur_mail("TEST", "VERBINDING OK"):
        st.sidebar.success("📩 Test mail verzonden!")

# --- HOOFDPROGRAMMA ---
st.title("🛡️ Dividend Trader Dashboard")
st.caption(f"La
