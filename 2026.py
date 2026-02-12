import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="Dual-Strategy Simulator 2026")

# Jouw API URL (Vergeet niet opnieuw te implementeren in Google Script bij wijzigingen!)
API_URL = "https://script.google.com/macros/s/AKfycbz-4mkyZJISTvixd3JsNHIj9ja3N9824MEHIBsoIZgd_tkx2fM6Yc5ota6kW4WjRKO_/exec"

# --- STYLING HELPERS ---
def style_action(val):
    if '✅' in val or '💎' in val: color = '#1e8449'
    elif 'BUY' in val: color = '#2ecc71'
    elif 'SELL' in val: color = '#e74c3c'
    elif '⚠️' in val or '❌' in val: color = '#9b59b6'
    elif 'WAIT' in val: color = '#f1c40f'
    else: color = '#3498db'
    return f'background-color: {color}; color: white; font-weight: bold'

def style_trend(val):
    try:
        num = float(val.replace('%', ''))
        return f'color: {"#2ecc71" if num > 0 else "#e74c3c"}; font-weight: bold'
    except: return ''

def style_portfolio(ticker, p1, p2):
    if ticker in p1: return 'background-color: #ffcc80; color: black; font-weight: bold'
    if ticker in p2: return 'background-color: #b3e5fc; color: black; font-weight: bold'
    return ''

# --- ROBUUSTE DATA FUNCTIE ---
def get_data():
    active_cols = ["Ticker", "Inleg", "Koers"]
    log_cols = ["Datum", "Ticker", "Inleg", "Winst"]
    try:
        r = requests.get(f"{API_URL}?t={int(time.time())}", timeout=10).json()
        
        def clean(data_key, fallback_cols):
            raw_data = r.get(data_key, [])
            if not raw_data or len(raw_data) <= 1:
                return pd.DataFrame(columns=fallback_cols)
            
            # Headers opschonen (spaties verwijderen)
            headers = [str(h).strip() for h in raw_data[0]]
            df = pd.DataFrame(raw_data[1:], columns=headers)
            
            # Fallback: als 'Ticker' niet exact wordt gevonden, neem de eerste kolom
            if 'Ticker' not in df.columns and len(df.columns) > 0:
                df.rename(columns={df.columns[0]: 'Ticker'}, inplace=True)
                
            for col in ['Inleg', 'Koers', 'Winst']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            return df.dropna(subset=['Ticker'])
            
        return clean('active', active_cols), clean('log', log_cols), \
               clean('active_div', active_cols), clean('log_div', log_cols)
    except Exception as e:
        st.error(f"⚠️ Verbindingsfout: {e}")
        return pd.DataFrame(columns=active_cols), pd.DataFrame(columns=log_cols), \
               pd.DataFrame(columns=active_cols), pd.DataFrame(columns=log_cols)

@st.cache_data(ttl=300)
def fetch_market(tickers, include_div=False):
    results = {}
    if not tickers: return results
    unique_tickers = list(set([t for t in tickers if t]))
    for t in unique_tickers:
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

# --- DATA LADEN ---
df_a, df_l, df_a_div, df_l_div = get_data()
growth_active_list = df_a['Ticker'].tolist() if not df_a.empty else []
div_active_list = df_a_div['Ticker'].tolist() if not df_a_div.empty else []

# --- UI ---
st.title("🚀 Dual-Strategy Simulator 2026")

c_m1, c_m2 = st.columns(2)
with c_m1:
    w_g = df_l['Winst'].sum() if not df_l.empty else 0.0
    st.metric("🔥 Growth Resultaat", f"€{w_g:.2f}")
with c_m2:
    w_d = df_l_div['Winst'].sum() if not df_l_div.empty else 0.0
    st.metric("🛡️ Dividend Resultaat", f"€{w_d:.2f}")

tab1, tab2, tab3 = st.tabs(["📈 Growth Portfolio", "💎 Dividend Portfolio", "⚙️ Beheer"])

