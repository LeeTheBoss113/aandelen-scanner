import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time
import os

# 1. Pagina configuratie
st.set_page_config(page_title="Dividend Trader Pro", layout="wide")

# Bestandsnaam voor opslag
PF_FILE = "mijn_posities.csv"

# Functies voor dataopslag
def laad_pf():
    if os.path.exists(PF_FILE):
        return pd.read_csv(PF_FILE).to_dict('records')
    return []

def schrijf_pf(data):
    pd.DataFrame(data).to_csv(PF_FILE, index=False)

# Sessiebeheer
if 'mijn_data' not in st.session_state:
    st.session_state.mijn_data = laad_pf()

# --- SIDEBAR: INTERACTIEVE INVULVELDEN ---
st.sidebar.header("📥 Trade Invoeren (Trade 212)")
with st.sidebar.form("invul_form", clear_on_submit=True):
    t_in = st.text_input("Ticker (bijv. O of KO)").upper()
    b_in = st.number_input("Ingelegd Bedrag ($)", min_value=0.0, step=10.0)
    p_in = st.number_input("Gem. Aankoopprijs ($)", min_value=0.0, step=0.01)
    stuur = st.form_submit_button("Voeg toe aan Portfolio")

if stuur and t_in:
    st.session_state.mijn_data.append({"Ticker": t_in, "Inleg": b_in, "Prijs": p_in})
    schrijf_pf(st.session_state.mijn_data)
    st.sidebar.success(f"{t_in} toegevoegd!")

if st.sidebar.button("🗑️ Wis Portfolio"):
    st.session_state.mijn_data = []
    if os.path.exists(PF_FILE): os.remove(PF_FILE)
    st.rerun()

# --- MAIN APP ---
st.title("🛡️ Dividend Trader & Portfolio")
st.write("Laatste update:", time.strftime('%H:%M:%S'))

# De 50 standaard tickers
markt_tickers = [
    'KO', 'PEP', 'JNJ', 'O', 'PG', 'ABBV', 'CVX', 'XOM', 'MMM', 'T',
    'VZ', 'WMT', 'LOW', 'TGT', 'ABT', 'MCD', 'ADBE', 'MSFT', 'AAPL', 'IBM',
    'HD', 'COST', 'LLY', 'PFE', 'MRK', 'DHR', 'UNH', 'BMY', 'AMGN', 'SBUX',
    'CAT', 'DE', 'HON', 'UPS', 'FDX', 'NEE', 'SO', 'D', 'DUK', 'PM',
    'MO', 'SCHW', 'BLK', 'SPGI', 'V', 'MA', 'AVGO', 'TXN', 'NVDA', 'JPM'
]

# Voeg portfolio tickers toe aan de scanlijst als ze er nog niet in staan
alle_tickers = list(set(markt_tickers + [p['Ticker'] for p in st.session_state.mijn_data]))

@st.cache_data(ttl=3600)
def haal_data(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="1y")
        if h.empty: return None
        i = tk.info
        return {
            "h": h, "d": (i.get('dividendYield', 0) or 0) * 100,
            "s": i.get('sector', 'N/B'), "p": h['Close'].iloc[-1],
            "t": i.get('targetMeanPrice', None)
        }
    except: return None

scanner_res, pf_res = [], []
balk = st.progress(0)

# De grote scan ronde
for n, s in enumerate(alle_tickers):
    data = haal_data(s)
    if data:
        prijs, hist = data['p'], data['h']
        rsi = ta.rsi(hist['Close'], length=14).iloc[-1]
        m1y, m6m = hist['Close'].mean(), hist['Close'].tail(126).mean()
        
        # Trends & Advies
        t1y, t6m = ("✅" if prijs > m1y else "❌"), ("✅" if prijs > m6m else "❌")
        if t1y == "✅" and t6m == "✅" and rsi < 45: adv = "🌟 KOOP DIP"
        elif t1y == "✅" and rsi > 70: adv = "💰 WINST"
        elif t1y == "✅": adv = "🟢 HOLD"
        else: adv = "🔴 NEE"

        # Check of ticker in portfolio zit
        for p in st.session_state.mijn_data:
            if p['Ticker'] == s:
                waarde = (p['Inleg'] / p['Prijs']) * prijs
                pf_res.append({
                    "Ticker": s, "Inleg": p['Inleg'], "Waarde": round(waarde, 2),
                    "Resultaat": round(waarde - p['Inleg'], 2), 
                    "%": round(((waarde - p['Inleg'])/p['Inleg'])*100, 1),
                    "RSI": round(rsi, 1), "Status": adv
                })

        # Alleen in scanner als het in de lijst van 50 staat
        if s in markt_tickers:
            scanner_res.append({
                "Ticker": s, "Sector": data['s'], "Status": adv, 
                "Prijs": round(prijs, 2), "Div%": round(data['d'], 2), "RSI": round(rsi, 1)
            })
    balk.progress((n + 1) / len(alle_tickers))

# --- DASHBOARD WEERGAVE ---

# 1. Portfolio Overzicht
if pf_res:
    st.subheader("📊 Mijn Open Posities")
    df_pf = pd.DataFrame(pf_res)
    totaal = sum([x['Resultaat'] for x in pf_res])
    st.metric("Totaal Winst/Verlies", f"$ {totaal:.2f}", delta=f"{totaal:.2f}")
    st.dataframe(df_pf, use_container_width=True, hide_index=True)

st.divider()

# 2. Scanner Overzicht
st.subheader("🔍 Markt Kansen (Top 50 Dividendaandelen)")
if scanner_res:
    df_sc = pd.DataFrame(scanner_res).sort_values("Div%", ascending=False)
    st.dataframe(df_sc, use_container_width=True, hide_index=True)

# Auto-refresh
time.sleep(900)
st.rerun()
