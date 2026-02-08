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
 df = pd.DataFrame(d)
 df.to_csv(F, index=False)

if 'pf' not in st.session_state:
 st.session_state.pf = ld()

with st.sidebar:
 st.header("Beheer")
 with st.form("a", clear_on_submit=True):
  t = st.text_input("Ticker").upper().strip()
  i = st.number_input("Inleg")
  p = st.number_input("Koers")
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

db, pr, sr = {}, [], []

with st.spinner('Loading...'):
 for t in AL:
  d = gd(t)
  if not d: continue
  p, h, inf = d['p'], d['h'], d['i']
  c = h['Close']
  r = ta.rsi(c, 14).iloc[-1]
  m = c.tail(200).mean()
  s = "OK"
  if p > m and r < 42: s = "BUY"
  elif r > 75: s = "HIGH"
  elif p < m: s = "WAIT"
  db[t] = {"p":p,"r":r,"s":s,"inf":inf}

for pi in st.session_state.pf:
 t = pi['T'].strip().upper()
 if t in db:
  d = db[t]
  a = float(pi['I'])/float(pi['P'])
  w = (a*d['p'])-float(pi['I'])
  pc = (w/float(pi['I']))*100
  pr.append({"T":t,"W$":round(w,2),"W%":round(pc,2),"K":round(d['p'],2),"S":d['s']})

for t in ML:
 if t in db:
  d = db[t]
  dy = d['inf'].get('dividendYield',0) or 0
  sr.append({"T":t,"P":round(d['p'],2),"D":round(dy*100,2),"R":round(d['r'],1),"S":d['s']})

st.title("Stability Investor")
L, R = st.columns([1, 1.2])

def clr(v):
 if v in ["BUY","OK"]: return "color:green"
 if v == "WAIT": return "color:red"
 if v == "HIGH": return "color:orange"
 return ""

with L:
 st.header("Portfolio")
 if pr:
  dfp = pd.DataFrame(pr)
  st.metric("Profit", round(dfp['W$'].sum(),2))
  st.dataframe(dfp.style.map(clr), hide_index=True)

with R:
 st.header("Scanner")
 if sr:
  dfs = pd.DataFrame(sr)
  top = dfs.sort_values(by='R').head(3)
  c = st.columns(3)
  for i, x in enumerate(top.to_dict('records')):
   c[i].metric(x['T'], x['P'], f"RSI: {x['R']}")
  st.divider()
  st.dataframe(dfs.sort_values(by='R').style.map(clr), hide_index=True)
