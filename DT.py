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
 for n, m in enumerate(st.session_state.pf):
  if st.sidebar.button(f"X {m['T']}", key=f"d{n}"):
   st.session_state.pf.pop(n); sv(st.session_state.pf); st.rerun()

ML = ['KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','MMM','T','VZ','WMT','LOW','TGT','ABT','MCD','MSFT','AAPL','IBM','HD','COST','LLY','PFE','MRK','UNH','BMY','SBUX','CAT','DE','NEE','PM','MO','BLK','V','MA','AVGO','TXN','JPM','SCHW']
AL = list(set(ML + [x['T'] for x in st.session_state.pf]))

@st.cache_data(ttl=3600)
def gd(s):
 try:
  tk = yf.Ticker(s); h = tk.history(period="2y")
  return {"h":h,"i":tk.info,"p":h['Close'].iloc[-1]}
 except: return None

pr, sr = [], []
for t in AL:
 d = gd(t)
 if not d: continue
 p, h, inf = d['p'], d['h'], d['i']
 r = round(ta.rsi(h['Close'], 14).iloc[-1], 1)
 m = h['Close'].tail(200).mean()
 p6 = round(((p-h['Close'].iloc[-126])/h['Close'].iloc[-126])*100,1)
 p1 = round(((p-h['Close'].iloc[-252])/h['Close'].iloc[-252])*100,1)
 s = "WAIT"
 if p > m:
  s = "OK"
  if r < 42: s = "BUY"
  if r > 75: s = "HIGH"
 a = "HOLD"
 if p < m: a = "SELL"
 elif r > 75: a = "TAKE"
 for pi in st.session_state.pf:
  if pi['T'] == t:
   w = (pi['I']/pi['P'])*p
   pr.append({"T":t,"P":p,"W$":round(w-pi['I'],2),"W%":round(((w-pi['I'])/pi['I'])*100,1),"6M":p6,"1Y":p1,"Stat":s,"Adv":a})
 if t in ML:
  sr.append({"T":t,"P":p,"D%":round((inf.get('dividendYield',0) or 0)*100,2),"Stat":s,"RSI":r})

st.title("Stability Investor")
t1, t2 = st.tabs(["Portfolio", "Scanner"])

def stl(df):
 c = {"BUY":"color:green","SELL":"color:red","TAKE":"color:orange"}
 try: return df.style.apply(lambda x: [c.get(v, "") for v in x], axis=0)
 except: return df

with t1:
 if pr:
  dfp = pd.DataFrame(pr)
  st.metric("Profit", round(dfp['W$'].sum
