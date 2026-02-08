import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import os

st.set_page_config(layout="wide", page_title="Stability Investor Pro")
F = "stability_portfolio.csv"

# 1. Data Functies
def ld():
    if not os.path.exists(F): return []
    try: return pd.read_csv(F).to_dict('records')
    except: return []

def sv(d):
    pd.DataFrame(d).to_csv(F, index=False)

if 'pf' not in st.session_state:
    st.session_state.pf = ld()

# 2. Sidebar Beheer
with st.sidebar:
    st.header("⚙️ Portfolio Beheer")
    with st.form("a", clear_on_submit=True):
        t = st.text_input("Ticker (bijv. MSFT)").upper().strip()
        i = st.number_input("Totale Inleg ($)", min_value=0.0, step=100.0)
        p = st.number_input("Aankoopkoers ($)", min_value=0.01, step=0.1)
        if st.form_submit_button("Aandeel Toevoegen"):
            if t:
                st.session_state.pf.append({"T":t,"I":i,"P":p})
                sv(st.session_state.pf)
                st.rerun()
    
    if st.session_state.pf:
        st.divider()
        for n, m in enumerate(st.session_state.pf):
            if st.sidebar.button(f"Verwijder {m['T']}", key=f"d{n}"):
                st.session_state.pf.pop(n)
                sv(st.session_state.pf)
                st.rerun()

# 3. Marktanalyse Config
ML = ['KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','MMM','T','VZ','WMT','LOW','TGT','ABT','MCD','MSFT','AAPL','IBM','HD','COST','LLY','PFE','MRK','UNH','BMY','SBUX','CAT','DE','NEE','PM','MO','BLK','V','MA','AVGO','TXN','JPM','SCHW']
AL = list(set(ML + [x['T'] for x in st.session_state.pf]))

@st.cache_data(ttl=900)
def gd(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="1y")
        if h.empty: return None
        return {"h":h, "i":tk.info, "p":h['Close'].iloc[-1]}
    except: return None

# 4. Data Verwerking
database = {}
pr, sr = [], []

with st.spinner('Marktgegevens ophal
