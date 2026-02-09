import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import os

st.set_page_config(layout="wide", page_title="Stability Investor Pro")
F = "stability_portfolio.csv"

# --- GOOGLE SHEETS CONNECTIE ---
# PLAK HIER JOUW VOLLEDIGE GOOGLE SHEETS URL:
URL = "JOUW_GOOGLE_SHEET_URL_HIER"

conn = st.connection("gsheets", type=GSheetsConnection)

# --- DATA OPSLAG LOGICA ---
def ld():
    # Check eerst of het bestand bestaat
    if os.path.exists(F):
        try:
            return pd.read_csv(F).to_dict('records')
        except:
            return []
    return []

def sv(d):
    df = pd.DataFrame(d)
    df.to_csv(F, index=False)
    # Ook opslaan in session_state als backup
    st.session_state.pf = d

# Initialiseer portfolio in de sessie
if 'pf' not in st.session_state:
    st.session_state.pf = ld()

with st.sidebar:
    st.header("Beheer")
    with st.form("a", clear_on_submit=True):
        t = st.text_input("Ticker (bv. ASML.AS)").upper().strip()
        i = st.number_input("Inleg (€/$)")
        p = st.number_input("Aankoopkoers")
        if st.form_submit_button("Toevoegen"):
            if t:
                # Toevoegen aan lokale lijst
                new_data = st.session_state.pf + [{"T":t,"I":i,"P":p}]
                sv(new_data)
                st.rerun()
    
    # Download backup knop (veiligheid voor Streamlit Cloud)
    if st.session_state.pf:
        df_download = pd.DataFrame(st.session_state.pf)
        csv = df_download.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Portfolio Backup",
            data=csv,
            file_name='my_portfolio.csv',
            mime='text/csv',
        )

    for n, m in enumerate(st.session_state.pf):
        if st.sidebar.button(f"Verwijder {m['T']}", key=f"d{n}"):
            st.session_state.pf.pop(n)
            sv(st.session_state.pf)
            st.rerun()

# --- DATA OPHALEN ---
ML = ['ASML.AS','SHELL.AS','UNA.AS','ABN.AS','INGA.AS','ADYEN.AS','KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','T','VZ','WMT','LOW','TGT','MSFT','AAPL','HD','COST','LLY','UNH','SBUX','CAT','V','MA','AVGO','JPM']
AL = list(set(ML + [str(x['T']).strip().upper() for x in st.session_state.pf]))

@st.cache_data(ttl=900)
def gd(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="2y")
        if h.empty: return None
        return {"h":h,"i":tk.info,"p":float(h['Close'].iloc[-1])}
    except: return None

db, pr, sr = {}, [], []
with st.spinner('Scannen van de markt...'):
    for t in AL:
        d = gd(t)
        if d:
            c = d['h']['Close']
            r = ta.rsi(c, 14).iloc[-1]
            m = c.tail(200).mean()
            p6 = ((d['p']-c.iloc[-126])/c.iloc[-126])*100 if len(c)>126 else 0
            p1 = ((d['p']-c.iloc[-252])/c.iloc[-252])*100 if len(c)>252 else 0
            s = "OK"
            if d['p'] > m and r < 40: s = "BUY"
            elif r > 70: s = "HIGH"
            elif d['p'] < m: s = "WAIT"
            db[t] = {"p":d['p'],"r":r,"s":s,"inf":d['i'],"6m":p6,"1y":p1}

# --- PORTFOLIO LOGICA ---
for pi in st.session_state.pf:
    tk = str(pi['T']).strip().upper()
    if tk in db:
        cur = db[tk]
        inv, buy, now = float(pi['I']), float(pi['P']), float(cur['p'])
        w_a = ((inv / buy) * now) - inv
        w_p = (w_a / inv) * 100
        pr.append({"T":tk,"W$":round(w_a,2),"W%":round(w_p,1),"6M":round(cur['6m'],1),"S":cur['s']})

for t in ML:
    if t in db:
        d = db[t]
        dy = d['inf'].get('dividendYield',0) or 0
        sr.append({"T":t,"P":round(d['p'],2),"D":round(dy*100,2),"R":round(d['r'],1),"S":d['s']})

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
        tot = round(dfp['W$'].sum(), 2)
        st.metric("Totaal Resultaat", f"€ {tot:.2f}")
        st.dataframe(dfp.sort_values(by='W%').style.map(clr), hide_index=True, use_container_width=True)
    else:
        st.info("Geen aandelen in portfolio. Voeg ze toe via de sidebar.")

with R:
    st.header("🔍 Beste Koopkansen")
    if sr:
        dfs = pd.DataFrame(sr)
        st.dataframe(dfs.sort_values(by='R').style.map(clr), hide_index=True, use_container_width=True)


