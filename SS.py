import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Holy Grail Scanner 2026", layout="wide")

def scan_aandeel(ticker):
    try:
        # Download data (1 jaar historie)
        # We gebruiken group_by='column' om Multi-index ellende te voorkomen
        df = yf.download(ticker, period="1y", interval="1d", progress=False, group_by='column')
        
        if df.empty or len(df) < 20:
            return None

        # Fix voor nieuwe yfinance Multi-index (pakt de 'Close' kolom ongeacht niveau)
        if isinstance(df.columns, pd.MultiIndex):
            close_prices = df['Close'][ticker]
        else:
            close_prices = df['Close']
            
        # RSI 14 Berekening
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs)).iloc[-1]
        
        # Dividend & Sector via Ticker object (snelle call)
        t_obj = yf.Ticker(ticker)
        info = t_obj.info
        div = (info.get('dividendYield', 0) or 0) * 100
        sector = info.get('sector', 'Onbekend')

        # HOLY GRAIL LOGICA
        rsi_val = float(rsi)
        rsi_factor = 100 - rsi_val
        if rsi_val > 70: rsi_factor -= 30 
        if rsi_val < 35: rsi_factor += 25  
        score = rsi_factor + (div * 3)
        
        return {
            "Ticker": ticker, 
            "RSI": round(rsi_val, 2), 
            "Div %": round(float(div), 2),
            "Sector": sector, 
            "Score": round(float(score), 2)
        }
    except Exception as e:
        st.sidebar.error(f"Fout bij {ticker}: {e}")
        return None

# --- 2. DASHBOARD ---
st.title("🚀 Holy Grail Portfolio Dashboard 2026")

c1, c2, c3, c4 = st.columns([1.2, 0.8, 1, 1])

# We laden de data één keer centraal om dubbele calls te voorkomen
watchlist_str = st.sidebar.text_input("Watchlist:", "ASML.AS, KO, PG, JNJ, O, ABBV, SHEL.AS, MO")
portfolio_str = st.sidebar.text_input("Mijn Bezit:", "KO, ASML.AS")

tickers_w = [t.strip().upper() for t in watchlist_str.split(",") if t.strip()]
tickers_p = [t.strip().upper() for t in portfolio_str.split(",") if t.strip()]

# Haal resultaten op
with st.spinner('Beursdata ophalen...'):
    results_w = [scan_aandeel(t) for t in tickers_w]
    results_w = [r for r in results_w if r is not None]
    
    results_p = [scan_aandeel(t) for t in tickers_p]
    results_p = [r for r in results_p if r is not None]

# --- KOLOM 1: SCANNER ---
with c1:
    st.header("🔍 Scanner")
    if results_w:
        df_all = pd.DataFrame(results_w).sort_values(by="Score", ascending=False)
        st.dataframe(df_all[['Ticker', 'RSI', 'Div %', 'Score']].style.background_gradient(cmap='RdYlGn', subset=['Score']), use_container_width=True)
    else:
        st.info("Geen watchlist data beschikbaar.")

# --- KOLOM 2: SIGNALEN ---
with c2:
    st.header("⚡ Signalen")
    st.subheader("💎 Buy")
    buys = [r for r in results_w if r['Score'] >= 85]
    if buys:
        for b in buys: st.success(f"**{b['Ticker']}** (Score: {b['Score']})")
    else: st.write("Geen koopkansen.")

    st.divider()
    st.subheader("🔥 Sell")
    sells = [r for r in results_p if r['RSI'] >= 70]
    if sells:
        for s in sells: st.warning(f"**{s['Ticker']}** (RSI: {s['RSI']})")
    else: st.write("Geen verkoop nodig.")

# --- KOLOM 3: PORTFOLIO ---
with c3:
    st.header("⚖️ Portfolio")
    if results_p:
        df_p = pd.DataFrame(results_p)
        st.dataframe(df_p[['Ticker', 'RSI', 'Sector']], use_container_width=True)
        st.bar_chart(df_p.set_index('Ticker')['RSI'])
    else:
        st.info("Portfolio leeg.")

# --- KOLOM 4: TAX ---
with c4:
    st.header("💰 Tax Benefit")
    vermogen = st.number_input("Vermogen (€):", value=100000)
    besparing = max(0, vermogen - 57000) * 0.021
    st.metric("Jaarlijkse Besparing", f"€{besparing:,.0f}")
    st.success("Box 3 Route: Actief")
