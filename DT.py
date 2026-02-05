import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time
import os

st.set_page_config(layout="wide")
PF = "stability_portfolio.csv"

def load():
    if os.path.exists(PF):
        try: return pd.read_csv(PF).to_dict('records')
        except: return []
    return []

def save(d):
    pd.DataFrame(d).to_csv(PF, index=False)

if 'pf_data' not in st.session_state:
    st.session_state.pf_data = load()

# --- SIDEBAR ---
with st.sidebar:
    st.header("Beheer")
    with st.form("add", clear_on_submit=True):
        t = st.text_input("Ticker").upper().strip()
        i = st.number_input("Inleg", min_value=0.0)
        p = st.number_input("Aankoop", min_value=0.01)
        if st.form_submit_button("Voeg toe"):
            if t:
                st.session_state.pf_data.append(
                    {"Ticker": t, "Inleg": i, "Prijs": p}
                )
                save(st.session_state.pf_data)
                st.rerun()

    for n, item in enumerate(st.session_state.pf_data):
        c1, c2 = st.columns([3, 1])
        c1.write(item['Ticker'])
        if c2.button("X", key=f"d{n}"):
            st.session_state.pf_data.pop(n)
            save(st.session_state.pf_data)
            st.rerun()

# --- ENGINE ---
ML = ['KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','MMM',
      'T','VZ','WMT','LOW','TGT','ABT','MCD','MSFT','AAPL',
      'IBM','HD','COST','LLY','PFE','MRK','UNH','BMY',
      'SBUX','CAT','DE','NEE','PM','MO','BLK','V','MA',
      'AVGO','TXN','JPM','SCHW']
AL = list(set(ML + [x['Ticker'] for x in st.session_state.pf_data]))

@st.cache_data(ttl=3600)
def gd(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="2y")
        return {"h": h, "i": tk.info, "p": h['Close'].iloc[-1]}
    except: return None

pr, sr = [], []
bar = st.progress(0)

for j, t in enumerate(AL):
    d = gd(t)
    if d:
        p, h, inf = d['p'], d['h'], d['i']
        rsi = ta.rsi(h['Close'], 14).iloc[-1]
        ma = h['Close'].tail(200).mean()
        
        stt = "WACHTEN"
        if p > ma:
            stt = "STABIEL"
            if rsi < 42: stt = "KOOP"
            if rsi > 75: stt = "DUUR"

        for pi in st.session_state.pf_data:
            if pi['Ticker'] == t:
                w = (pi['Inleg'] / pi['Prijs']) * p
                pr.append({"Ticker": t, "Prijs": p, 
                           "Winst": w - pi['Inleg'], 
                           "Status": stt})

        if t in ML:
            sr.append({"Ticker": t, "Prijs": p, 
                       "Div": (inf.get('dividendYield', 0) or 0)*100,
                       "Pay": (inf.get('payoutRatio', 0) or 0)*100,
                       "Status": stt})
    bar.progress((j + 1) / len(AL))

# --- VIEW ---
st.title("Stability Investor")
t1, t2 = st.tabs(["Portfolio", "Scanner"])

def style(df):
    def _c(v):
        if v == "KOOP": return "color: green"
        if v == "WACHTEN": return "color: red"
        return ""
    if 'Status' in df.columns:
        return df.style.map(_c, subset=['Status'])
    return df

with t1:
    if pr: 
        st.dataframe(style(pd.DataFrame(pr)), hide_index=True)
    else: 
        st.write("Leeg")

with t2:
    if sr:
        df = pd.DataFrame(sr)
        # Sorteer-logica veilig opgesplitst
        rk = {"KOOP": 1, "STABIEL": 2, "DUUR": 3, "WACHTEN": 4}
        df['R'] = df['Status'].map(rk)
        # Gebruik variabelen om de regel kort te houden
        C1 = 'R'
        C2 = 'Div'
        df = df.sort_values([C1, C2], ascending=[True, False])
        st.dataframe(style(df.drop(columns='R')), hide_index=True)

time.sleep(900)
st.rerun()
