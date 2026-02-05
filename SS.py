import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time
import os

# 1. Pagina configuratie
st.set_page_config(page_title="Stability Investor Pro", layout="wide")

# Bestandsnaam voor opslag
PF_FILE = "stability_portfolio.csv"

def load_pf():
    if os.path.exists(PF_FILE):
        try:
            return pd.read_csv(PF_FILE).to_dict('records')
        except:
            return []
    return []

def save_pf(data):
    pd.DataFrame(data).to_csv(PF_FILE, index=False)

# Initialiseer sessiegeheugen
if 'pf_data' not in st.session_state:
    st.session_state.pf_data = load_pf()

# --- SIDEBAR: PORTFOLIO BEHEER ---
st.sidebar.header("🏦 Lange Termijn Inleg")
with st.sidebar.form("invul_form", clear_on_submit=True):
    t_in = st.text_input("Ticker (bijv. AAPL)").upper().strip()
    b_in = st.number_input("Totaal Ingelegd Bedrag ($)", min_value=0.0, step=10.0)
    p_in = st.number_input("Gemiddelde Aankoopprijs ($)", min_value=0.01, step=0.1)
    submit = st.form_submit_button("Voeg toe aan Portfolio")

if submit and t_in:
    st.session_state.pf_data.append({
        "Ticker": t_in,
        "Inleg": b_in,
        "Prijs": p_in
    })
    save_pf(st.session_state.pf_data)
    st.sidebar.success(f"{t_in} toegevoegd!")
    st.rerun()

if st.sidebar.button("🗑️ Wis Portfolio"):
    st.session_state.pf_data = []
    if os.path.exists(PF_FILE):
        os.remove(PF_FILE)
    st.rerun()

# --- MAIN APP ---
st.title("📈 Dividend Stability & Quality Scanner")
st.markdown("*Focus op de lange termijn: Stabiliteit, MA200-trend en Payout Ratio.*")

markt_tickers = [
    'KO', 'PEP', 'JNJ', 'O', 'PG', 'ABBV', 'CVX', 'XOM', 'MMM', 'T',
    'VZ', 'WMT', 'LOW', 'TGT', 'ABT', 'MCD', 'MSFT', 'AAPL', 'IBM',
    'HD', 'COST', 'LLY', 'PFE', 'MRK', 'UNH', 'BMY', 'SBUX', 'CAT', 'DE',
    'NEE', 'PM', 'MO', 'BLK', 'V', 'MA', 'AVGO', 'TXN', 'JPM', 'SCHW'
]

mijn_tickers = [str(p['Ticker']).upper() for p in st.session_state.pf_data]
alle_tickers = list(set(markt_tickers + mijn_tickers))

@st.cache_data(ttl=3600)
def get_stability_data(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="2y")
        if h.empty: 
            return None
        i = tk.info
        # De gecorrigeerde dictionary:
        return {
            "h": h, 
            "div": (i.get('dividendYield', 0) or 0) * 100,
            "payout": (i.get('payoutRatio', 0) or 0) * 100,
            "sector": i.get('sector', 'N/B'),
            "price": h['Close'].iloc[-1]
        }
    except:
        return None

scanner_res, pf_res = [], []
balk = st.progress(0)

for n, s in enumerate(alle_tickers):
    data = get_stability_data(s)
    if data:
        p, h = data['price'], data['h']
        rsi = ta.rsi(h['Close'], length=14).iloc[-1]
        ma200 = h['Close'].tail(200).mean()
        ma50 = h['Close'].tail(50).mean()
        
        is_bullish = p > ma200 and ma50 > ma200
        if is_bullish and rsi < 42: adv = "💎 STERKE KOOP"
        elif is_bullish and rsi > 75: adv = "⚠️
