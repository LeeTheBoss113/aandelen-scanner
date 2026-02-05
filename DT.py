import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time
import os

# --- 1. SETUP ---
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

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Beheer")
    with st.form("add_stock", clear_on_submit=True):
        t_in = st.text_input("Ticker").upper().strip()
        i_in = st.number_input("Inleg ($)", min_value=0.0, step=10.0)
        p_in = st.number_input("Aankoop ($)", min_value=0.01, step=0.1)
        if st.form_submit_button("➕ Toevoegen"):
            if t_in:
                st.session_state.pf_data.append(
                    {"Ticker": t_in, "Inleg": i_in, "Prijs": p_in}
                )
                save_pf(st.session_state.pf_data)
                st.rerun()

    if st.session_state.pf_data:
        st.divider()
        for n, item in enumerate(st.session_state.pf_data):
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{item['Ticker']}**")
            if c2.button("❌", key=f"del_{n}"):
                st.session_state.pf_data.pop(n)
                save_pf(st.session_state.pf_data)
                st.rerun()

# --- 3. DATA ENGINE ---
m_list = ['KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','MMM',
          'T','VZ','WMT','LOW','TGT','ABT','MCD','MSFT','AAPL',
          'IBM','HD','COST','LLY','PFE','MRK','UNH','BMY',
          'SBUX','CAT','DE','NEE','PM','MO','BLK','V','MA',
          'AVGO','TXN','JPM','SCHW']
a_list = list(set(m_list + [x['Ticker'] for x in st.session_state.pf_data]))

@st.cache_data(ttl=3600)
def get_stock(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="2y")
        if h.empty: return None
        return {"h": h, "i": tk.info, "p": h['Close'].iloc[-1]}
    except: return None

pf_res, sc_res = [], []
pb = st.progress(0)

for i, t in enumerate(a_list):
    d = get_stock(t)
    if d:
        p, h, inf = d['p'], d['h'], d['i']
        # RSI afronden op 1 decimaal
        rsi_raw = ta.rsi(h['Close'], 14).iloc[-1] if len(h) > 14 else 50
        rsi = round(rsi_raw, 1)
        
        ma = h['Close'].tail(200).mean() if len(h) >= 200 else p
        
        stt = "WACHTEN"
        if p > ma:
            stt = "STABIEL"
            if rsi < 42: stt = "KOOP"
            if rsi > 75: stt = "DUUR"

        for pi in st.session_state.pf_data:
            if pi['Ticker'] == t:
                aantal = pi['Inleg'] / pi['Prijs']
                waarde = aantal * p
                winst = waarde - pi['Inleg']
                pf_res.append({
                    "Ticker": t, "Inleg": pi['Inleg'], "Koers": p, 
                    "Waarde": waarde, "Winst": winst, "Status": stt
                })

        if t in m_list:
            sc_res.append({
                "Ticker": t, "Koers": p, "Sector": inf.get('sector', 'N/B'), 
                "Div": (inf.get('dividendYield', 0) or 0) * 100,
                "Pay
