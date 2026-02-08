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

# De lijst met tickers die de scanner MOET controleren
ML = ['KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','MMM','T','VZ','WMT','LOW','TGT','ABT','MCD','MSFT','AAPL','IBM','HD','COST','LLY','PFE','MRK','UNH','BMY','SBUX','CAT','DE','NEE','PM','MO','BLK','V','MA','AVGO','TXN','JPM','SCHW']
AL = list(set(ML + [x['T'] for x in st.session_state.pf]))

@st.cache_data(ttl=900) # Verlaagd naar 15 min voor verse data
def gd(s):
 try:
  tk = yf.Ticker(s)
  h = tk.history(period="1y") # 1 jaar is genoeg voor MA200
  if h.empty: return None
  return {"h":h,"i":tk.info,"p":h['Close'].iloc[-1]}
 except: return None

pr, sr = [], []
# Feedback in de UI dat er gewerkt wordt
with st.spinner('Scanner controleert tickers...'):
 for t in AL:
  d = gd(t)
  if not d: continue
  p, h, inf = d['p'], d['h'], d['i']
  c = h['Close']
  
  # Basis berekeningen
  r = round(ta.rsi(c, 14).iloc[-1], 1) if len(c)>14 else 50
  m = c.tail(200).mean() if len(c)>200 else c.mean()
  
  s = "OK"
  if p > m and r < 42: s = "BUY"
  if r > 75: s = "HIGH"
  if p < m: s = "WAIT"
  
  a = "HOLD"
  if p < m: a = "SELL"
  if r > 75: a = "TAKE"
  
  # Check of het in Portfolio zit
  for pi in st.session_state.pf:
   if pi['T'] == t:
    w = (pi['I']/pi['P'])*p
    pr.append({"T":t,"W$":round(w-pi['I'],2),"W%":round(((w-pi['I'])/pi['I'])*100,1),"Stat":s,"Adv":a})
  
  # Check of het in de Scanner lijst moet
  if t in ML:
   dy = inf.get('dividendYield', 0) or 0
   sr.append({"T":t,"P":round(p,2),"D":round(dy*100,2),"R":r,"S":s})

# Layout
st.title("🏦 Stability Investor Pro")
L, R = st.columns([1, 1])

def clr(v):
 if v in ["BUY","OK"]: return "color:green"
 if v in ["SELL","WAIT"]: return "color:red"
 if v == "TAKE": return "color:orange"
 return ""

with L:
 st.header("📊 Portfolio")
 if pr:
  dfp = pd.DataFrame(pr)
  st.metric("Total Profit", round(dfp['W$'].sum(), 2))
  st.dataframe(dfp.style.map(clr), hide_index=True, use_container_width=True)
 else:
  st.info("Geen aandelen in portfolio.")

with R:
 st.header("🔍 Scanner")
 if sr:
  dfs = pd.DataFrame(sr)
  # Top 3 op basis van RSI
  st.subheader("🔥 Beste Kansen")
  top = dfs.sort_values(by='R').head(3)
  c = st.columns(3)
  for idx, x in enumerate(top.to_dict('records')):
   c[idx].metric(x['T'], f"${x['P']}", f"RSI: {x['R']}")
  
  st.divider()
  st.dataframe(dfs.sort_values(by='R').style.map(clr), hide_index=True, use_container_width=True)
 else:
  st.error("Scanner heeft geen data kunnen ophalen. Probeer 'Clear Cache' rechtsboven.")
