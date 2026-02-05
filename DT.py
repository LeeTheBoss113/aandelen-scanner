import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time
import os

# --- 1. CONFIGURATIE ---
st.set_page_config(page_title="Stability Investor Pro", layout="wide")

PF_FILE = "stability_portfolio.csv"

def load_pf():
    if os.path.exists(PF_FILE):
        try: return pd.read_csv(PF_FILE).to_dict('records')
        except: return []
    return []

def save_pf(data):
    pd.DataFrame(data).to_csv(PF_FILE, index=False)

if 'pf_data' not in st.session_state:
    st.session_state.pf_data = load_pf()

# --- 2. SIDEBAR BEHEER ---
with st.sidebar:
    st.header("⚙️ Beheer")
    with st.form("add_stock", clear_on_submit=True):
        t_in = st.text_input("Ticker").upper().strip()
        b_in = st.number_input("Inleg ($)", min_value=0.0, step=10.0)
        p_in = st.number_input("Aankoopprijs ($)", min_value=0.01, step=0.1)
        if st.form_submit_button("➕ Toevoegen"):
            if t_in:
                st.session_state.pf_data.append({"Ticker": t_in, "Inleg": b_in, "Prijs": p_in})
                save_pf(st.session_state.pf_data)
                st.rerun()

    st.divider()
    if st.session_state.pf_data:
        st.subheader("🗑️ Verwijderen")
        for i, item in enumerate(st.session_state.pf_data):
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{item['Ticker']}**")
            if c2.button("❌", key=f"del_{i}"):
                st.session_state.pf_data.pop(i)
                save_pf(st.session_state.pf_data)
                st.rerun()
    
    if st.button("🚨 Wis Alles"):
        st.session_state.pf_data = []
        if os.path.exists(PF_FILE): os.remove(PF_FILE)
        st.rerun()

# --- 3. DATA ENGINE ---
markt_list = ['KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','MMM','T','VZ','WMT','LOW','TGT','ABT','MCD','MSFT','AAPL','IBM','HD','COST','LLY','PFE','MRK','UNH','BMY','SBUX','CAT','DE','NEE','PM','MO','BLK','V','MA','AVGO','TXN','JPM','SCHW']
mijn_list = [p['Ticker'] for p in st.session_state.pf_data]
alle_tickers = list(set(markt_list + mijn_list))

@st.cache_data(ttl=3600)
def fetch_stock_data(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="2y")
        if h.empty: return None
        return {"h": h, "info": tk.info, "price": h['Close'].iloc[-1]}
    except: return None

pf_results, market_results = [], []
progress_bar = st.progress(0)

for i, ticker in enumerate(alle_tickers):
    data = fetch_stock_data(ticker)
    if data:
        p, h, inf = data['price'], data['h'], data['info']
        rsi = ta.rsi(h['Close'], length=14).iloc[-1] if len(h) > 14 else 50
        ma200 = h['Close'].tail(200).mean() if len(h) >= 200 else p
        
        status = "STABIEL" if p > ma200 else "WACHTEN"
        if p > ma200 and rsi < 42: status = "KOOP"
        if p > ma200 and rsi > 75: status = "DUUR"

        for p_item in st.session_state.pf_data:
            if p_item['Ticker'] == ticker:
                w = (p_item['Inleg'] / p_item['Prijs']) * p
                pf_results.append({
                    "Ticker": ticker, "Inleg": p_item['Inleg'], "Prijs": p,
                    "Waarde": w, "Winst": w - p_item['Inleg'], "Status": status
                })

        if ticker in markt_
