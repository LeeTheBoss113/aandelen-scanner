import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
import time
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE & INITIALISATIE ---
st.set_page_config(page_title="Holy Grail Scanner 2026", layout="wide")

# Mail log om spam te voorkomen (1 uur limiet per ticker)
if 'mail_log' not in st.session_state:
    st.session_state.mail_log = {}

# --- 2. FUNCTIES ---

def stuur_alert_mail(ticker, score, rsi, type="KOOP"):
    huidige_tijd = time.time()
    log_key = f"{ticker}_{type}"
    
    # Check 1-uur limiet (3600 seconden) tenzij het een TEST is
    if type != "TEST":
        last_sent = st.session_state.mail_log.get(log_key, 0)
        if huidige_tijd - last_sent < 3600:
            return False

    try:
        user = st.secrets["email"]["user"]
        pw = st.secrets["email"]["password"]
        receiver = st.secrets["email"]["receiver"]
        
        subject = f"💎 {type} Signaal: {ticker}"
        body = f"""
        🚀 HOLY GRAIL DASHBOARD ALERT
        ------------------------------
        Type: {type}
        Aandeel: {ticker}
        Score: {score}
        RSI: {rsi}
        
        Box 3 Route: Denk aan het fiscale voordeel via je partner!
        """
        
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = user
        msg['To'] = receiver
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, pw)
            server.sendmail(user, receiver, msg.as_string())
        
        st.session_state.mail_log[log_key] = huidige_tijd
        return True
    except Exception as e:
        st.sidebar.error(f"Mail fout: {e}")
        return False

def scan_aandeel(ticker):
    try:
        # Download data met extra stabiliteit
        df = yf.download(ticker, period="1y", interval="1d", progress=False, group_by='column')
        
        if df.empty or len(df) < 20:
            return None

        # Fix voor Multi-index kolommen
        if isinstance(df.columns, pd.MultiIndex):
            close_prices = df['Close'][ticker]
        else:
            close_prices = df['Close']
            
        # RSI 14 EMA Berekening
        delta = close_prices.diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ema_up = up.ewm(com=13, adjust=False).mean()
        ema_down = down.ewm(com=13, adjust=False).mean()
        rs = ema_up / ema_down
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Fundamentele data
        t_obj = yf.Ticker(ticker)
        info = t_obj.info
        div = (info.get('dividendYield', 0) or 0) * 100
        sector = info.get('sector', 'Onbekend')

        # HOLY GRAIL LOGICA
        rsi_val = float(rsi)
        rsi_factor = 100 - rsi_val
        if rsi_val > 70: rsi_factor -= 30 # Strafpunt duur
        if rsi_val < 35: rsi_factor += 25 # Bonus goedkoop
        
        score = rsi_factor + (div * 3)
        
        return {
