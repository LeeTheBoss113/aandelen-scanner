import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import os
from datetime import date

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
  t = st.text_input("Ticker").upper().strip()
  i = st.number_input("Inleg (€)")
  p = st.number_input("Koers")
  d_in = st.date_input("Datum", value=date.today())
  if st.form_submit_button("OK"):
   if t:
    st.session_state.pf.append({"T":t,"I":i,"P":p,"D":str(d_in)})
    sv(st.session_state.pf)
    st.rerun()
 for n, m in enumerate(st.session_state.pf):
  if st.sidebar.button(f"X {m['T']}", key=f"d{n}"):
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
  # Veilige berekening
  v_i = float(pi['I'])
  v_p = float(pi['P'])
  v_n = float(cur['p'])
  d_s = pd.to_datetime(pi.get('D', date.today()))
  dag = (pd.Timestamp.now() - d_s).days
  val = (v_i / v_p) * v_n
  w_a = val - v_i
  w_p = (w_a / v_i) * 100
  pr.append({"T":tk,"W$":round(w_a,2),"W%":round(w_p,1),"€":round(val,2),"Dagen":dag,"S":cur['s']})

for t in ML:
 if t in db:
  d = db[t]
  dy = d['inf'].get('dividendYield',0) or 0
  sr.append({"T":t,"P":round(d['p'],2),"D":round(dy*100,2),"R":round(d['r'],1),"S":d['s']})

st.title("🏦 Stability Investor Pro")
L, R = st.columns([1, 1.1])

def clr(v):
 if v in ["BUY","OK"]: return "color:green"
 if v == "WAIT": return "color:red"
 if v == "HIGH": return "color:orange"
 return ""

with L:
 st
