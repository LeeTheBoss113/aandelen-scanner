import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="Daytrade Dashboard Pro")
API_URL = "https://script.google.com/macros/s/AKfycbyhZxfS0WjCo-oT9n1j9fXrGd5Y7gE2ymU2g2SNSBv49P0be9W6ySsKFgc7QjCySnKm/exec"

# --- STYLING FUNCTIE ---
def style_action(val):
    if val == 'BUY': color = '#2ecc71'  # Groen
    elif val == 'SELL': color = '#e74c3c'  # Rood
    elif val == 'WAIT': color = '#f1c40f'  # Geel
    else: color = '#3498db'  # Blauw
    return f'background-color: {color}; color: white; font-weight: bold'

# --- DATA LADEN UIT GOOGLE ---
def get_sheet_data():
    try:
        # De 't=' timestamp voorkomt dat Google oude (gecachete) data stuurt
        r = requests.get(f"{API_URL}?t={int(time.time())}", timeout=10)
        data = r.json()
        if len(data) < 2: 
            return pd.DataFrame(columns=["Ticker", "Inleg", "Koers"])
        # Gebruik de eerste rij als kolomnamen
        df = pd.DataFrame(data[1:], columns=data[0])
        return df
    except Exception as e:
        return pd.DataFrame(columns=["Ticker", "Inleg", "Koers"])

# --- MARKT DATA OPHALEN ---
@st.cache_data(ttl=300)
def fetch_market(tickers):
    results = {}
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            h = tk.history(period="1y")
            if h.empty: continue
            price = h['Close'].iloc[-1]
            rsi = ta.rsi(h['Close'], 14).iloc[-1]
            
            # Daytrade Logica
            status = "WAIT"
            if rsi < 35: status = "BUY"
            elif rsi > 65: status = "SELL"
            
            # Trend 6 maanden
            p6m = h['Close'].iloc[-126] if len(h) > 126 else h['Close'].iloc[0]
            trend = ((price - p6m) / p6m) * 100
            
            results[t] = {"price": price, "rsi": rsi, "status": status, "trend": trend}
        except: continue
    return results

# --- UI OPBOUW ---
st.title("⚡ Pro Daytrade Connector")

# Data ophalen bij start
df_sheet = get_sheet_data()

tab1, tab2 = st.tabs(["📊 Portfolio Beheer", "🔍 Market Scanner"])

with tab1:
    col_input, col_display = st.columns([1, 2])
    
    with col_input:
        st.subheader("Nieuwe Positie")
        with st.form("add_trade", clear_on_submit=True):
            t_in = st.text_input("Ticker (bv. NVDA)").upper().strip()
            i_in = st.number_input("Inleg (€)", value=100.0, step=50.0)
            k_in = st.number_input("Aankoopkoers", value=0.0, format="%.2f")
            if st.form_submit_button("Opslaan naar Google Sheets"):
                if t_in and k_in > 0:
                    with st.spinner("Opslaan..."):
                        payload = {"ticker": t_in, "inleg": i_in, "koers": k_in}
                        requests.post(API_URL, data=json.dumps(payload))
                        st.success(f"{t_in} toegevoegd aan je Sheet!")
                        time.sleep(1)
                        st.rerun()
                else:
                    st.error("Vul een geldige ticker en koers in.")

    with col_display:
        st.subheader("Huidige Live Portfolio")
        if not df_sheet.empty and len(df_sheet) > 0:
            # Tickers uit de sheet halen voor live koersen
            tickers_in_sheet = df_sheet['Ticker'].unique().tolist()
            m_data = fetch_market(tickers_in_sheet)
            
            pf_list = []
            for _, row in df_sheet.iterrows():
                t = str(row['Ticker']).strip().upper()
                if t in m_data:
                    cur = m_data[t]
                    try:
                        inv = float(row['Inleg'])
                        buy = float(row['Koers'])
                        winst = ((inv / buy) * cur['price']) - inv
                        pf_list.append({
                            "Ticker": t, 
                            "Inleg": inv, 
                            "Koers": buy, 
                            "Nu": round(cur['price'], 2), 
                            "Winst": round(winst, 2), 
                            "Actie": cur['status']
                        })
                    except: continue
            
            if pf_list:
                df_final = pd.DataFrame(pf_list)
                st.dataframe(df_final.style.map(style_action, subset=['Actie']), hide_index=True, use_container_width=True)
                
                st.divider()
                # Verwijder functionaliteit
                to_del = st.selectbox("Selecteer ticker om te verwijderen", [""] + df_final['Ticker'].tolist())
                if st.button("🗑️ Verwijder geselecteerde ticker"):
                    if to_del:
                        requests.post(API_URL, data=json.dumps({"method": "delete", "ticker": to_del}))
                        st.warning(f"{to_del} verwijderd.")
                        time.sleep(1)
                        st.rerun()
            else:
                st.info("Wachten op marktdata voor je tickers...")
        else:
            st.info("Je Google Sheet is momenteel leeg. Voeg een trade toe aan de linkerkant.")

with tab2:
    st.subheader("Top 25 Daytrade Scanner")
    # Jouw selectie van top aandelen
    watchlist = ['NVDA','TSLA','AAPL','MSFT','AMZN','META','AMD','NFLX','GOOGL','ASML.AS','ADYEN.AS','INGA.AS','SHELL.AS','PLTR','COIN','BABA']
    
    with st.spinner("Markt scannen..."):
        m_watch = fetch_market(watchlist)
        scan_rows = []
        for k, v in m_watch.items():
            scan_rows.append({
                "Ticker": k, 
                "Prijs": round(v['price'], 2), 
                "RSI": round(v['rsi'], 1), 
                "6M Trend": f"{v['trend']:.1f}%", 
                "Actie": v['status']
            })
        
        if scan_rows:
            scan_df = pd.DataFrame(scan_rows).sort_values('RSI')
            st.dataframe(scan_df.style.map(style_action, subset=['Actie']), hide_index=True, use_container_width=True)