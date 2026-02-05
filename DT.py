import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import os

st.set_page_config(layout="wide")
F = "stability_portfolio.csv"

def ld():
 if not os.path.exists(F): return []
 try: return pd.read_csv(F).to_dict('records')
 except: return []

def sv(d): pd.DataFrame(d).to_csv(F, index=False)
if 'pf' not in st.session_state: st.session_state.pf = ld()

# --- SIDEBAR ---
with st.sidebar:
 st.header("Beheer")
 with st.form("a", clear_on_submit=True):
  t = st.text_input("Ticker").upper()
  i = st.number_input("Inleg", min_value=0.0)
  p = st.number_input("Aankoop", min_value=0.01)
  if st.form_submit_button("OK"):
   if t:
    st.session_state.pf.append({"T":t,"I":i,"P":p})
    sv(st.session_state.pf); st.rerun()
 
 if st.session_state.pf:
  for n, m in enumerate(st.session_state.pf):
   if st.sidebar.button(f"X {m['T']}", key=f"d{n}"):
    st.session_state.pf.pop(n); sv(st.session_state.pf); st.rerun()

# --- DATA ---
ML = ['KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','MMM','T','VZ','WMT','LOW','TGT','ABT','MCD','MSFT','AAPL','IBM','HD','COST','LLY','PFE','MRK','UNH','BMY','SBUX','CAT','DE','NEE','PM','MO','BLK','V','MA','AVGO','TXN','JPM','SCHW']
AL = list(set(ML + [x['T'] for x in st.session_state.pf]))

@st.cache_data(ttl=3600)
def gd(s):
 try:
  tk = yf.Ticker(s)
  h = tk.history(period="1y") # Iets kortere historie voor snelheid
  if h.empty: return None
  return {"h":h,"i":tk.info,"p":h['Close'].iloc[-1]}
 except: return None

pr, sr = [], []
# We gebruiken nu een simpele spinner ipv een progress bar
with st.spinner('Data ophalen...'):
 for t in AL:
  d = gd(t)
  if not d: continue
  p, h, inf = d['p'], d['h'], d['i']
  r = round(ta.rsi(h['Close'], 14).iloc[-1], 1) if len(h)>14 else 50
  m = h['Close'].tail(200).mean() if len(h)>=200 else p
  
  s = "WACHTEN"
  if p > m: s = "STABIEL"
  if p > m and r < 42: s = "KOOP"
  if p > m and r > 75: s = "DUUR"
  
  for pi in st.session_state.pf:
   if pi['T'] == t:
    w = (pi['I']/pi['P'])*p
    pr.append({"Ticker":t,"Inleg":pi['I'],"Koers":p,"Winst":w-pi['I'],"Status":s})
  
  if t in ML:
   sr.append({"Ticker":t,"Koers":p,"Div":round((inf.get('dividendYield',0) or 0)*100,2),"Pay":round((inf.get('payoutRatio',0) or 0)*100,1),"Status":s,"RSI":r})

# --- UI ---
st.title("🏦 Stability Investor Dashboard")
if not pr and not sr:
 st.warning("Geen data gevonden. Controleer je internetverbinding of tickers.")
else:
 t1, t2 = st.tabs(["📊 Portfolio", "🔍 Scanner"])
 
 def stl(df):
  if 'Status' not in df.columns: return df
  return df.style.map(lambda v: "color:green" if v=="KOOP" else ("color:red" if v=="WACHTEN" else ""), subset=['Status'])

 with t1:
  if pr:
   dfp = pd.DataFrame(pr)
   st.metric("Totaal Winst", f"$ {round(dfp['Winst'].sum(), 2)}")
   st.dataframe(stl(dfp), use_container_width=True, hide_index=True)
  else: st.info("Voeg aandelen toe via de sidebar.")

 with t2:
  if sr:
   dfs = pd.DataFrame(sr)
   rk = {"KOOP":1,"STABIEL":2,"DUUR":3,"WACHTEN":4}
   dfs['R'] = dfs['Status'].map(rk)
   dfs = dfs.sort_values(['R','Div'], ascending=[True, False]).drop(columns='R')
   st.dataframe(stl(dfs), use_container_width=True, hide_index=True)
