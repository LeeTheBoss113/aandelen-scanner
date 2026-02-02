import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
import os
from datetime import date
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE & MAIL SETTINGS ---
st.set_page_config(page_title="Holy Grail Sector Hub", layout="wide")

EMAIL_SENDER = "jouw-email@gmail.com"
EMAIL_PASSWORD = "jouw-app-wachtwoord" # Gebruik een Google App Password
EMAIL_RECEIVER = "ontvanger-email@gmail.com"
LOG_FILE = "mail_log.txt"

def stuur_dagelijkse_mail(strong_buys):
    """Verstuurt één verzamelmail per dag met alle Strong Buys."""
    vandaag = str(date.today())
    
    # Check of we vandaag al gemaild hebben
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r") as f:
            laatste_datum = f.read().strip()
            if laatste_datum == vandaag:
                return # Stop de functie als er vandaag al gemaild is

    # Stel de mail samen
    inhoud = "De Holy Grail Scanner heeft de volgende Strong Buys gevonden voor vandaag:\n\n"
    for sb in strong_buys:
        inhoud += f"- {sb['Ticker']} (Sector: {sb['Sector']}) | Score: {sb['Score']} | Koers: €{sb['Prijs']}\n"
    
    msg = MIMEText(inhoud)
    msg['Subject'] = f"🎯 Dagelijkse Holy Grail Update - {vandaag}"
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        
        # Log de datum van vandaag na succesvol verzenden
        with open(LOG_FILE, "w") as f:
            f.write(vandaag)
        st.sidebar.success("Dagelijkse update verzonden!")
    except Exception as e:
        st.sidebar.error(f"Mail fout: {e}")

# --- 2. DATA FUNCTIE (Met trend-logica) ---
def scan_aandeel(ticker, sector):
    try:
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        if df is None or df.empty or len(df) < 252: return None
        
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        close = df['Close']
        curr = float(close.iloc[-1])

        # TRENDS (3M & 1J)
        sma_63 = close.rolling(63).mean().iloc[-1]
        sma_252 = close.rolling(252).mean().iloc[-1]
        
        # INDICATOREN
        delta = close.diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = -1 * delta.clip(upper=0).rolling(14).mean()
        rsi = 100 - (100 / (1 + (up / (down + 0.000001)).iloc[-1]))
        hi = float(close.tail(252).max()) 
        dist_top = ((
