import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="Dual-Strategy Simulator 2026")

API_URL = "https://script.google.com/macros/s/AKfycbz-4mkyZJISTvixd3JsNHIj9ja3N9824MEHIBsoIZgd_tkx2fM6Yc5ota6kW4WjRKO_/exec"

# --- STYLING HELPERS ---
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
    if ticker in p1: return 'background-color: #ffcc80; color: black; font-weight: bold'
    if ticker in p2: return 'background-color: #b3e5fc; color: black; font-weight: bold'
    return ''

# --- DATA FUNCTIE (FORCED COLUMN MAPPING) ---
def get_data():
    try:
        r = requests.get(f"{API_URL}?t={int(time.time())}", timeout=10).json()
        
        def clean(data_key, is_log=False):
            raw_data = r.get(data_key, [])
            # Als er geen data is, geef een lege dataframe met juiste kolommen
            if not raw_data or len(raw_data) <= 1:
                cols = ["Datum", "Ticker", "Inleg", "Winst"] if is_log else ["Ticker", "Inleg", "Koers"]
                return pd.DataFrame(columns=cols)
            
            # We forceren de kolomnamen op basis van POSITIE, niet op basis van wat in de Sheet staat
            df = pd.DataFrame(raw_data[1:]) # Sla de eerste rij (headers) over
            
            if is_log:
                df = df.iloc[:, :4] # Pak de eerste 4 kolommen
                df.columns = ["Datum", "Ticker", "Inleg", "Winst"]
            else:
                df = df.iloc[:, :3] # Pak de eerste 3 kolommen
                df.columns = ["Ticker", "Inleg", "Koers"]
            
            # Verwijder rijen waar de Ticker kolom leeg is
            df = df[df["Ticker"].astype(str).str.strip() != ""]
            
            # Zet getallen om en voorkom fouten
            for col in ['Inleg', 'Koers', 'Winst']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            return df
            
        return clean('active'), clean('log', True), clean('active_div'), clean('log_div', True)
    except Exception as e:
        st.error(f"⚠️ Verbindingsfout: {e}")
        return pd.DataFrame(columns=["Ticker","Inleg","Koers"]), pd.DataFrame(), \
               pd.DataFrame(columns=["Ticker","Inleg","Koers"]), pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_market(tickers, include_div=False):
    results = {}
    if not tickers: return results
    unique_tickers = list(set([str(t).strip().upper() for t in tickers if t and str(t) != "nan"]))
    for t in unique_tickers:
        try:
            tk = yf.Ticker(t)
            h = tk.history(period="1y")
            if h.empty: continue
            price = h['Close'].iloc[-1]
            rsi = ta.rsi(h['Close'], 14).iloc[-1]
            trend12m = ((price - h['Close'].iloc[0]) / h['Close'].iloc[0]) * 100
            trend6m = ((price - h['Close'].iloc[-126]) / h['Close'].iloc[-126]) * 100 if len(h) > 126 else 0
            div = tk.info.get('dividendYield', 0) * 100 if include_div else 0
            results[t] = {
                "price": price, "rsi": rsi, 
                "status": "BUY" if rsi < 35 else "SELL" if rsi > 65 else "WAIT",
                "trend6m": trend6m, "trend12m": trend12m, "div": div
            }
        except: continue
    return results

# --- DATA LADEN ---
df_a, df_l, df_a_div, df_l_div = get_data()
growth_list = df_a['Ticker'].astype(str).tolist() if not df_a.empty else []
div_list = df_a_div['Ticker'].astype(str).tolist() if not df_a_div.empty else []

# --- UI ---
st.title("⚡ Dual-Strategy Dashboard 2026")

m1, m2 = st.columns(2)
m1.metric("🔥 Growth Resultaat", f"€{df_l['Winst'].sum() if not df_l.empty else 0:.2f}")
m2.metric("🛡️ Dividend Resultaat", f"€{df_l_div['Winst'].sum() if not df_l_div.empty else 0:.2f}")

