import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time
import os

st.set_page_config(page_title="Stability Investor Pro", layout="wide")

# Bestandsbeheer
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

# --- SIDEBAR ---
with st.sidebar:
    st.header("🏦 Portfolio Beheer")
    with st.form("invul_form", clear_on_submit=True):
        t_in = st.text_input("Ticker").upper().strip()
        b_in = st.number_input("Inleg ($)", min_value=0.0, step=10.0)
        p_in = st.number_input("Aankoopprijs ($)", min_value=0.01, step=0.1)
        submit = st.form_submit_button("➕ Toevoegen")

    if submit and t_in:
        st.session_state.pf_data.append({"Ticker": t_in, "Inleg": b_in, "Prijs": p_in})
        save_pf(st.session_state.pf_data)
        st.rerun()

    if st.button("🗑️ Wis Alles"):
        st.session_state.pf_data = []
        if os.path.exists(PF_FILE): os.remove(PF_FILE)
        st.rerun()

# --- DATA SCANNEN ---
markt_tickers = [
    'KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','MMM','T','VZ','WMT',
    'LOW','TGT','ABT','MCD','MSFT','AAPL','IBM','HD','COST','LLY','PFE',
    'MRK','UNH','BMY','SBUX','CAT','DE','NEE','PM','MO','BLK','V','MA',
    'AVGO','TXN','JPM','SCHW'
]

mijn_tickers_lijst = [str(p['Ticker']).upper() for p in st.session_state.pf_data]
alle_tickers = list(set(markt_tickers + mijn_tickers_lijst))

@st.cache_data(ttl=3600)
def get_data(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="2y")
        if h.empty: return None
        i = tk.info
        return {
            "h": h, 
            "div": (i.get('dividendYield', 0) or 0) * 100, 
            "payout": (i.get('payoutRatio', 0) or 0) * 100, 
            "sector": i.get('sector', 'N/B'), 
            "price": h['Close'].iloc[-1]
        }
    except: return None

scanner_res, pf_res = [], []
balk = st.progress(0)

for n, s in enumerate(alle_tickers):
    data = get_data(s)
    if data:
        p, h = data['price'], data['h']
        rsi = ta.rsi(h['Close'], length=14).iloc[-1] if len(h) > 14 else 50
        ma200 = h['Close'].tail(200).mean() if len(h) >= 200 else p
        
        # Status bepaling
        if p > ma200 and rsi < 42: adv = "KOOP"
        elif p > ma200 and rsi > 75: adv = "DUUR"
        elif p > ma200: adv = "STABIEL"
        else: adv = "WACHTEN"

        # Portfolio verwerking
        for entry in st.session_state.pf_data:
            if str(entry['Ticker']).upper() == s:
                inleg = float(entry['Inleg'])
                waarde = (inleg / float(entry['Prijs'])) * p
                pf_res.append({
                    "Ticker": s, 
                    "Inleg": inleg, 
                    "Waarde": waarde, 
                    "Winst": waarde-inleg, 
                    "Rendement %": ((waarde-inleg)/inleg)*100, 
                    "RSI": rsi, 
                    "Status": adv
                })

        # Scanner verwerking
        if s in markt_tickers:
            scanner_res.append({
                "Ticker": s, 
                "Sector": data['sector'], 
                "Status": adv, 
                "Div %": data['div'], 
                "Payout %": data['payout'], 
                "RSI": rsi
            })
    balk.progress((n + 1) / len(alle_tickers))

# --- DASHBOARD ---
st.title("📈 Stability Investor
