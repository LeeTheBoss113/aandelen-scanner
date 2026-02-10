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
    if val == 'BUY': color = '#2ecc71'
    elif val == 'SELL': color = '#e74c3c'
    elif val == 'WAIT': color = '#f1c40f'
    else: color = '#3498db'
    return f'background-color: {color}; color: white; font-weight: bold'

# --- DATA LADEN UIT GOOGLE ---
def get_sheet_data():
    try:
        r = requests.get(f"{API_URL}?t={int(time.time())}", timeout=10)
        data = r.json()
        if not data or len(data) < 2: 
            return pd.DataFrame(columns=["Ticker", "Inleg", "Koers"])
        df = pd.DataFrame(data[1:])
        df = df.iloc[:, :3] 
        df.columns = ["Ticker", "Inleg", "Koers"]
        df['Ticker'] = df['Ticker'].astype(str).str.strip().str.upper()
        df['Inleg'] = pd.to_numeric(df['Inleg'], errors='coerce')
        df['Koers'] = pd.to_numeric(df['Koers'], errors='coerce')
        return df.dropna(subset=['Ticker'])
    except:
        return pd.DataFrame(columns=["Ticker", "Inleg", "Koers"])

# --- MARKT DATA OPHALEN ---
@st.cache_data(ttl=300)
def fetch_market(tickers):
    results = {}
    if not tickers: return results
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            h = tk.history(period="1y")
            if h.empty: continue
            price = h['Close'].iloc[-1]
            rsi = ta.rsi(h['Close'], 14).iloc[-1]
            status = "WAIT"
            if rsi < 35: status = "BUY"
            elif rsi > 65: status = "SELL"
            p6m = h['Close'].iloc[-126] if len(h) > 126 else h['Close'].iloc[0]
            trend = ((price - p6m) / p6m) * 100
            results[t] = {"price": price, "rsi": rsi, "status": status, "trend": trend}
        except: continue
    return results

# --- UI OPBOUW ---
st.title("⚡ Pro Daytrade Connector 2026")

tab1, tab2 = st.tabs(["📊 Portfolio Beheer", "🔍 Market Scanner"])

with tab1:
    col_input, col_display = st.columns([1, 2.5])
    
    with col_input:
        st.subheader("Nieuwe Positie")
        with st.form("add_trade", clear_on_submit=True):
            t_in = st.text_input("Ticker (bv. NVDA)").upper().strip()
            i_in = st.number_input("Inleg (€)", value=100.0, step=50.0)
            k_in = st.number_input("Aankoopkoers", value=0.0, format="%.2f")
            if st.form_submit_button("Opslaan naar Google Sheets"):
                if t_in and k_in > 0:
                    payload = {"ticker": t_in, "inleg": i_in, "koers": k_in}
                    requests.post(API_URL, data=json.dumps(payload))
                    st.success(f"{t_in} toegevoegd!")
                    time.sleep(1)
                    st.rerun()

    with col_display:
        st.subheader("Huidige Live Portfolio")
        df_sheet = get_sheet_data()
        
        if not df_sheet.empty:
            tickers_in_sheet = [t for t in df_sheet['Ticker'].unique().tolist() if t and t != 'NONE']
            
            if tickers_in_sheet:
                m_data = fetch_market(tickers_in_sheet)
                pf_list = []
                total_inleg = 0
                total_waarde = 0
                
                for _, row in df_sheet.iterrows():
                    t = row['Ticker']
                    if t in m_data:
                        cur = m_data[t]
                        inv = float(row['Inleg'])
                        buy = float(row['Koers'])
                        huidige_waarde = (inv / buy) * cur['price']
                        winst = huidige_waarde - inv
                        
                        total_inleg += inv
                        total_waarde += huidige_waarde
                        
                        pf_list.append({
                            "Ticker": t, 
                            "Inleg": inv, 
                            "Aankoop": f"€{buy:.2f}", 
                            "Nu": round(cur['price'], 2), 
                            "Waarde": round(huidige_waarde, 2),
                            "Opbrengst": round(winst, 2), 
                            "Actie": cur['status']
                        })
                
                if pf_list:
                    # Totaaloverzicht bovenaan
                    c_m1, c_m2, c_m3 = st.columns(3)
                    total_pnl = total_waarde - total_inleg
                    c_m1.metric("Totale Inleg", f"€{total_inleg:.2f}")
                    c_m2.metric("Huidige Waarde", f"€{total_waarde:.2f}")
                    c_m3.metric("Totaal Rendement", f"€{total_pnl:.2f}", delta=f"{((total_pnl/total_inleg)*100 if total_inleg > 0 else 0):.2f}%")
                    
                    st.divider()
                    
                    df_final = pd.DataFrame(pf_list)
                    # We maken de kolommen mooi op
                    st.dataframe(
                        df_final.style.map(style_action, subset=['Actie'])
                        .format({"Inleg": "€{:.2f}", "Waarde": "€{:.2f}", "Opbrengst": "€{:.2f}"}), 
                        hide_index=True, use_container_width=True
                    )
                    
                    st.divider()
                    to_del = st.selectbox("Ticker verwijderen?", [""] + df_final['Ticker'].tolist())
                    if st.button("🗑️ Verwijder uit Sheet"):
                        if to_del:
                            requests.post(API_URL, data=json.dumps({"method": "delete", "ticker": to_del}))
                            st.rerun()
            else:
                st.info("Geen marktdata beschikbaar.")
        else:
            st.info("De Google Sheet is leeg.")

with tab2:
    st.subheader("Top 25 Daytrade Scanner")
    watchlist = ['NVDA','TSLA','AAPL','MSFT','AMZN','META','AMD','NFLX','GOOGL','ASML.AS','ADYEN.AS','INGA.AS','SHELL.AS','PLTR','COIN','BABA']
    m_watch = fetch_market(watchlist)
    scan_rows = [{"Ticker": k, "Prijs": round(v['price'], 2), "RSI": round(v['rsi'], 1), "6M Trend": f"{v['trend']:.1f}%", "Actie": v['status']} for k, v in m_watch.items()]
    if scan_rows:
        st.dataframe(pd.DataFrame(scan_rows).sort_values('RSI').style.map(style_action, subset=['Actie']), hide_index=True, use_container_width=True)