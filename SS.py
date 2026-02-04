import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import numpy as np
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- VEILIGHEID: SECRETS LADEN MET FALLBACK ---
GMAIL_USER = st.secrets.get("GMAIL_USER", None)
GMAIL_PASSWORD = st.secrets.get("GMAIL_PASSWORD", None)
SEND_TO = st.secrets.get("SEND_TO", None)

st.set_page_config(page_title="Safe Dividend Trader", layout="wide")

if not GMAIL_USER or not GMAIL_PASSWORD:
    st.warning("⚠️ Secrets zijn nog niet (juist) ingesteld in het Streamlit Dashboard of secrets.toml.")
    st.info("Ga naar Settings -> Secrets en voeg GMAIL_USER en GMAIL_PASSWORD toe.")
else:
    st.sidebar.success("✅ Mail-gegevens geladen uit Secrets")

# --- MAIL FUNCTIE ---
def stuur_mail(ticker, advies, div, rsi, is_test=False):
    if not GMAIL_USER or not GMAIL_PASSWORD:
        st.error("Kan geen mail sturen: gegevens ontbreken.")
        return False
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = SEND_TO
        msg['Subject'] = "🧪 TEST" if is_test else f"🚀 ACTIE: {ticker}"
        body = "Verbinding werkt!" if is_test else f"Check {ticker} ({advies})"
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(GMAIL_USER, GMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        st.error(f"Fout bij verzenden: {e}")
        return False

# De rest van je code (Tickers, Analyse, Tabel) blijft hetzelfde...