def render_strategy_view(df_active, is_div, strategy_name):
    watchlist = ['NVDA','TSLA','AAPL','MSFT','AMD','PLTR'] if not is_div else ['KO','PEP','O','JNJ','PG','INGA.AS']
    
    # Combineer watchlist en actieve posities voor data ophalen
    all_needed = list(set(watchlist + (df_active['Ticker'].tolist() if not df_active.empty else [])))
    market_data = fetch_market(all_needed, include_div=is_div)
    
    col_left, col_right = st.columns([1, 2])
    
    with col_left:
        st.subheader(f"Nieuwe {strategy_name}")
        with st.form(f"form_{strategy_name}"):
            t = st.text_input("Ticker").upper().strip()
            i = st.number_input("Inleg (€)", value=100.0)
            k = st.number_input("Koers", value=0.0)
            if st.form_submit_button("Open Positie"):
                if t and k > 0:
                    requests.post(API_URL, data=json.dumps({"ticker":t,"inleg":i,"koers":k,"is_div":is_div}))
                    st.rerun()

    with col_right:
        st.subheader("Openstaande Posities")
        pf = []
        if not df_active.empty:
            for _, r in df_active.iterrows():
                if r['Ticker'] in market_data:
                    d = market_data[r['Ticker']]
                    # Berekening winst (0.3% kosten voor US aandelen)
                    netto = ((r['Inleg']/r['Koers'])*d['price']) * (1.0 if "." in r['Ticker'] else 0.997) - r['Inleg']
                    pf.append({
                        "Ticker": r['Ticker'], "Inleg": r['Inleg'], "Aankoop": r['Koers'], 
                        "Nu": round(d['price'], 2), "Winst": round(netto, 2), "RSI": round(d['rsi'], 1)
                    })
        
        if pf:
            df_pf = pd.DataFrame(pf)
            st.dataframe(df_pf, use_container_width=True, hide_index=True)
            sel = st.selectbox("Sluit positie:", [""] + df_pf['Ticker'].tolist(), key=f"sel_{strategy_name}")
            if st.button("Verkoop & Log", key=f"btn_{strategy_name}"):
                if sel:
                    row = df_pf[df_pf['Ticker'] == sel].iloc[0]
                    requests.post(API_URL, data=json.dumps({"method":"delete","ticker":sel,"inleg":row['Inleg'],"winst":row['Winst'],"is_div":is_div}))
                    st.rerun()
        else:
            st.info(f"Geen actieve {strategy_name} trades.")

    st.divider()
    st.subheader(f"🔍 {strategy_name} Scanner")
    scan_results = []
    # Gebruik alleen watchlist voor scanner overzicht
    scanner_market = fetch_market(watchlist, include_div=is_div)
    for k, v in scanner_market.items():
        status = v['status']
        if is_div:
            if v['trend12m'] < 0: status = "❌ ZWAK"
            elif status == "BUY": status = "💎 SAFE BUY"
        else:
            if status == "BUY" and v['trend6m'] < -5: status = "⚠️ VALLEND MES"
        
        row = {"Ticker": k, "Prijs": round(v['price'], 2), "RSI": round(v['rsi'], 1), "12M %": f"{v['trend12m']:.1f}%", "Advies": status}
        if is_div: row["Div %"] = f"{v['div']:.1f}%"
        scan_results.append(row)
    
    if scan_results:
        df_scan = pd.DataFrame(scan_results).sort_values('RSI')
        st.dataframe(
            df_scan.style.map(style_action, subset=['Advies'])
                    .map(style_trend, subset=['12M %'])
                    .apply(lambda x: [style_portfolio(val, growth_active_list, div_active_list) if x.name == 'Ticker' else '' for val in x]),
            use_container_width=True, hide_index=True
        )

with tab1: render_strategy_view(df_a, False, "Growth")
with tab2: render_strategy_view(df_a_div, True, "Dividend")
with tab3:
    st.subheader("🧹 Beheer")
    if st.button("Reset Growth Portfolio"):
        requests.post(API_URL, data=json.dumps({"method":"reset_active","is_div":False}))
        st.rerun()
    if st.button("Reset Dividend Portfolio"):
        requests.post(API_URL, data=json.dumps({"method":"reset_active","is_div":True}))
        st.rerun()