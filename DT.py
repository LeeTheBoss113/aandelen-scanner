import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time
import os

st.set_page_config(page_title="Stability Investor Pro", layout="wide")

PF_FILE = "stability_portfolio.csv"

def load_pf():
    if os.path.exists(PF_FILE):
        try: return pd.read_csv(PF_FILE).to_dict('records')
        except: return []
    return []

def save_pf(d):
    pd.DataFrame(d).to_csv(PF_FILE, index=False)

if 'pf_data' not in st.session_state:
    st.session_state.pf_data = load_pf()

# --- SIDEBAR BEHEER ---
with st.sidebar:
    st.header("⚙️ Beheer")
    with st.form("add_stock", clear_on_submit=True):
        t_in = st.text_input("Ticker").upper().strip()
        b_in = st.number_input("Inleg ($)", min_value=0.0, step=10.0)
        p_in = st.number_input("Aankoop ($)", min_value=0.01, step=0.1)
        if st.form_submit_button("➕ Toevoegen"):
            if t_in:
                st.session_state.pf_data.append({"Ticker": t_in, "Inleg": b_in, "Prijs": p_in})
                save_pf(st.session_state.pf_data)
                st.rerun()

    if st.session_state.pf_data:
        st.divider()
        for i, item in enumerate(st.session_state.pf_data):
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{item['Ticker']}**")
            if c2.button("❌", key=f"del_{i}"):
                st.session_state.pf_data.pop(i)
                save_pf(st.session_state.pf_data)
                st.rerun()

# --- DATA ENGINE ---
m_list = ['KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','MMM','T','VZ','WMT','LOW','TGT','ABT','MCD','MSFT','AAPL','IBM','HD','COST','LLY','PFE','MRK','UNH','BMY','SBUX','CAT','DE','NEE','PM','MO','BLK','V','MA','AVGO','TXN','JPM','SCHW']
a_list = list(set(m_list + [p['Ticker'] for p in st.session_state.pf_data]))

@st.cache_data(ttl=3600)
def get_data(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="2y")
        if h.empty: return None
        return {"h": h, "i": tk.info, "p": h['Close'].iloc[-1]}
    except: return None

pf_res, sc_res = [], []
pb = st.progress(0)

for i, t in enumerate(a_list):
    d = get_data(t)
    if d:
        p, h, inf = d['p'], d['h'], d['i']
        rsi = ta.rsi(h['Close'], length=14).iloc[-1] if len(h) > 14 else 50
        ma = h['Close'].tail(200).mean() if len(h) >= 200 else p
        
        stt = "STABIEL" if p > ma else "WACHTEN"
        if p > ma and rsi < 42: stt = "KOOP"
        if p > ma and rsi > 75: stt = "DU
