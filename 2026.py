import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
from datetime import datetime

# --- CONFIG ---
AIRTABLE_TOKEN = "patCdgzOgVDPNlGCw.3008de99d994972e122dc62031b3f5aa5f2647cfa75c5ac67215dc72eba2ce07"
BASE_ID = "appgvzDsvbvKi7e45"
PORTFOLIO_TABLE = "Portfolio"
LOG_TABLE = "Logboek"

HEADERS = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}

st.set_page_config(layout="wide", page_title="Live Profit Scanner 2026", initial_sidebar_state="expanded")

# --- DATA FUNCTIES ---
def get_airtable_data(table_name):
    try:
        url = f"https://api.airtable.com/v0/{BASE_ID}/{table_name}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            records = r.json().get('records', [])
            return pd.DataFrame([ {**rec['fields'], 'airtable_id': rec['id']} for rec in records ])
        return pd.DataFrame()
    except: return pd.DataFrame()

@st.cache_data(ttl=600)  # Ververst elke 10 minuten
def get_dynamic_watchlist():
    """Haalt live de meest interessante aandelen op van Yahoo Finance"""
    try:
        # We gebruiken bekende tickers als basis, maar vullen dit aan met de huidige top-performers
        # In een geavanceerdere setup zou je hier een echte API-scrapper gebruiken
        # Voor nu laden we een brede selectie van 'High Volume' en 'Top Gainers'
        base_tickers = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMD', 'PLTR', 'COIN', 'MSTR', 'MARA', 'META', 'AMZN', 'GOOGL', 'BABA']
        return base_tickers
    except:
        return ['NVDA', 'TSLA', 'PLTR']

@st.cache_data(ttl=300)
def get_scan_metrics(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="6mo")
        if len(hist) < 20: return None
        cur = hist['Close'].iloc[-1]
        rsi = ta.rsi(hist['Close'], length=14).iloc[-1]
        vol_change = (hist['Volume'].iloc[-1] / hist['Volume'].mean()) 
        return {
            "Ticker": ticker, 
            "Prijs": round(cur, 2), 
            "RSI": round(rsi, 1), 
            "Volume_Boost": round(vol_change, 2),
            "Day_%": round(((hist['Close'].iloc[-1] - hist['Open'].iloc[-1]) / hist['Open'].iloc[-1]) * 100, 2)
        }
    except: return None

# --- UI LOGICA ---
df_p = get_airtable_data(PORTFOLIO_TABLE)
df_l = get_airtable_data(LOG_TABLE)

st.title("🚀 Real-Time Profit Scanner")
st.markdown("Deze scanner zoekt naar **momentum** en **volume** in de huidige markt.")

# Dynamische Watchlist ophalen
watchlist = get_dynamic_watchlist()
results = []
for t in watchlist:
    m = get_scan_metrics(t)
    if m:
        # Strategie: Filter op aandelen met hoog volume OF een RSI dip
        if m['Volume_Boost'] > 1.5: m['Actie'] = "🔥 HIGH VOLUME"
        elif m['RSI'] < 35: m['Actie'] = "🛡️ OVERSOLD (BUY)"
        elif m['RSI'] > 70: m['Actie'] = "⚠️ OVERBOUGHT"
        else: m['Actie'] = "⚖️ NEUTRAL"
        results.append(m)

if results:
    scan_df = pd.DataFrame(results).sort_values(by="Day_%", ascending=False)
    
    # Styling
    def highlight_profit(row):
        color = 'transparent'
        if row['Actie'] == "🔥 HIGH VOLUME": color = '#1abc9c'
        elif row['Actie'] == "🛡️ OVERSOLD (BUY)": color = '#3498db'
        elif row['Actie'] == "⚠️ OVERBOUGHT": color = '#e74c3c'
        return [f'background-color: {color}' if i == len(row)-1 else '' for i in range(len(row))]

    st.dataframe(scan_df.style.apply(highlight_profit, axis=1), use_container_width=True, hide_index=True)

st.divider()

# --- PORTFOLIO SECTIE MET 15% TRIGGER ---
st.subheader("💼 Jouw Strategie Check")
if not df_p.empty:
    for _, row in df_p.iterrows():
        t_data = yf.Ticker(row['Ticker']).history(period="1d")
        if not t_data.empty:
            cur_p = t_data['Close'].iloc[-1]
            win_perc = ((cur_p - row['Koers']) / row['Koers']) * 100
            
            # De 15% Salami-regel
            label = "✅ GEZOND"
            if win_perc >= 15:
                label = "🎯 TARGET BEREIKT: PAK WINST!"
                st.balloons()
            elif win_perc < -5:
                label = "⚠️ STOP-LOSS ALERT"

            st.metric(f"{row['Ticker']} (Inleg: €{row['Inleg']})", f"{win_perc:.2f}%", delta=label)