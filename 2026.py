import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="Dual-Strategy Simulator 2026")

try:
    API_URL = st.secrets["google_api_url"]
except:
    st.error("⚠️ API_URL niet gevonden!")
    st.stop()

# --- HELPERS ---
def style_action(val):
    if '✅' in val or '💎' in val: color = '#1e8449'
    elif 'BUY' in val: color = '#2ecc71'
    elif 'SELL' in val: color = '#e74c3c'
    elif '⚠️' in val or '❌' in val: color = '#9b59b6'
    else: color = '#3498db'
    return f'background-color: {color}; color: white; font-weight: bold'

def style_trend(val):
    try:
        num = float(val.replace('%', ''))
        return f'color: {"#2ecc71" if num > 0 else "#e74c3c"}; font-weight: bold'
    except: return ''

def style_portfolio(ticker, p1, p2):
    if ticker in p1: return 'background-color: #ffcc80; color: black;'
    if ticker in p2: return 'background-color: #b3e5fc; color: black;'
    return ''

@st.cache_data(ttl=300)
def fetch_market(tickers, include_div=False):
    results = {}
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            h = tk.history(period="1y")
            if h.empty: continue
            price = h['Close'].iloc[-1]
            rsi = ta.rsi(h['Close'], 14).iloc[-1]
            trend6m = ((price - h['Close'].iloc[-126]) / h['Close'].iloc[-126]) * 100 if len(h) > 126 else 0
            trend12m = ((price - h['Close'].iloc[0]) / h['Close'].iloc[0]) * 100
            div = tk.info.get('dividendYield', 0) * 100 if include_div else 0
            status = "BUY" if rsi < 35 else "SELL" if rsi > 65 else "WAIT"
            results[t] = {"price": price, "rsi": rsi, "status": status, "trend6m": trend6m, "trend12m": trend12m, "div": div}
        except: continue
    return results

def get_data():
    r = requests.get(f"{API_URL}?t={int(time.time())}").json()
    def clean(data):
        df = pd.DataFrame(data[1:], columns=data[0]) if len(data) > 1 else pd.DataFrame(columns=data[0])
        for col in ['Inleg', 'Koers', 'Winst']:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
        return df.dropna(subset=['Ticker']) if 'Ticker' in df.columns else df
    return clean(r['active']), clean(r['log']), clean(r['active_div']), clean(r['log_div'])

# --- LOGICA ---
df_a, df_l, df_a_div, df_l_div = get_data()
all_active = df_a['Ticker'].tolist() + df_a_div['Ticker'].tolist()

st.title("🚀 Dual-Strategy: Growth vs. Dividend")

# Metrics per strategie
col1, col2 = st.columns(2)
with col1:
    st.subheader("🔥 Aggressive Growth")
    winst_l = df_l['Winst'].sum() if not df_l.empty else 0.0
    st.metric("Gerealiseerd", f"€{winst_l:.2f}")

with col2:
    st.subheader("🛡️ Safe Haven Dividend")
    winst_l_div = df_l_div['Winst'].sum() if not df_l_div.empty else 0.0
    st.metric("Gerealiseerd", f"€{winst_l_div:.2f}")

tab1, tab2, tab3 = st.tabs(["📈 Growth Strategy", "💎 Dividend Strategy", "⚙️ Instellingen"])

def render_strategy(df_active, is_div):
    m_watch = ['NVDA','TSLA','AAPL','MSFT','AMD','PLTR'] if not is_div else ['KO','PEP','O','JNJ','PG','INGA.AS','NN.AS']
    data = fetch_market(m_watch + df_active['Ticker'].tolist(), include_div=is_div)
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.write("➕ Nieuwe Positie")
        with st.form(f"add_{is_div}"):
            t = st.text_input("Ticker").upper()
            i = st.number_input("Inleg", 100)
            k = st.number_input("Koers", 0.0)
            if st.form_submit_button("Openen"):
                requests.post(API_URL, data=json.dumps({"ticker":t,"inleg":i,"koers":k,"is_div":is_div}))
                st.rerun()
    with c2:
        st.write("📊 Open Posities")
        pf = []
        for _, r in df_active.iterrows():
            if r['Ticker'] in data:
                d = data[r['Ticker']]
                netto = ((r['Inleg']/r['Koers'])*d['price']) * (1 if "." in r['Ticker'] else 0.997) - r['Inleg']
                pf.append({"Ticker":r['Ticker'], "Inleg":r['Inleg'], "Winst":round(netto,2), "RSI":round(d['rsi'],1)})
        if pf:
            st.dataframe(pd.DataFrame(pf), use_container_width=True, hide_index=True)
            sel = st.selectbox("Sluiten:", [""]+[p['Ticker'] for p in pf], key=f"sel_{is_div}")
            if st.button("Verkoop & Log", key=f"btn_{is_div}"):
                row = [p for p in pf if p['Ticker']==sel][0]
                requests.post(API_URL, data=json.dumps({"method":"delete","ticker":sel,"inleg":row['Inleg'],"winst":row['Winst'],"is_div":is_div}))
                st.rerun()

    st.divider()
    st.write("🔍 Scanner")
    scan = []
    for k, v in fetch_market(m_watch, include_div=is_div).items():
        status = v['status']
        if is_div:
            if v['trend12m'] < 0: status = "❌ ZWAK"
            elif status == "BUY": status = "💎 SAFE BUY"
        else:
            if status == "BUY" and v['trend6m'] < -5: status = "⚠️ VALLEND MES"
        
        row = {"Ticker":k, "Prijs":v['price'], "RSI":v['rsi'], "12M %":f"{v['trend12m']:.1f}%", "Advies":status}
        if is_div: row["Div %"] = f"{v['div']:.1f}%"
        scan.append(row)
    
    df_scan = pd.DataFrame(scan)
    st.dataframe(df_scan.style.map(style_action, subset=['Advies']).map(style_trend, subset=['12M %']), use_container_width=True, hide_index=True)

with tab1: render_strategy(df_a, False)
with tab2: render_strategy(df_a_div, True)
with tab3:
    if st.button("🚨 Reset ALLES (Growth)"): requests.post(API_URL, data=json.dumps({"method":"reset_active","is_div":False})); st.rerun()
    if st.button("🚨 Reset ALLES (Dividend)"): requests.post(API_URL, data=json.dumps({"method":"reset_active","is_div":True})); st.rerun()