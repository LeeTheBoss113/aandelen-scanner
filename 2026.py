import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="Daytrade Dashboard Pro 2026")
API_URL = "https://script.google.com/macros/s/AKfycbyhZxfS0WjCo-oT9n1j9fXrGd5Y7gE2ymU2g2SNSBv49P0be9W6ySsKFgc7QjCySnKm/exec"

# --- STYLING FUNCTIE ---
def style_action(val):
    if val == 'BUY': color = '#2ecc71'  # Groen
    elif val == 'SELL': color = '#e74c3c'  # Rood
    elif val == 'WAIT': color = '#f1c40f'  # Geel
    else: color = '#3498db'  # Blauw
    return f'background-color: {color}; color: white; font-weight: bold'

# --- DATA LADEN UIT GOOGLE (VERBETERD) ---
def get_sheet_data():
    try:
        # Cache-buster voorkomt oude data
        r = requests.get(f"{API_URL}?t={int(time.time())}", timeout=10)
        data = r.json()
        
        # Als de sheet leeg is of alleen headers heeft
        if not data or len(data) < 2: 
            return pd.DataFrame(columns=["Ticker", "Inleg", "Koers"])
        
        # We negeren de headers uit de sheet en dwingen eigen namen af
        # Dit voorkomt de KeyError: 'Ticker'
        df = pd.DataFrame(data[1:]) # Pak alles vanaf rij 2
        df = df.iloc[:, :3] # Pak alleen de eerste 3 kolommen (A, B, C)
        df.columns = ["Ticker", "Inleg", "Koers"]
        
        # Data opschonen
        df['Ticker'] = df['Ticker'].astype(str).str.strip().str.upper()
        df['Inleg'] = pd.to_numeric(df['Inleg'], errors='coerce')
        df['Koers'] = pd.to_numeric(df['Koers'], errors='coerce')
        
        return df.dropna(subset=['Ticker'])
    except Exception as e:
        st.error(f"Fout bij ophalen Google Sheets: {e}")
        return pd.DataFrame(columns=["Ticker", "Inleg", "Koers"])

# --- MARKT DATA OPHALEN ---
@st.cache_data(ttl=300)
def fetch_market(tickers):
    results = {}
    if not tickers:
        return results
        
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
st.title("⚡ Pro Daytrade Connector 2026")

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
                    with st.spinner("Verzenden..."):
                        payload = {"ticker": t_in, "inleg": i_in, "koers": k_in}
                        requests.post(API_URL, data=json.dumps(payload))
                        st.success(f"{t_in} succesvol toegevoegd!")
                        time.sleep(1.5)
                        st.rerun()
                else:
                    st.error("Vul een geldige ticker en koers in.")

    with col_display:
        st.subheader("Huidige Live Portfolio")
        df_sheet = get_sheet_data()
        
        if not df_sheet.empty:
            # Haal unieke tickers op voor marktdata
            tickers_in_sheet = [t for t in df_sheet['Ticker'].unique().tolist() if t and t != 'NONE']
            
            if tickers_in_sheet:
                with st.spinner("Live koersen ophalen..."):
                    m_data = fetch_market(tickers_in_sheet)
                    
                    pf_list = []
                    for _, row in df_sheet.iterrows():
                        t = row['Ticker']
                        if t in m_data:
                            cur = m_data[t]
                            try:
                                inv = float(row['Inleg'])
                                buy = float(row['Koers'])
                                winst = ((inv / buy) * cur['price']) - inv
                                pf_list.append({
                                    "Ticker": t, 
                                    "Inleg": f"€{inv:.2f}", 
                                    "Koers": f"€{buy:.2f}", 
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
                                st.warning(f"{to_del} verwijderd uit Google Sheets.")
                                time.sleep(1.5)
                                st.rerun()
                    else:
                        st.info("Geen marktdata gevonden voor de tickers in je sheet.")
            else:
                st.info("Geen tickers gevonden in de sheet.")
        else:
            st.info("Je Google Sheet is leeg. Voeg een trade toe aan de linkerkant.")

with tab2:
    st.subheader("Top 25 Daytrade Scanner")
    watchlist = ['NVDA','TSLA','AAPL','MSFT','AMZN','META','AMD','NFLX','GOOGL','ASML.AS','ADYEN.AS','INGA.AS','SHELL.AS','PLTR','COIN','BABA','PLTR','DIS','PYPL']
    
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