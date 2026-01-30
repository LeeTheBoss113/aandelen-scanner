import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE & FUNCTIES ---
st.set_page_config(page_title="Ultimate Score Scanner 2026", layout="wide")

def scan_aandeel(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        if hist.empty: return None
        
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        info = stock.info
        div = info.get('dividendYield', 0) * 100 if info.get('dividendYield') else 0
        score = (100 - rsi) + (div * 5)
        
        return {
            "Ticker": ticker,
            "Prijs": round(hist['Close'].iloc[-1], 2),
            "RSI": round(rsi, 2),
            "Div %": round(div, 2),
            "Sector": info.get('sector', 'Onbekend'),
            "Score": round(score, 2)
        }
    except: return None

# --- 2. LAYOUT: DRIE KOLOMMEN ---
st.title("🚀 Ultimate Score Scanner 2026")

col_scan, col_kansen, col_port = st.columns([1.2, 1, 1.2])

# KOLOM 1: DE VOLLEDIGE SCANNER
with col_scan:
    st.header("🔍 Scanner")
    watch_input = st.text_input("Watchlist:", "ASML.AS, KO, PG, JNJ, TSLA, SHEL.AS, AAPL", key="scan_in")
    tickers = [t.strip().upper() for t in watch_input.split(",")]
    
    results = []
    for t in tickers:
        data = scan_aandeel(t)
        if data: results.append(data)
    
    if results:
        df_all = pd.DataFrame(results).sort_values(by="Score", ascending=False)
        st.dataframe(df_all[['Ticker', 'RSI', 'Score']], use_container_width=True)

# KOLOM 2: DE BESTE KANSEN (FILTER)
with col_kansen:
    st.header("💎 Top Kansen")
    if results:
        # We filteren op aandelen met een RSI onder de 40 of een Score boven de 70
        df_kansen = df_all[df_all['RSI'] <= 40].copy()
        if not df_kansen.empty:
            for _, row in df_kansen.iterrows():
                st.success(f"**{row['Ticker']}**\n\nRSI: {row['RSI']} | Score: {row['Score']}")
        else:
            st.info("Geen directe koopkansen gevonden.")

# KOLOM 3: PORTFOLIO & RISICO
with col_port:
    st.header("⚖️ Monitor")
    port_input = st.text_input("Mijn Bezit:", "KO, ASML.AS", key="port_in")
    mijn_tickers = [t.strip().upper() for t in port_input.split(",")]
    
    p_results = []
    for t in mijn_tickers:
        d = scan_aandeel(t)
        if d: p_results.append(d)
    
    if p_results:
        df_p = pd.DataFrame(p_results)
        st.bar_chart(df_p['Sector'].value_counts())
        for _, row in df_p.iterrows():
            st.write(f"**{row['Ticker']}**: {row['Sector']}")
