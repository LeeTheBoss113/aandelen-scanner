import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time
import os

st.set_page_config(page_title="Stability Investor", layout="wide")

# Bestandsbeheer voor je portfolio
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
st.sidebar.header("Lange Termijn Inleg")
with st.sidebar.form("invul_form", clear_on_submit=True):
    t_in = st.text_input("Ticker (bijv. KO)").upper().strip()
    b_in = st.number_input("Inleg ($)", min_value=0.0)
    p_in = st.number_input("Aankoopprijs ($)", min_value=0.01)
    submit = st.form_submit_button("Voeg toe aan Portfolio")

if submit and t_in:
    st.session_state.pf_data.append({"Ticker": t_in, "Inleg": b_in, "Prijs": p_in})
    save_pf(st.session_state.pf_data)
    st.rerun()

if st.sidebar.button("Wis Portfolio"):
    st.session_state.pf_data = []
    if os.path.exists(PF_FILE): os.remove(PF_FILE)
    st.rerun()

# --- DATA SCANNEN ---
markt_tickers = ['KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','MMM','T','VZ','WMT','LOW','TGT','ABT','MCD','MSFT','AAPL','IBM','HD','COST','LLY','PFE','MRK','UNH','BMY','SBUX','CAT','DE','NEE','PM','MO','BLK','V','MA','AVGO','TXN','JPM','SCHW']

# Zorg dat we altijd de unieke lijst van tickers hebben
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

if alle_tickers:
    for n, s in enumerate(alle_tickers):
        data = get_data(s)
        if data:
            p, h = data['price'], data['h']
            
            # Bereken indicatoren
            rsi = ta.rsi(h['Close'], length=14).iloc[-1] if len(h) > 14 else 50
            ma200 = h['Close'].tail(200).mean() if len(h) >= 200 else p
            ma50 = h['Close'].tail(50).mean() if len(h) >= 50 else p
            
            # Bepaal Status
            is_bullish = p > ma200
            if is_bullish and rsi < 42: adv = "KOOP"
            elif is_bullish and rsi > 75: adv = "DUUR"
            elif is_bullish: adv = "STABIEL"
            else: adv = "AFWACHTEN"

            # Check voor Portfolio
            for entry in st.session_state.pf_data:
                if str(entry['Ticker']).upper() == s:
                    inleg = float(entry['Inleg'])
                    prijs_toen = float(entry['Prijs'])
                    waarde = (inleg / prijs_toen) * p
                    pf_res.append({
                        "Ticker": s,
                        "Inleg": round(inleg, 2),
                        "Waarde": round(waarde, 2),
                        "Winst": round(waarde - inleg, 2),
                        "Rendement %": round(((waarde - inleg)/inleg)*100, 1) if inleg > 0 else 0,
                        "Status": adv
                    })

            # Check voor Scanner (alleen als in de 40-lijst)
            if s in markt_tickers:
                scanner_res.append({
                    "Ticker": s, 
                    "Sector": data['sector'], 
                    "Status": adv, 
                    "Div %": round(data['div'], 2), 
                    "Payout %": round(data['payout'], 1),
                    "RSI": round(rsi, 1)
                })
        balk.progress((n + 1) / len(alle_tickers))

# --- DASHBOARD WEERGAVE ---
st.title("📈 Stability Investor Dashboard")

# Sectie 1: Jouw Portfolio
st.subheader("Mijn Open Posities")
if pf_res:
    st.dataframe(pd.DataFrame(pf_res), use_container_width=True, hide_index=True)
else:
    st.write("Geen actieve posities gevonden. Voeg een ticker toe in de zijbalk.")

st.divider()

# Sectie 2: De Markt Scanner
st.subheader("Lange Termijn Markt Scanner")
if scanner_res:
    st.dataframe(pd.DataFrame(scanner_res).sort_values("Div %", ascending=False), use_container_width=True, hide_index=True)
else:
    st.error("Er kon geen marktdata worden opgehaald. Controleer je internetverbinding of herstart de app.")

time.sleep(900)
st.rerun()
