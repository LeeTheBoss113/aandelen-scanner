import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json

st.set_page_config(layout="wide", page_title="Stability Investor Pro")

# --- CONFIG ---
# PLAK HIER DE URL VAN JE GOOGLE APPS SCRIPT:
API_URL = "https://script.google.com/macros/s/AKfycbxlP2U3_PsLajE1cjn3ZC4G4d7S9hNcSya1bwR_Jk3WFBoRdPpmKFJrtv_Rhb5As54N/exec"

def load_data():
    try:
        r = requests.get(API_URL)
        data = r.json()
        # Maak dataframe en zorg dat kolommen altijd T, I, P zijn
        df = pd.DataFrame(data[1:], columns=["T", "I", "P"])
        return df
    except:
        return pd.DataFrame(columns=["T", "I", "P"])

df_pf = load_data()

# --- SIDEBAR (BEHEER) ---
with st.sidebar:
    st.header("Beheer")
    with st.form("add_form", clear_on_submit=True):
        t = st.text_input("Ticker (bv. ASML.AS)").upper().strip()
        i = st.number_input("Inleg (€)", value=500.0)
        p = st.number_input("Aankoopkoers", min_value=0.01)
        if st.form_submit_button("Toevoegen"):
            if t and p > 0:
                requests.post(API_URL, data=json.dumps({"ticker":t, "inleg":i, "koers":p}))
                st.success(f"{t} toegevoegd aan Google!")
                st.rerun()

    st.divider()
    st.subheader("Huidige Posities")
    for index, row in df_pf.iterrows():
        # Verwijderknop per ticker
        if st.button(f"🗑️ Verwijder {row['T']}", key=f"del{index}"):
            requests.post(API_URL, data=json.dumps({"method":"delete", "ticker":row['T']}))
            st.rerun()

# --- ANALYSE LOGICA ---
# Uitgebreide lijst met kwaliteits-tickers
ML = ['ASML.AS','SHELL.AS','UNA.AS','ABN.AS','INGA.AS','ADYEN.AS','KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','T','VZ','WMT','LOW','TGT','MSFT','AAPL','HD','COST','LLY','UNH','SBUX','CAT','V','MA','AVGO','JPM']
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
with st.spinner('Markt scannen...'):
    for t in AL:
        d = gd(t)
        if d:
            c = d['h']['Close']
            rsi = ta.rsi(c, 14).iloc[-1]
            ma200 = c.tail(200).mean()
            p6m = ((d['p']-c.iloc[-126])/c.iloc[-126])*100 if len(c)>126 else 0
            
            status = "OK"
            if d['p'] > ma200 and rsi < 40: status = "BUY"
            elif rsi > 70: status = "HIGH"
            elif d['p'] < ma200: status = "WAIT"
            
            db[t] = {"p":d['p'], "r":rsi, "s":status, "inf":d['i'], "6m":p6m}

# Portfolio verwerken
for _, row in df_pf.iterrows():
    t = row['T']
    if t in db:
        d = db[t]
        try:
            # Forceer getallen om rekenfouten te voorkomen
            inv = float(row['I'])
            buy = float(row['P'])
            now = d['p']
            w_a = ((inv / buy) * now) - inv
            w_p = (w_a / inv) * 100
            pr.append({"T":t, "W$":round(w_a,2), "W%":round(w_p,1), "6M":round(d['6m'],1), "S":d['s']})
        except: continue

# Scanner verwerken
for t in ML:
    if t in db:
        d = db[t]
        dy = d['inf'].get('dividendYield',0) or 0
        sr.append({"T":t, "P":round(d['p'],2), "D":round(dy*100,2), "R":round(d['r'],1), "S":d['s']})

# --- UI ---
st.title("🏦 Stability Investor Pro")

def clr(v):
    if v in ["BUY","OK"]: return "color:green; font-weight:bold"
    if v == "WAIT": return "color:red"
    if v == "HIGH": return "color:orange"
    return ""

L, R = st.columns([1, 1.1])

with L:
    st.header("📊 Portfolio Status")
    if pr:
        dfp = pd.DataFrame(pr)
        st.metric("Totaal Resultaat", f"€ {dfp['W$'].sum():.2f}")
        st.dataframe(dfp.sort_values(by='W%').style.map(clr), hide_index=True, use_container_width=True)
    else:
        st.info("Geen actieve posities gevonden in Google Sheets.")

with R:
    st.header("🔍 Beste Koopkansen")
    if sr:
        dfs = pd.DataFrame(sr)
        st.dataframe(dfs.sort_values(by='R').style.map(clr), hide_index=True, use_container_width=True)
