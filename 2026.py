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

st.set_page_config(layout="wide", page_title="Trend-RSI Scanner 2026", initial_sidebar_state="expanded")

# --- DATA FUNCTIES ---
def get_airtable_data(table_name):
    try:
        url = f"https://api.airtable.com/v0/{BASE_ID}/{table_name}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            records = r.json().get('records', [])
            return pd.DataFrame([ {**rec['fields'], 'airtable_id': rec['id']} for rec in records if rec['fields'].get('Ticker') ])
        return pd.DataFrame()
    except: return pd.DataFrame()

@st.cache_data(ttl=300)
def get_combo_metrics(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="14mo") # Extra marge voor 12m berekening
        if len(hist) < 252: return None
        
        cur = hist['Close'].iloc[-1]
        m6 = hist['Close'].iloc[-126] # ~6 maanden geleden
        m12 = hist['Close'].iloc[-252] # ~1 jaar geleden
        
        rsi = ta.rsi(hist['Close'], length=14).iloc[-1]
        p6 = ((cur - m6) / m6) * 100
        p12 = ((cur - m12) / m12) * 100
        
        # SCORE LOGICA
        advies = "⌛ WAIT"
        score = 0
        if p12 > 0 and p6 > 10: # Sterke Bull Trend
            if rsi < 40: 
                advies = "🔥 STRONG BUY (Dip)"
                score = 3
            elif rsi < 50: 
                advies = "✅ ACCUMULATE"
                score = 2
        elif rsi > 75:
            advies = "💰 TAKE PROFIT"
            score = -1

        return {
            "Ticker": ticker, 
            "Prijs": round(cur, 2), 
            "RSI": round(rsi, 1), 
            "6M %": round(p6, 1), 
            "12M %": round(p12, 1),
            "Advies": advies,
            "Score": score
        }
    except: return None

# --- UI ---
df_p = get_airtable_data(PORTFOLIO_TABLE)
df_l = get_airtable_data(LOG_TABLE)

tab1, tab2 = st.tabs(["🚀 Trend-RSI Scanner", "📜 Logboek"])

with tab1:
    c1, c2 = st.columns([1.5, 1])
    
    with c1:
        st.subheader("🔍 Markt Kansen")
        watchlist = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMD', 'PLTR', 'COIN', 'MSTR', 'META', 'AMZN', 'GOOGL', 'ASML.AS', 'ADYEN.AS']
        results = []
        for t in watchlist:
            m = get_combo_metrics(t)
            if m: results.append(m)
        
        if results:
            sdf = pd.DataFrame(results).sort_values(by="Score", ascending=False)
            
            def color_advies(val):
                color = 'white'
                if 'BUY' in val: color = '#27ae60'
                elif 'PROFIT' in val: color = '#e74c3c'
                elif 'ACCUMULATE' in val: color = '#f39c12'
                return f'background-color: {color}; color: black; font-weight: bold'

            st.dataframe(sdf.style.applymap(color_advies, subset=['Advies']), use_container_width=True, hide_index=True)

    with c2:
        st.subheader("💼 Portfolio Status")
        if not df_p.empty:
            for _, row in df_p.iterrows():
                ticker = str(row['Ticker']).upper()
                try:
                    p_live = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
                    win_p = ((p_live - row['Koers']) / row['Koers']) * 100
                    
                    # SALAMI 15% TRIGGER
                    status = "Normal"
                    if win_p >= 15:
                        st.warning(f"🎯 {ticker} TARGET BEREIKT (+15%)!")
                        if st.button(f"Cash winst op {ticker}", key=f"s_{row['airtable_id']}"):
                            # Verkoop functie aanroepen (zie eerdere code)
                            pass
                    
                    st.metric(ticker, f"{win_p:.1f}%", delta=f"€{((row['Inleg']/row['Koers'])*p_live - row['Inleg']):.2f}")
                except: pass

with tab2:
    # Logboek code (maandoverzicht) zoals eerder besproken...
    st.info("Zie dashboard voor maandelijkse winsten.")