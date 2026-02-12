import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import time

# --- CONFIG ---
AIRTABLE_TOKEN = "patCdgzOgVDPNlGCw.3008de99d994972e122dc62031b3f5aa5f2647cfa75c5ac67215dc72eba2ce07"
BASE_ID = "appgvzDsvbvKi7e45"
TABLE_NAME = "Portfolio"

# WATCHLISTS (Pas deze aan naar jouw favorieten)
WATCHLIST_GROWTH = ['NVDA', 'TSLA', 'PLTR', 'AMD', 'COIN', 'META', 'MSTR', 'ASML']
WATCHLIST_DIVIDEND = ['KO', 'PEP', 'O', 'ABBV', 'JNJ', 'MSFT', 'SCHD', 'MAIN']

URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
HEADERS = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}

st.set_page_config(layout="wide", page_title="Market Explorer 2026")

# --- STYLING ---
def style_ticker(row):
    # Als het aandeel in bezit is, geef de Ticker kolom een kleurtje
    if row['In Bezit'] == '✅':
        return ['background-color: #2e4053; color: #58d68d; font-weight: bold'] + [''] * 5
    return [''] * 6

def color_signal(val):
    if 'BUY' in val: color = '#27ae60'
    elif 'SELL' in val: color = '#e74c3c'
    else: color = '#34495e'
    return f'background-color: {color}; color: white; font-weight: bold'

# --- DATA FUNCTIES ---
def get_portfolio():
    try:
        r = requests.get(URL, headers=HEADERS).json()
        records = r.get('records', [])
        return {rec['fields'].get('Ticker'): rec['fields'] for rec in records}
    except: return {}

def get_market_info(ticker):
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="60d")
        if df.empty: return None
        return {
            "price": df['Close'].iloc[-1],
            "rsi": ta.rsi(df['Close'], length=14).iloc[-1]
        }
    except: return None

# --- UI ---
st.title("🔍 Market Explorer & Scanner")
portfolio = get_portfolio()

tab1, tab2 = st.tabs(["🚀 Growth Explorer", "💎 Dividend Watcher"])

def scan_market(watchlist, strategy_name, buy_rsi):
    st.subheader(f"Marktanalyse: {strategy_name}")
    
    results = []
    for ticker in watchlist:
        m_data = get_market_info(ticker)
        if m_data:
            in_bezit = '✅' if ticker in portfolio else '⚪'
            rsi = round(m_data['rsi'], 2)
            price = round(m_data['price'], 2)
            
            # Signaal Logica
            if strategy_name == "Growth":
                signal = "🔥 BUY" if rsi < 35 else "🚀 HOLD"
                if rsi > 70: signal = "💰 TAKE PROFIT"
            else:
                signal = "💎 BUY" if rsi < 45 else "🛡️ HOLD"
            
            results.append({
                "Ticker": ticker,
                "In Bezit": in_bezit,
                "Prijs": f"€{price}",
                "RSI": rsi,
                "Signaal": signal,
                "Status": "Portefeuille" if ticker in portfolio else "Markt"
            })
    
    if results:
        res_df = pd.DataFrame(results)
        # Styling toepassen
        styled_df = res_df.style.apply(style_ticker, axis=1).applymap(color_signal, subset=['Signaal'])
        st.dataframe(styled_df, use_container_width=True, hide_index=True)

    # Snel toevoegen onder de tabel
    with st.expander("➕ Nieuwe positie toevoegen aan Airtable"):
        with st.form(f"add_{strategy_name}"):
            c1, c2, c3 = st.columns(3)
            t = c1.text_input("Ticker").upper()
            i = c2.number_input("Inleg (€)", 100)
            k = c3.number_input("Aankoopkoers", 0.0)
            if st.form_submit_button("Opslaan naar Airtable"):
                requests.post(URL, headers=HEADERS, json={"fields": {"Ticker": t, "Inleg": i, "Koers": k, "Type": strategy_name}})
                st.rerun()

with tab1: scan_market(WATCHLIST_GROWTH, "Growth", 35)
with tab2: scan_market(WATCHLIST_DIVIDEND, "Dividend", 45)

st.sidebar.info("✅ = In bezit\n⚪ = Markt verkenning")