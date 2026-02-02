import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib, os
from datetime import date
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Sector Hub", layout="wide")
EMAIL_SENDER = "jouw-email@gmail.com"
EMAIL_PASSWORD = "jouw-app-wachtwoord" 
EMAIL_RECEIVER = "ontvanger-email@gmail.com"
LOG_FILE = "mail_log.txt"

SECTOREN = {
    "💻 Tech": ["NVDA", "MSFT", "GOOGL", "AMZN", "AAPL", "TSLA", "ASML.AS"],
    "🏦 Finance": ["INGA.AS", "ABN.AS", "V", "MA", "JPM", "GS", "KO"],
    "⛽ Energie": ["SHEL.AS", "XOM", "CVX", "TTE", "BP"],
    "🛒 Retail": ["AD.AS", "WMT", "COST", "NKE", "DIS", "MCD"],
    "🧪 Recovery": ["PYPL", "BABA", "INTC", "CRM", "SQ", "SHOP"]
}

# --- 2. MAIL FUNCTIE ---
def stuur_mail(strong_buys):
    try:
        vandaag = str(date.today())
        if os.path.exists(LOG_FILE):
            with open(LOG_FILE, "r") as f:
                if f.read().strip() == vandaag: return
        inhoud = "".join([f"💎 {s['Ticker']} | Score: {s['Score']}\n" for s in strong_buys])
        msg = MIMEText(inhoud)
        msg['Subject'] = f"🎯 Holy Grail: {len(strong_buys)} Strong Buys"
        msg['From'], msg['To'] = EMAIL_SENDER, EMAIL_RECEIVER
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, EMAIL_RECEIVER, msg.as_string())
        with open(LOG_FILE, "w") as f: f.write(vandaag)
    except: pass

# --- 3. SCAN LOGICA ---
def scan_aandeel(ticker, sector):
    try:
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        if df is None or len(df) < 252: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
        close = df['Close']
        curr = float(close.iloc[-1])
        sma63, sma252 = close.rolling(63).mean().iloc[-1], close.rolling(252).mean().iloc[-1]
        delta = close.diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = -1 * delta.clip(upper=0).rolling(14).mean()
        rsi = 100 - (100 / (1 + (up / (down + 1e-6)).iloc[-1]))
        hi = float(close.tail(252).max())
        dist_top = ((hi - curr) / hi) * 100
        score = (100 - float(rsi)) + (dist_top * 1.5)
        if curr > sma252: score += 10
        if curr > sma63: score += 5
        status = "💎 STRONG BUY" if score > 100 and curr > sma252 else "✅ Buy" if score > 80 else "🔥 SELL" if rsi > 75 else "⚖️ Hold"
        return {"Sector": sector, "Ticker": ticker, "Score": round(score, 1), "Prijs": round(curr, 2), "Status": status, "Trend3M": "✅" if curr > sma63 else "❌", "Trend1J": "✅" if curr > sma252 else
