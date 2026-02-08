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
  i = st.number_input("Inleg", format="%.2f")
  p = st.number_input("Aankoopkoers", format="%.2f")
  if st.form_submit_button("OK"):
   if t:
    st.session_state.pf.append({"T":t,"I":float(i),"P":float(p)})
    sv(st.session_state.pf)
    st.rerun()
 for n, m in enumerate(st.session_state.pf):
  if st.sidebar.button(f"X {m['T']}", key=f"d{n}"):
   st.session_state.pf.pop(n)
   sv(st.session_state.pf)
   st.rerun()

ML = ['KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','MMM','T','VZ','WMT','LOW','TGT','ABT','MCD','MSFT','AAPL','IBM','HD','COST','LLY','PFE','MRK','UNH','BMY','SBUX','CAT','DE','NEE','PM','MO','BLK','V','MA','AVGO','TXN','JPM','SCHW']
AL = list(set(ML + [str(x['T']).strip().upper() for x in st.session_state.pf]))

@st.cache_data(ttl=900)
def gd(s):
 try:
  tk = yf.Ticker(s)
  h = tk.history(period="1y")
  if h.empty: return None
  return {"h":h,"i":tk.info,"p":float(h['Close'].iloc[-1])}
 except: return None

db, pr, sr = {}, [], []

with st.spinner('Loading...'):
 for t in AL:
  d = gd(t)
  if d:
   c = d['h']['Close']
   r = ta.rsi(c, 14).iloc[-1]
   m = c.tail(200).mean()
   s = "OK"
   if d['p'] > m and r < 42: s = "BUY"
   elif r > 75: s = "HIGH"
   elif d['p'] < m: s = "WAIT"
   db[t] = {"p":d['p'],"r":r,"s":s,"inf":d['i']}

for pi in st.session_state.pf:
 tk = str(pi['T']).strip().upper()
 if tk in db:
  cur = db[tk]
  # Directe berekening
  inleg = float(pi['I'])
  koop = float(pi['P'])
  nu = float(cur['p'])
  
  winst = (inleg / koop * nu) - inleg
  perc = (winst / inleg) * 100
  
  pr.append({
   "T": tk,
   "W$": round(winst, 2),
   "W%": round(perc, 2),
   "Prijs": round(nu, 2),
   "S": cur['s']
  })

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
  st.metric("Total Profit", f"$ {round(
