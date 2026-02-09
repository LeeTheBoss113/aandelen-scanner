import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import os
from datetime import date

st.set_page_config(layout="wide", page_title="Stability Investor Pro")
F = "stability_portfolio.csv"

def ld():
 if not os.path.exists(F): return []
 try: 
  df = pd.read_csv(F)
  return df.to_dict('records')
 except: return []

def sv(d):
 pd.DataFrame(d).to_csv(F, index=False)

if 'pf' not in st.session_state:
 st.session_state.pf = ld()

with st.sidebar:
 st.header("Beheer")
 with st.form("a", clear_on_submit=True):
  t = st.text_input("Ticker (bv. ASML.AS)").upper().strip()
  i = st.number_input("Inleg (€)", min_value=0.0)
  p = st.number_input("Aankoopkoers", min_value=0.0)
  d_in = st.date_input("Aankoopdatum", value=date.today())
  if st.form_submit_button("Toevoegen"):
   if t:
    st.session_state.pf.append({"T":t,"I":i,"P":p,"D":str(d_in)})
    sv(st.session_state.pf)
    st.rerun()
 
 for n, m in enumerate(st.session_state.pf):
  if st.sidebar.button(f"Verwijder {m['T']}", key=f"d{n}"):
   st.session_state.pf.pop(n)
   sv(st.session_state.pf)
   st.rerun()

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
for t in AL:
 d = gd(t)
 if d:
  c = d['h']['Close']
  r = ta.rsi(c, 14).iloc[-1]
  m = c.tail(200).mean()
  s = "OK"
  if d['p'] > m and r < 40: s = "BUY"
  elif r > 70: s = "HIGH"
  elif d['p'] < m: s = "WAIT"
  db[t] = {"p":d['p'],"r":r,"s":s,"inf":d['i']}

for pi in st.session_state.pf:
 tk = str(pi['T']).strip().upper()
 if tk in db:
  cur = db[tk]
  inv, buy
