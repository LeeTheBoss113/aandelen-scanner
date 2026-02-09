import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json

st.set_page_config(layout="wide", page_title="Stability Investor Pro")

# --- CONFIG ---
# ZORG DAT DIT DE URL IS VAN JE NIEUWE IMPLEMENTATIE (Iedereen toegang)
API_URL = "https://script.google.com/macros/s/AKfycbxlP2U3_PsLajE1cjn3ZC4G4d7S9hNcSya1bwR_Jk3WFBoRdPpmKFJrtv_Rhb5As54N/exec"

def load_data():
    try:
        r = requests.get(API_URL, timeout=10)
        data = r.json()
        
        if not data or len(data) < 2: 
            return pd.DataFrame(columns=["T", "I", "P"])
        
        # We negeren de headers van Google en dwingen eigen koppen af
        df = pd.DataFrame(data[1:])
        df = df.iloc[:, :3] # Pak alleen de eerste 3 kolommen
        df.columns = ["T", "I", "P"]
        
        # Schoon de data op naar bruikbare getallen
        df['T'] = df['T'].astype(str).str.upper().str.strip()
        df['I'] = pd.to_numeric(df['I'], errors='coerce')
        df['P'] = pd.to_numeric(df['P'], errors='coerce')
        
        # Verwijder rijen die echt leeg zijn
        return df.dropna(subset=['T', 'I']).reset_index(drop=True)
    except:
        # Als alles faalt, geef een lege tabel terug zodat de app niet crasht
        return pd.DataFrame(columns=["T", "I", "P"])

# INITIALISEER DATA (Dit voorkomt de NameError)
df_pf = load_data()

# --- SIDEBAR ---
with st.sidebar:
    st.header("Beheer")
    with st.form("add_form", clear_on_submit=True):
        t = st.text_input("Ticker (bv. ASML.AS)").upper().strip()
        i = st.number_input("Inleg (€)", value=500.0)
        p = st.number_input("Aankoopkoers", min_value=0.01)
        if st.form_submit_button("Toevoegen"):
            if t and p > 0:
                requests.post(API_URL, data=json.dumps({"ticker":t, "inleg":i, "koers":p}))
                st.success(f"{t} toegevoegd!")
                st.rerun()

    st.divider()
    # Check veilig of er data is geladen
    if not df_pf.empty:
        st.subheader("Huidige Posities")
        for index, row in df_pf.iterrows():
            if st.button(f"🗑️ Verwijder {row['T']}", key=f"del{index}"):
                requests.post(API_URL, data=json.dumps({"method":"delete", "ticker":row['T']}))
                st.rerun()

# --- ANALYSE ---
ML = ['ASML.AS','SHELL.AS','UNA.AS','ABN.AS','INGA.AS','ADYEN.AS','KO','PEP','JNJ','O','PG','WMT','MSFT','AAPL','LLY','V','MA','COST','ABBV','JPM','MCD']
# Combineer masterlist met wat er in je sheet staat
all_tickers = list(set(ML + df_pf['T'].tolist()))

@st.cache_data(ttl=600)
def gd(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="2y")
        if h.empty: return None
        return {"h":h, "i":tk.info, "p":float(h['Close'].iloc[-1])}
    except: return None

db, pr, sr = {}, [], []
with st.spinner('Live koersen ophalen...'):
    for t in all_tickers:
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

# Portfolio resultaten
for _, row in df_pf.iterrows():
    t = str(row['T'])
    if t in db:
        now_p = db[t]['p']
        try:
            inv, buy = float(row['I']), float(row['P'])
            w_a = ((inv / buy) * now_p) - inv
            w_p = (w_a / inv) * 100
            pr.append({"T":t, "W$":round(w_a,2), "W%":round(w_p,1), "S":db[t]['s']})
        except: continue

# Scanner resultaten
for t in ML:
    if t in db:
        sr.append({"T":t, "P":round(db[t]['p'],2), "R":round(db[t]['r'],1), "S":db[t]['s']})

# --- UI ---
st.title("🏦 Stability Investor Pro")

def clr(v):
    if v in ["BUY","OK"]: return "color:green; font-weight:bold"
    if v == "WAIT": return "color:red"
    if v == "HIGH": return "color:orange"
    return ""

L, R = st.columns(2)
with L:
    st.header("📊 Portfolio Status")
    if pr:
        st.dataframe(pd.DataFrame(pr).style.map(clr), hide_index=True, use_container_width=True)
    else:
        st.info("Geen posities gevonden. Check de API link of voeg een aandeel toe.")
with R:
    st.header("🔍 Koopkansen (Scanner)")
    if sr:
        st.dataframe(pd.DataFrame(sr).sort_values(by='R').style.map(clr), hide_index=True, use_container_width=True)
