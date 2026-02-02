import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
import os
from datetime import date
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Sector Hub", layout="wide")

# Pas deze gegevens aan voor je eigen mail (liefst via Streamlit Secrets)
EMAIL_SENDER = "jouw-email@gmail.com"
EMAIL_PASSWORD = "jouw-app-wachtwoord" 
EMAIL_RECEIVER = "ontvanger-email@gmail.com"
LOG_FILE = "mail_log.txt"

# --- 2. SECTOR DEFINITIES ---
SECTOREN = {
    "💻 Tech": ["NVDA", "MSFT", "GOOGL", "AMZN", "AAPL", "TSLA", "ASML.AS"],
    "🏦 Finance": ["INGA.AS", "ABN.AS", "V", "MA", "JPM", "GS", "KO"],
    "⛽ Energie": ["SHEL.AS", "XOM", "CVX", "TTE", "BP"],
    "🛒 Retail": ["AD.AS", "WMT", "COST", "NKE", "DIS", "MCD"],
    "🧪 Recovery": ["PYPL", "BABA", "INTC", "CRM", "SQ", "SHOP"]
}

# --- 3. MAIL FUNCTIE ---
def stuur_dagelijkse_mail(strong_buys):
    vandaag = str(date.today())
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            if f.read().strip() == vandaag:
                return

    inhoud = f"Holy Grail Scanner Update ({vandaag}):\n\n"
    for sb in strong_buys:
        inhoud += f"💎 {sb['Ticker']} | Score: {sb['Score']} | Prijs: €{sb['Prijs']}\n"
    
    msg = MIMEText(inhoud)
    msg['Subject'] = f"🎯 Dagelijkse Strong Buys - {vandaag}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        with open(LOG_FILE, "w") as f:
            f.write(vandaag)
        st.sidebar.success("Dagelijkse mail verzonden!")
    except Exception as e:
        st.sidebar.error(f"Mail fout: {e}")

# --- 4. DATA FUNCTIE ---
def scan_aandeel(ticker, sector):
    try:
        # 2 jaar data ophalen voor SMA 252
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        if df is None or df.empty or len(df) < 252:
            return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        close = df['Close']
        curr = float(close.iloc[-1])
        sma_63 = close.rolling(63).mean().iloc[-1]
        sma_252 = close.rolling(252).mean().iloc[-1]
