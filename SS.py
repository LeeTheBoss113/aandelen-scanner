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

def stuur_alert_mail(naam, ticker, score, rsi, type="KOOP"):
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
        
        body = f"🚨 {type} ALERT\n\nBedrijf: {naam}\nTicker: {ticker}\nScore: {score}\nRSI: {rsi}\n\nCheck je dashboard voor de Box 3 route!"
        msg = MIMEText(body)
        msg['Subject'] = f"💎 {type} Signaal: {naam}"
        msg['From'] = user
        msg['To'] = receiver
        
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(user, pw)
            server.sendmail(user, receiver, msg.as_string())
        
        st.session_state.mail_log[log_key] = huidige_tijd
        return True
    except:
        return False

def scan_aandeel(ticker):
    try:
        # Threads=False tegen MemoryErrors, period="1mo" voor snelheid
        df = yf.download(ticker, period="1mo", interval="1d", progress=False, threads=False)
        if df.empty or len(df) < 15:
            return None
        
        # Kolom fix voor Yahoo Multi-index
        if isinstance(df.columns, pd.MultiIndex):
            close_prices = df['Close'][ticker]
        else:
            close_prices = df['Close']
            
        # RSI berekening
        delta = close_prices.diff()
        up = delta.clip(lower=0).rolling(window=14).mean()
        down = -1 * delta.clip(upper=0).rolling(window=14).mean()
        rs = up / down
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Bedrijfsinfo ophalen
        t_obj = yf.Ticker(ticker)
        info = t_obj.info
        naam = info.get('longName', ticker)
        div = (info.get('dividendYield', 0) or 0) * 100
        
        # Holy Grail Score berekening
        score = (100 - float(rsi)) + (float(div) * 3)
        
        return {
            "Bedrijf": naam,
            "Ticker": ticker, 
            "RSI": round(float(rsi), 2), 
            "Div %": round(float(div), 2), 
            "Score": round(float(score), 2)
        }
    except:
        return None
