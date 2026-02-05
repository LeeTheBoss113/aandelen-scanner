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

@st.cache_data(ttl=3600)
def gd(s):
 try:
  tk = yf.Ticker(s)
  h = tk.history(period="2y")
  return {"h":h,"i":tk.info,"p":h['Close'].iloc[-1]}
 except: return None

pr, sr = [], []
for t in AL:
 d = gd(t)
 if not d: continue
 p, h, inf = d['p'], d['h'], d['i']
 c = h['Close']
 r = ta.rsi(c, 14).iloc[-1]
 r = round(r, 1)
 m = c.tail(200).mean()
 p6 = (p-c.iloc[-126])/c.iloc[-126]
 p6 = round(p6*100, 1)
 p1 = (p-c.iloc[-252])/c.iloc[-252]
 p1 = round(p1*100, 1)
 
 s = "OK"
 if p > m and r < 42: s = "BUY"
 if r > 75: s = "HIGH"
 if p < m: s = "WAIT"
 
 a = "HOLD"
 if p < m: a = "SELL"
 if r > 75: a = "TAKE"
 
 for pi in st.session_state.pf:
  if pi['T'] == t:
   w = (pi['I']/pi['P'])*p
   w_abs = round(w-pi['I'], 2)
   w_pc = (w-pi['I'])/pi['I']
   w_pc = round(w_pc*100, 1)
   res = {"T":t,"P":p,"W$":w_abs,"W%":w_pc,"6M":p6,"1Y":p1,"S":s,"A":a}
   pr.append(res)
 if t in ML:
  dy = inf.get('dividendYield', 0)
  if dy is None: dy = 0
  sr.append({"T":t,"P":p,"D":round(dy*100,2),"R":r,"S":s})

st.title("Stability Investor")
t1, t2 = st.tabs(["Portfolio", "Scanner"])

with t1:
 if pr:
  dfp = pd.DataFrame(pr)
  tot = dfp['W$'].sum()
  st.metric("Total Profit", round(tot, 2))
  st.dataframe(dfp, hide_index=True)

with t2:
 if sr:
  dfs = pd.DataFrame(sr)
  st.subheader("Top 3 Low RSI")
  top = dfs.sort_values(by='R')
  top3 = top.head(3)
  cl = st.columns(3)
  for i, x in enumerate(top3.to_dict('records')):
   cl[i].metric(x['T'], x['P'], f"RSI: {x['R']}")
  st.divider()
  st.dataframe(top, hide_index=True)
