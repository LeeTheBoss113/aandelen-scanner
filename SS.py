import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib, os
from datetime import date
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Sector Hub", layout="wide")

# Pas deze aan indien nodig
EMAIL_SENDER = "jouw-email@gmail.com"
EMAIL_PASSWORD = "jouw-app-wachtwoord" 
EMAIL_RECEIVER = "ontvanger-email@gmail.com"

SECTOREN = {
    "💻 Tech": ["NVDA", "MSFT", "GOOGL", "AMZN", "AAPL", "TSLA", "ASML.AS"],
    "🏦 Finance": ["INGA.AS", "ABN.AS", "V", "MA", "JPM", "GS", "KO"],
    "⛽ Energie": ["SHEL.AS", "XOM", "CVX", "TTE", "BP"],
    "🛒 Retail": ["AD.AS", "WMT", "COST", "NKE", "DIS", "MCD"],
    "🧪 Recovery": ["PYPL", "BABA", "INTC", "CRM", "SQ", "SHOP"]
}

# --- 2. SCAN LOGICA ---
def scan_aandeel(ticker, sector):
    try:
        df = yf.download(ticker, period="2y", interval="1d", progress=False)
        if df is None or len(df) < 252: return None
        if isinstance(df.columns, pd.MultiIndex): 
            df.columns = df.columns.get_level_values(0)
            
        close = df['Close']
        curr = float(close.iloc[-1])
        sma63 = close.rolling(63).mean().iloc[-1]
        sma252 = close.rolling(252).mean().iloc[-1]
        
        delta = close.diff()
        up = delta.clip(lower=0).rolling(14).mean()
        down = -1 * delta.clip(upper=0).rolling(14).mean()
        rsi = 100 - (100 / (1 + (up / (down + 1e-6)).iloc[-1]))
        hi = float(close.tail(252).max())
        dist_top = ((hi - curr) / hi) * 100
        
        score = (100 - float(rsi)) + (dist_top * 1.5)
        if curr > sma252: score += 10
        if curr > sma63: score += 5
        
        status = "⚖️ Hold"
        if score > 100 and curr > sma252: status = "💎 STRONG BUY"
        elif score > 80: status = "✅ Buy"
        elif rsi > 75: status = "🔥 SELL"
            
        res = {"Sector": sector, "Ticker": ticker}
        res["Score"] = round(score, 1)
        res["Status"] = status
        res["Trend3M"] = "✅" if curr > sma63 else "❌"
        res["Trend1J"] = "✅" if curr > sma252 else "❌"
        res["History"] = close.tail(126) # 6 maanden voor grafiek
        return res
    except: 
        return None

# --- 3. UI UITVOERING ---
st.title("🎯 Holy Grail: Sector Dashboard")
all_res = []
ticker_items = [(t, s) for s, ts in SECTOREN.items() for t in ts]
pb = st
