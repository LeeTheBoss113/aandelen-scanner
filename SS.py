import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time
import os

# 1. Pagina configuratie
st.set_page_config(page_title="Stability Investor Pro", layout="wide")

# Bestandsnaam voor opslag van jouw lange termijn posities
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
    # Voeg toe aan de lijst in het geheugen
    st.session_state.pf_data.append({
        "Ticker": t_in,
        "Inleg": b_in,
        "Prijs": p_in
    })
    # Sla op in CSV voor de volgende keer
    save_pf(st.session_state.pf_data)
    st.sidebar.success(f"{t_in} succesvol toegevoegd!")
    st.rerun()

if st.sidebar.button("🗑️ Wis Portfolio"):
    st.session_state.pf_data = []
    if os.path.exists(PF_FILE):
        os.remove(PF_FILE)
    st.rerun()

# --- MAIN APP ---
st.title("📈 Dividend Stability & Quality Scanner")
st.markdown("*Focus op de lange termijn: Stabiliteit, MA200-trend en Payout Ratio.*")

# De vaste lijst met kwaliteitsaandelen
markt_tickers = [
    'KO', 'PEP', 'JNJ', 'O', 'PG', 'ABBV', 'CVX', 'XOM', 'MMM', 'T',
    'VZ', 'WMT', 'LOW', 'TGT', 'ABT', 'MCD', 'MSFT', 'AAPL', 'IBM',
    'HD', 'COST', 'LLY', 'PFE', 'MRK', 'UNH', 'BMY', 'SBUX', 'CAT', 'DE',
    'NEE', 'PM', 'MO', 'BLK', 'V', 'MA', 'AVGO', 'TXN', 'JPM', 'SCHW'
]

# Haal de tickers uit je eigen portfolio
mijn_tickers = [str(p['Ticker']).upper() for p in st.session_state.pf_data]

# Combineer alles tot een unieke lijst om te scannen
alle_tickers = list(set(markt_tickers + mijn_tickers))

@st.cache_data(ttl=3600)
def get_stability_data(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="2y") # 2 jaar historie voor MA200 berekening
        if h.empty: return None
        i = tk.info
        return {
            "h": h, 
            "div": (i.get('dividendYield', 0) or 0) * 100,
