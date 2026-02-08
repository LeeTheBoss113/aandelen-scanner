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

def sv(d):
 pd.DataFrame(d).to_csv(F, index=False)

if 'pf' not in st.session_state:
 st.session_state.pf = ld()

with st.sidebar:
 st.header("Beheer")
 with st.form("a", clear_on_submit=True):
  t = st.text_input("Ticker").upper()
  i = st.number_input("Inleg")
  p = st.number_input("Aankoop")
  if st.form_submit_button("OK"):
   if t:
    st.session_state.pf.append({"T":t,"I":i,"P":p})
    sv(st.session_state.pf)
    st.rerun()
 for n, m in enumerate(st.session_state.pf):
  if st.sidebar.button(f"X {m['T']}", key=f"d{n}"):
   st.session_state.pf.pop(n)
   sv(st.session_state.pf)
   st.rerun()

ML = ['KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','MMM','T','VZ','WMT','LOW','TGT','ABT','MCD','MSFT','AAPL','IBM','HD','COST','LLY','PFE','MRK','UNH','BMY','SBUX','CAT','DE','NEE','PM','MO','BLK','V','MA','AVGO','TXN','JPM','SCHW']
AL = list(set(ML + [x['T'] for x in st.session_state.pf]))

@st.cache_data(ttl=900)
def gd(s):
 try:
  tk = yf.Ticker(s)
  h = tk.history(period="1y")
  if h.empty: return None
  return {"h":h,"i":tk.info,"p":h['Close'].iloc[-1]}
 except: return None

pr, sr = [], []
with st.spinner('Data ophalen...'):
 for t in AL:
  d = gd(t)
  if not d: continue
  p, h, inf = d['p'], d['h'], d['i']
  c = h['Close']
  r = round(ta.rsi(c, 14).iloc[-1], 1) if len(c)>14 else 50
  m = c.tail(200).mean() if len(c)>200 else c.mean()
  
  s = "OK"
  if p > m and r < 42: s = "BUY"
  if r > 75: s = "HIGH"
  if p < m: s = "WAIT"
  
  # Portfolio vullen
  for pi in st.session_state.pf:
   if pi['T'] == t:
    w = (pi['I']/pi['P'])*p
    pr.append({"T":t,"W$":round(w-pi['I'],2),"W%":round(((w-pi['I'])/pi['I'])*100,1),"Stat":s})
  
  # Scanner vullen
  if t in ML:
   dy = inf.get('dividendYield', 0) or 0
   sr.append({"T":t,"P":round(p,2),"D":round(dy*100,2),"R":r,"S":s})

st.title("🏦 Stability Investor Pro")
L, R = st.columns([1, 1.2]) # Scanner iets breder

def clr(v):
 if v in ["BUY","OK"]: return "color:green"
 if v in ["WAIT"]: return "color:red"
 if v == "HIGH": return "color:orange"
 return ""

with L:
 st.header("📊 Portfolio")
 if pr:
  dfp = pd.DataFrame(pr)
  st.metric("Total Profit", round(dfp['W$'].sum(), 2))
  st.dataframe(dfp.style.map(clr), hide_index=True, use_container_width=True)
 else:
  st.info("Voeg tickers toe in de sidebar.")

with R:
 st.header("🔍 Scanner")
 if sr:
  dfs = pd.DataFrame(sr)
  top = dfs.sort_values(by='R').head(3)
  c = st.columns(3)
  for idx, x in enumerate(top.to_dict('records')):
   c[idx].metric(x['T'], f"${x['P']}", f"RSI: {x['R']}")
  st.divider()
  st.dataframe(dfs.sort_values(by='R').style.map(clr), hide_index=True, use_container_width=True)
