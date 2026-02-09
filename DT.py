import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json

st.set_page_config(layout="wide", page_title="Stability Investor Pro")

# PLAK HIER DE URL VAN JE GOOGLE APPS SCRIPT:
API_URL = "https://script.google.com/macros/s/AKfycbxlP2U3_PsLajE1cjn3ZC4G4d7S9hNcSya1bwR_Jk3WFBoRdPpmKFJrtv_Rhb5As54N/exec"

def load_data():
    try:
        r = requests.get(API_URL)
        data = r.json()
        return pd.DataFrame(data[1:], columns=data[0])
    except:
        return pd.DataFrame(columns=["T", "I", "P"])

df_pf = load_data()

with st.sidebar:
    st.header("Beheer")
    with st.form("add_form", clear_on_submit=True):
        t = st.text_input("Ticker").upper().strip()
        i = st.number_input("Inleg (€)", value=500.0)
        p = st.number_input("Koers")
        if st.form_submit_button("Toevoegen"):
            if t and p > 0:
                requests.post(API_URL, data=json.dumps({"ticker":t, "inleg":i, "koers":p}))
                st.success("Verzonden naar Google Sheets!")
                st.rerun()

    for index, row in df_pf.iterrows():
        if st.button(f"🗑️ {row['T']}", key=f"del{index}"):
            requests.post(API_URL, data=json.dumps({"method":"delete", "ticker":row['T']}))
            st.rerun()

# --- ANALYSE ---
ML = ['ASML.AS','SHELL.AS','KO','PEP','MSFT','AAPL','JPM']
AL = list(set(ML + df_pf['T'].tolist()))

@st.cache_data(ttl=600)
def gd(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="2y")
        if h.empty: return None
        return {"h":h, "i":tk.info, "p":float(h['Close'].iloc[-1])}
    except: return None

db, pr, sr = {}, [], []
for t in AL:
    d = gd(t)
    if d:
        c = d['h']['Close']
        rsi = ta.rsi(c, 14).iloc[-1]
        ma200 = c.tail(200).mean()
        status = "OK"
        if d['p'] > ma200 and rsi < 40: status = "BUY"
        elif rsi > 70: status = "HIGH"
        elif d['p'] < ma200: status = "WAIT"
        db[t] = {"p":d['p'], "r":rsi, "s":status, "inf":d['i']}

for _, row in df_pf.iterrows():
    t = row['T']
    if t in db:
        now_p = db[t]['p']
        w_a = ((float(row['I']) / float(row['P'])) * now_p) - float(row['I'])
        pr.append({"T":t, "W$":round(w_a,2), "S":db[t]['s']})

for t in ML:
    if t in db:
        sr.append({"T":t, "P":round(db[t]['p'],2), "R":round(db[t]['r'],1), "S":db[t]['s']})

st.title("🏦 Stability Investor Pro")
col1, col2 = st.columns(2)

with col1:
    st.header("Portfolio")
    if pr: st.dataframe(pd.DataFrame(pr), hide_index=True)
with col2:
    st.header("Scanner")
    if sr: st.dataframe(pd.DataFrame(sr), hide_index=True)

