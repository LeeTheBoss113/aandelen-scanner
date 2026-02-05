import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import os

st.set_page_config(layout="wide", page_title="Stability Investor")
F = "stability_portfolio.csv"

def ld():
 if not os.path.exists(F): return []
 try: return pd.read_csv(F).to_dict('records')
 except: return []

def sv(d): pd.DataFrame(d).to_csv(F, index=False)
if 'pf' not in st.session_state: st.session_state.pf = ld()

with st.sidebar:
 st.header("⚙️ Beheer")
 with st.form("a", clear_on_submit=True):
  t = st.text_input("Ticker").upper()
  i = st.number_input("Inleg ($)", min_value=0.0)
  p = st.number_input("Aankoop ($)", min_value=0.01)
  if st.form_submit_button("Toevoegen"):
   if t:
    st.session_state.pf.append({"T":t,"I":i,"P":p})
    sv(st.session_state.pf); st.rerun()
 if st.session_state.pf:
  st.divider()
  for n, m in enumerate(st.session_state.pf):
   if st.sidebar.button(f"🗑️ {m['T']}", key=f"d{n}"):
    st.session_state.pf.pop(n); sv(st.session_state.pf); st.rerun()

ML = ['KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','MMM','T','VZ','WMT','LOW','TGT','ABT','MCD','MSFT','AAPL','IBM','HD','COST','LLY','PFE','MRK','UNH','BMY','SBUX','CAT','DE','NEE','PM','MO','BLK','V','MA','AVGO','TXN','JPM','SCHW']
AL = list(set(ML + [x['T'] for x in st.session_state.pf]))

@st.cache_data(ttl=3600)
def gd(s):
 try:
  tk = yf.Ticker(s); h = tk.history(period="2y")
  if h.empty: return None
  return {"h":h,"i":tk.info,"p":h['Close'].iloc[-1]}
 except: return None

pr, sr = [], []
with st.spinner('Markt scannen...'):
 for t in AL:
  d = gd(t)
  if not d: continue
  p, h, inf = d['p'], d['h'], d['i']
  r = round(ta.rsi(h['Close'], 14).iloc[-1], 1) if len(h)>14 else 50.0
  m = h['Close'].tail(200).mean() if len(h)>=200 else p
  p_6m = round(((p - h['Close'].iloc[-126])/h['Close'].iloc[-126])*100,1) if len(h)>126 else 0.0
  p_1y = round(((p - h['Close'].iloc[-252])/h['Close'].iloc[-252])*100,1) if len(h)>252 else 0.0
  s = "WACHTEN"
  if p > m:
   s = "STABIEL"
   if r < 42: s = "KOOP"
   if r > 75: s = "DUUR"
  a = "H