tab1, tab2, tab3 = st.tabs(["📈 Growth Strategy", "💎 Dividend Strategy", "⚙️ Beheer"])

def render_strategy(df_active, is_div, label):
    watchlist = ['NVDA','TSLA','AAPL','MSFT','AMD','PLTR'] if not is_div else ['KO','PEP','O','JNJ','PG','INGA.AS']
    all_needed = list(set(watchlist + (df_active['Ticker'].astype(str).tolist() if not df_active.empty else [])))
    data = fetch_market(all_needed, include_div=is_div)
    
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader(f"Nieuwe {label}")
        with st.form(f"f_{label}"):
            t_in = st.text_input("Ticker").upper().strip()
            i_in = st.number_input("Inleg (€)", 100.0)
            k_in = st.number_input("Koers", 0.0)
            if st.form_submit_button("Openen"):
                if t_in and k_in > 0:
                    requests.post(API_URL, data=json.dumps({"ticker":t_in,"inleg":i_in,"koers":k_in,"is_div":is_div}))
                    st.rerun()

    with c2:
        st.subheader("Posities")
        pf = []
        if not df_active.empty:
            for _, r in df_active.iterrows():
                t_code = str(r['Ticker']).upper()
                if t_code in data:
                    cur = data[t_code]
                    # Berekening met 0.3% kosten voor US stocks
                    factor = 1.0 if "." in t_code else 0.997
                    netto = ((r['Inleg']/r['Koers'])*cur['price']) * factor - r['Inleg']
                    pf.append({
                        "Ticker": t_code, "Inleg": r['Inleg'], "Koers": r['Koers'], 
                        "Nu": round(cur['price'], 2), "Winst": round(netto, 2), "RSI": round(cur['rsi'], 1)
                    })
        if pf:
            df_pf = pd.DataFrame(pf)
            st.dataframe(df_pf, use_container_width=True, hide_index=True)
            sel = st.selectbox("Sluiten:", [""] + df_pf['Ticker'].tolist(), key=f"s_{label}")
            if st.button("Sluiten & Log", key=f"b_{label}"):
                if sel:
                    row = df_pf[df_pf['Ticker'] == sel].iloc[0]
                    requests.post(API_URL, data=json.dumps({"method":"delete","ticker":sel,"inleg":row['Inleg'],"winst":row['Winst'],"is_div":is_div}))
                    st.rerun()
        else: st.info("Geen actieve posities.")

    st.divider()
    st.subheader(f"🔍 Scanner ({label})")
    s_data = fetch_market(watchlist, include_div=is_div)
    s_rows = []
    for k, v in s_data.items():
        st_val = v['status']
        if is_div:
            st_val = "❌ ZWAK" if v['trend12m'] < 0 else "💎 SAFE BUY" if st_val == "BUY" else st_val
        else:
            st_val = "⚠️ VALLEND MES" if (st_val == "BUY" and v['trend6m'] < -5) else st_val
        
        row = {"Ticker":k, "Prijs":round(v['price'], 2), "RSI":round(v['rsi'], 1), "12M %":f"{v['trend12m']:.1f}%", "Advies":st_val}
        if is_div: row["Div %"] = f"{v['div']:.1f}%"
        s_rows.append(row)
    
    if s_rows:
        df_scan = pd.DataFrame(s_rows).sort_values('RSI')
        st.dataframe(df_scan.style.map(style_action, subset=['Advies']).map(style_trend, subset=['12M %']).apply(lambda x: [style_portfolio(val, growth_list, div_list) if x.name == 'Ticker' else '' for val in x]), use_container_width=True, hide_index=True)

with tab1: render_strategy(df_a, False, "Growth")
with tab3:
    if st.button("Reset Growth Portfolio"): 
        requests.post(API_URL, data=json.dumps({"method":"reset_active","is_div":False}))
        st.rerun()
    if st.button("Reset Dividend Portfolio"): 
        requests.post(API_URL, data=json.dumps({"method":"reset_active","is_div":True}))
        st.rerun()
with tab2: render_strategy(df_a_div, True, "Dividend")