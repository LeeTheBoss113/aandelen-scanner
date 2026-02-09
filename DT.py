import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
from streamlit_gsheets import GSheetsConnection

st.set_page_config(layout="wide", page_title="Stability Investor Pro")

# --- GOOGLE SHEETS CONNECTIE ---
# PLAK HIER JOUW VOLLEDIGE GOOGLE SHEETS URL:
URL = "JOUW_GOOGLE_SHEET_URL_HIER"

conn = st.connection("gsheets", type=GSheetsConnection)

def load_data():
    try:
        return conn.read(spreadsheet=URL, ttl="0")
    except:
        return pd.DataFrame(columns=["T", "I", "P"])

df_pf = load_data()

with st.sidebar:
    st.header("Beheer")
    with st.form("add_form", clear_on_submit=True):
        t = st.text_input("Ticker (bv. ASML.AS)").upper().strip()
        i = st.number_input("Inleg (€/$)")
        p = st.number_input("Aankoopkoers")
        if st.form_submit_button("Toevoegen"):
            if t and p > 0:
                new_row = pd.DataFrame([{"T": t, "I": i, "P": p}])
                updated_df = pd.concat([df_pf, new_row], ignore_index=True)
                conn.update(spreadsheet=URL, data=updated_df)
                st.success(f"{t} toegevoegd!")
                st.rerun()

    st.divider()
    for index, row in df_pf.iterrows():
        if st.button(f"🗑️ {row['T']}", key=f"del{index}"):
            updated_df = df_pf.drop(index)
            conn.update(spreadsheet=URL, data=updated_df)
            st.rerun()

# --- ANALYSE LOGICA ---
ML = ['ASML.AS','SHELL.AS','UNA.AS','INGA.AS','KO','PEP','JNJ','O','PG','MSFT','AAPL','LLY','V','MA','AVGO']
# Combineer Masterlist met jouw Portfolio Tickers
AL = list(set(ML + df_pf['T'].tolist()))

@st.cache_data(ttl=900)
def gd(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="2y")
        if h.empty: return None
        return {"h":h, "i":tk.info, "p":float(h['Close'].iloc[-1])}
    except: return None

db, pr, sr = {}, [], []
with st.spinner('Live koersen ophalen...'):
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

# Portfolio resultaten berekenen
for _, row in df_pf.iterrows():
    t = row['T']
    if t in db:
        d = db[t]
        inv, buy, now = float(row['I']), float(row['P']), d['p']
        w_a = ((inv / buy) * now) - inv
        w_p = (w_a / inv) * 100
        pr.append({"T":t, "W$":round(w_a,2), "W%":round(w_p,1), "6M":round(d['6m'],1), "S":d['s']})

# Scanner resultaten
for t in ML:
    if t in db:
        d = db[t]
        dy = d['inf'].get('dividendYield',0) or 0
        sr.append({"T":t, "P":round(d['p'],2), "D":round(dy*100,2), "R":round(d['r'],1), "S":d['s']})

# --- UI WEERGAVE ---
st.title("🏦 Stability Investor Pro")
st.caption("Data live gesynchroniseerd met Google Sheets")

def clr(v):
    if v in ["BUY","OK"]: return "color:green; font-weight:bold"
    if v == "WAIT": return "color:red"
    if v == "HIGH": return "color:orange"
    return ""

L, R = st.columns([1, 1.1])

with L:
    st.header("📊 Portfolio")
    if pr:
        dfp = pd.DataFrame(pr)
        st.metric("Totaal Resultaat", f"€ {dfp['W$'].sum():.2f}")
        st.dataframe(dfp.sort_values(by='W%').style.map(clr), hide_index=True, use_container_width=True)
    else:
        st.info("Voeg aandelen toe in de sidebar om te beginnen.")

with R:
    st.header("🔍 Beste Koopkansen")
    if sr:
        dfs = pd.DataFrame(sr)
        st.dataframe(dfs.sort_values(by='R').style.map(clr), hide_index=True, use_container_width=True)
