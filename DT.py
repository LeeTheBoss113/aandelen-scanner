import streamlit as st
import pandas as pd
import yfinance as yf
import os
from datetime import date

st.set_page_config(layout="wide")
F = "stability_portfolio.csv"

# 1. Data laden
def ld():
    if not os.path.exists(F): return []
    try:
        df = pd.read_csv(F)
        return df.to_dict('records')
    except: return []

def sv(d):
    pd.DataFrame(d).to_csv(F, index=False)

if 'pf' not in st.session_state:
    st.session_state.pf = ld()

# 2. Sidebar Beheer
with st.sidebar:
    st.header("Beheer")
    with st.form("add_form", clear_on_submit=True):
        t = st.text_input("Ticker (bv. KO)").upper().strip()
        i = st.number_input("Inleg (€)", value=500.0)
        p = st.number_input("Aankoopkoers", value=1.0)
        if st.form_submit_button("OK"):
            if t:
                st.session_state.pf.append({"T":t,"I":i,"P":p,"D":str(date.today())})
                sv(st.session_state.pf)
                st.rerun()
    
    for n, m in enumerate(st.session_state.pf):
        if st.sidebar.button(f"X {m['T']}", key=f"del{n}"):
            st.session_state.pf.pop(n)
            sv(st.session_state.pf)
            st.rerun()

# 3. Ticker Lijst & Data ophalen
ML = ['ASML.AS','SHELL.AS','KO','PEP','MSFT','AAPL','JNJ','O']
AL = list(set(ML + [x['T'] for x in st.session_state.pf]))

db, pr, sr = {}, [], []

# Directe data fetch
for t in AL:
    try:
        tk = yf.Ticker(t)
        h = tk.history(period="1y")
        if not h.empty:
            cur_p = h['Close'].iloc[-1]
            # Handmatige RSI berekening (simpel)
            delta = h['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs.iloc[-1]))
            
            db[t] = {"p": cur_p, "r": rsi, "inf": tk.info}
    except:
        continue

# 4. Portfolio verwerken
for pi in st.session_state.pf:
    tk = pi['T']
    if tk in db:
        now_p = db[tk]['p']
        winst = (float(pi['I']) / float(pi['P']) * now_p) - float(pi['I'])
        pr.append({"Ticker": tk, "Winst": round(winst, 2), "Koers": round(now_p, 2)})

# 5. Scanner verwerken
for t in ML:
    if t in db:
        sr.append({"Ticker": t, "Prijs": round(db[t]['p'], 2), "RSI": round(db[t]['r'], 1)})

# 6. UI
st.title("🏦 Stability Investor")

col1, col2 = st.columns(2)

with col1:
    st.header("Portfolio")
    if pr:
        st.table(pd.DataFrame(pr))
    else:
        st.write("Geen portfolio data.")

with col2:
    st.header("Scanner")
    if sr:
        st.table(pd.DataFrame(sr))
    else:
        st.write("Scanner zoekt data...")
