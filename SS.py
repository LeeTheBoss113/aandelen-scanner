import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
import time
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Scanner 2026", layout="wide")

if 'mail_log' not in st.session_state:
    st.session_state.mail_log = {}

# --- 2. FUNCTIES ---

def stuur_alert_mail(ticker, score, rsi, type="KOOP"):
    huidige_tijd = time.time()
    log_key = f"{ticker}_{type}"
    if type != "TEST":
        last_sent = st.session_state.mail_log.get(log_key, 0)
        if huidige_tijd - last_sent < 3600:
            return False
    try:
        user = st.secrets["email"]["user"]
        pw = st.secrets["email"]["password"]
        receiver = st.secrets["email"]["receiver"]
        msg = MIMEText(f"🚨 {type} ALERT\nTicker: {ticker}\nScore: {score}\nRSI: {rsi}")
        msg['Subject'] = f"💎 {type} Signaal: {ticker}"
        msg['From'] = user
        msg['To'] = receiver
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, pw)
            server.sendmail(user, receiver, msg.as_string())
        st.session_state.mail_log[log_key] = huidige_tijd
        return True
    except: return False

def scan_aandeel(ticker):
    try:
        # 1. Data ophalen
        df = yf.download(ticker, period="1mo", interval="1d", progress=False, threads=False)
        if df.empty or len(df) < 15: 
            return None
        
        # 2. Kolom fix voor Multi-index
        close_prices = df['Close'][ticker] if isinstance(df.columns, pd.MultiIndex) else df['Close']
            
        # 3. RSI berekening
        delta = close_prices.diff()
        up = delta.clip(lower=0).rolling(window=14).mean()
        down = -1 * delta.clip(upper=0).rolling(window=14).mean()
        rs = up / down
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # 4. Dividend ophalen
        t_obj = yf.Ticker(ticker)
        div = (t_obj.info.get('dividendYield', 0) or 0) * 100
        
        # 5. Score berekenen
        score = (100 - float(rsi)) + (float(div) * 3)
        
        return {
            "Ticker": ticker, 
            "RSI": round(float(rsi), 2), 
            "Div %": round(float(div), 2), 
            "Score": round(float(score), 2)
        }
    except Exception as e:
        # Als er iets misgaat, vangen we het hier netjes op
    return None
