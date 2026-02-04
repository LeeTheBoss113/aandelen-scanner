import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import numpy as np
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

st.set_page_config(page_title="Dividend Trader Pro", layout="wide")

# --- SECRETS & DIAGNOSE ---
st.sidebar.title("🔐 Status")
try:
    sleutels = list(st.secrets.keys())
except:
    sleutels = []

GMAIL_USER = st.secrets.get("GMAIL_USER")
GMAIL_PASSWORD = st.secrets.get("GMAIL_PASSWORD")
SEND_TO = st.secrets.get("SEND_TO", GMAIL_USER)

if GMAIL_USER and GMAIL_PASSWORD:
    st.sidebar.success("✅ Secrets geladen")
else:
    st.sidebar.error("❌ Secrets missen")

# --- MAIL FUNCTIE ---
def stuur_mail(ticker, advies):
    try:
        msg = MIMEMultipart()
        msg['From'] = GMAIL_USER
        msg['To'] = SEND_TO
        msg['Subject'] = f"🚀 ACTIE: {ticker}"
        msg.attach(MIMEText(f"Signaal voor {ticker}: {advies}", 'plain'))
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
    if stuur_mail("TEST", "VERBINDING WERKT"):
        st.sidebar.success("📩 Check je inbox!")

# --- DATA VERWERKING ---
st.title("🛡️ Dividend Trader Dashboard")

# Simpele lijst om syntax-fouten te voorkomen
tickers = [
    'KO', 'PEP', 'JNJ', 'O', 'PG', 'ABBV', 'CVX', 'XOM', 'MMM', 'T',
    'VZ', 'WMT', 'LOW', 'TGT', 'ABT', 'MCD', 'ADBE', 'MSFT', 'AAPL', 'IBM',
    'HD', 'COST', 'LLY', 'PFE', 'MRK', 'DHR', 'UNH', 'BMY', 'AMGN', 'SBUX',
    'CAT', 'DE', 'HON', 'UPS', 'FDX', 'NEE', 'SO', 'D', 'DUK', 'PM',
    'MO', 'SCHW', 'BLK', 'SPGI', 'V', 'MA', 'AVGO', 'TXN', 'NVDA', 'JPM'
]

@st.cache_data(ttl=600)
def get_stock_data(symbol):
    try:
        t = yf.Ticker(symbol)
        df = t.history(period="1y")
        if df.empty: return None, 0
        div = (t.info.get('dividendYield', 0) or 0) * 100
        df['RSI'] = ta.rsi(df['Close'], length=14)
        return df, div
    except:
        return None, 0

data_rows = []
progress = st.progress(0)

for i, sym in enumerate(tickers):
    df, div = get_stock_data(sym)
    if df is not None:
        p = df['Close'].iloc[-1]
        rsi = df['RSI'].iloc[-1]
        m1y = df['Close'].mean()
        m6m = df['Close'].tail(126).mean()
        
        t1y = "✅" if p > m1y else "❌"
        t6m = "✅" if p > m6m else "❌"
        
        if t1y == "✅" and t6m == "✅" and rsi < 45:
            advies = "🌟 NU KOPEN"
        elif t1y == "✅" and rsi > 70:
            advies = "💰 WINST PAKKEN"
        elif t1y == "✅":
            advies = "🟢 HOLD"
        else:
            advies = "🔴 VERMIJDEN"

        data_rows.append({
            "Ticker": sym, "Advies": advies, "Dividend %": round(div, 2),
            "RSI": round(rsi, 1), "6m Trend": t6m, "1j Trend": t1y
        })
    progress.progress((i + 1) / len(tickers))

if data_rows:
    df_final = pd.DataFrame(data_rows).sort_values("Dividend %", ascending=False)
    st.dataframe(df_final, use_container_width=True)

time.sleep(900)
st.rerun()
