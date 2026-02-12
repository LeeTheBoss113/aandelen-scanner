import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG ---
AIRTABLE_TOKEN = "JOUW_PAT_TOKEN_HIER"
BASE_ID = "JOUW_BASE_ID_HIER"
TABLE_NAME = "Portfolio"

URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
HEADERS = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}

st.set_page_config(layout="wide", page_title="Market Scanner 2026")

# --- STYLING ---
def color_signal(val):
    if 'BUY' in val: color = '#27ae60'
    elif 'SELL' in val: color = '#e74c3c'
    elif 'HOLD' in val: color = '#f39c12'
    else: color = '#34495e'
    return f'background-color: {color}; color: white; font-weight: bold'

# --- DATA FUNCTIES ---
def get_data():
    try:
        r = requests.get(f"{URL}?t={int(time.time())}", headers=HEADERS).json()
        records = r.get('records', [])
        if not records: return pd.DataFrame()
        rows = []
        for r in records:
            row = r['fields']
            row['airtable_id'] = r['id']
            rows.append(row)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

def get_market_data(ticker):
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="60d")
        if df.empty: return None
        current_price = df['Close'].iloc[-1]
        rsi = ta.rsi(df['Close'], length=14).iloc[-1]
        return {"price": round(current_price, 2), "rsi": round(rsi, 2)}
    except: return None

# --- UI ---
st.title("📊 Smart Market Scanner 2026")
df = get_data()

# Tabs
tab1, tab2 = st.tabs(["🚀 Growth (Fast Profit)", "💎 Dividend (Long Term)"])

def render_strategy(strategy_name, rsi_buy_threshold):
    col1, col2 = st.columns([1, 2])
    
    # Filter data
    strat_df = pd.DataFrame()
    if not df.empty and 'Type' in df.columns:
        strat_df = df[df['Type'] == strategy_name].copy()

    with col1:
        st.subheader(f"Toevoegen: {strategy_name}")
        with st.form(f"add_{strategy_name}"):
            t_in = st.text_input("Ticker").upper().strip()
            i_in = st.number_input("Inleg (€)", 100)
            k_in = st.number_input("Aankoopkoers", 0.0)
            if st.form_submit_button("Opslaan"):
                requests.post(URL, headers=HEADERS, json={"fields": {"Ticker": t_in, "Inleg": i_in, "Koers": k_in, "Type": strategy_name}})
                st.rerun()

    with col2:
        st.subheader(f"Scanner Resultaten: {strategy_name}")
        if not strat_df.empty:
            # Analyse uitvoeren
            analysis = []
            for _, row in strat_df.iterrows():
                m_data = get_market_data(row['Ticker'])
                if m_data:
                    rsi = m_data['rsi']
                    p_diff = ((m_data['price'] - row['Koers']) / row['Koers']) * 100 if row['Koers'] > 0 else 0
                    
                    # Signaal Logica
                    if strategy_name == "Growth":
                        signal = "🔥 BUY (Oversold)" if rsi < 30 else "🚀 HOLD"
                        if rsi > 70 or p_diff > 10: signal = "💰 SELL (Take Profit)"
                    else: # Dividend
                        signal = "💎 BUY (Good Entry)" if rsi < 45 else "🛡️ HOLD"
                        if rsi > 75: signal = "⚠️ OVERBOUGHT"

                    analysis.append({
                        "Ticker": row['Ticker'],
                        "Inleg": f"€{row['Inleg']}",
                        "Huidig": f"€{m_data['price']}",
                        "Rendement": f"{p_diff:.2f}%",
                        "RSI": rsi,
                        "Signaal": signal
                    })
            
            if analysis:
                res_df = pd.DataFrame(analysis)
                st.dataframe(res_df.style.applymap(color_signal, subset=['Signaal']), use_container_width=True, hide_index=True)
        else:
            st.info("Geen aandelen gevonden in deze categorie.")

with tab1: render_strategy("Growth", 30)
with tab2: render_strategy("Dividend", 45)