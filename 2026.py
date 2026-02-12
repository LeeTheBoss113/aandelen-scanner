
import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG & VEILIGHEID ---
st.set_page_config(layout="wide", page_title="Daytrade Simulator Pro 2026")

# Haal de URL veilig op uit Streamlit Secrets
try:
    API_URL = st.secrets["google_api_url"]
except:
    st.error("⚠️ API_URL niet gevonden in Secrets! Voeg 'google_api_url' toe in de Streamlit Cloud Settings.")
    st.stop()

# --- STYLING FUNCTIES ---
def style_action(val):
    if '✅ STERKE BUY' in val: color = '#1e8449' # Donkergroen
    elif 'BUY' in val: color = '#2ecc71'
    elif 'SELL' in val: color = '#e74c3c'
    elif '⚠️ VALLEND MES' in val: color = '#9b59b6' # Paars (gevaarlijk)
    elif 'WAIT' in val: color = '#f1c40f'
    else: color = '#3498db'
    return f'background-color: {color}; color: white; font-weight: bold'

def style_trend(val):
    try:
        num = float(val.replace('%', ''))
        color = '#2ecc71' if num > 0 else '#e74c3c'
        return f'color: {color}; font-weight: bold'
    except: return ''

# --- DATA FUNCTIES ---
def get_all_data():
    try:
        r = requests.get(f"{API_URL}?t={int(time.time())}", timeout=10)
        res = r.json()
        active_raw = res.get('active', [])
        log_raw = res.get('log', [])
        df_active = pd.DataFrame(active_raw[1:], columns=["Ticker", "Inleg", "Koers"]) if len(active_raw) > 1 else pd.DataFrame(columns=["Ticker", "Inleg", "Koers"])
        df_active['Inleg'] = pd.to_numeric(df_active['Inleg'], errors='coerce')
        df_active['Koers'] = pd.to_numeric(df_active['Koers'], errors='coerce')
        df_log = pd.DataFrame(log_raw[1:], columns=["Datum", "Ticker", "Inleg", "Winst"]) if len(log_raw) > 1 else pd.DataFrame(columns=["Datum", "Ticker", "Inleg", "Winst"])
        if not df_log.empty: df_log['Winst'] = pd.to_numeric(df_log['Winst'], errors='coerce')
        return df_active.dropna(subset=['Ticker']), df_log
    except:
        return pd.DataFrame(columns=["Ticker", "Inleg", "Koers"]), pd.DataFrame(columns=["Datum", "Ticker", "Inleg", "Winst"])

@st.cache_data(ttl=300)
def fetch_market(tickers):
    results = {}
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            h = tk.history(period="1y") 
            if h.empty: continue
            price = h['Close'].iloc[-1]
            rsi = ta.rsi(h['Close'], 14).iloc[-1]
            p6m = h['Close'].iloc[-126] if len(h) >= 126 else h['Close'].iloc[0]
            trend6m = ((price - p6m) / p6m) * 100
            p12m = h['Close'].iloc[0]
            trend12m = ((price - p12m) / p12m) * 100
            
            status = "WAIT"
            if rsi < 35: status = "BUY"
            elif rsi > 65: status = "SELL"
            
            results[t] = {"price": price, "rsi": rsi, "status": status, "trend6m": trend6m, "trend12m": trend12m}
        except: continue
    return results

# --- DATA LADEN ---
df_active, df_log = get_all_data()
gerealiseerde_winst = df_log['Winst'].sum() if not df_log.empty else 0.0

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Dashboard")
    sim_mode = st.toggle("🛠️ Simulator Modus", value=True)
    st.divider()
    st.subheader("🧹 Opschonen")
    if st.button("🗑️ Reset Actieve Portfolio"):
        requests.post(API_URL, data=json.dumps({"method": "reset_active"}))
        st.rerun()
    if st.button("📜 Wis Logboek"):
        requests.post(API_URL, data=json.dumps({"method": "reset_log"}))
        st.rerun()

# --- MAIN UI ---
st.title("⚡ Pro Daytrade Dashboard 2026")
if sim_mode: st.info("🔵 **SIMULATOR MODUS** - Kosten: 0.3% per transactie")

tickers_in_sheet = [t for t in df_active['Ticker'].unique().tolist() if t and t != 'NONE']
m_data = fetch_market(tickers_in_sheet)

openstaande_winst = 0.0
pf_list = []

for _, row in df_active.iterrows():
    t = row['Ticker']
    if t in m_data:
        cur = m_data[t]
        inv, buy = float(row['Inleg']), float(row['Koers'])
        be_price = buy * 1.006
        waarde_bruto = (inv / buy) * cur['price']
        netto_waarde = waarde_bruto * (0.997 if "." not in t else 1.0)
        winst = netto_waarde - inv
        openstaande_winst += winst
        pf_list.append({
            "Ticker": t, "Inleg": inv, "Aankoop": buy, "B-E": round(be_price, 2),
            "Nu": round(cur['price'], 2), "Winst": round(winst, 2), "RSI": round(cur['rsi'], 1)
        })

m1, m2, m3 = st.columns(3)
m1.metric("Gerealiseerd", f"€{gerealiseerde_winst:.2f}")
m2.metric("Openstaand", f"€{openstaande_winst:.2f}", delta=f"{openstaande_winst:.2f}")
m3.metric("Totaal", f"€{(gerealiseerde_winst + openstaande_winst):.2f}")

tab1, tab2, tab3 = st.tabs(["📊 Portfolio", "🔍 Smart Scanner", "📜 Historie"])

with tab1:
    c1, c2 = st.columns([1, 2.5])
    with c1:
        st.subheader("Nieuwe Trade")
        with st.form("add"):
            t_in = st.text_input("Ticker").upper().strip()
            i_in = st.number_input("Inleg (€)", value=100.0)
            k_in = st.number_input("Koers", value=0.0)
            if st.form_submit_button("Openen"):
                if t_in and k_in > 0:
                    requests.post(API_URL, data=json.dumps({"ticker": t_in, "inleg": i_in, "koers": k_in}))
                    st.rerun()
    with c2:
        st.subheader("Open Posities")
        if pf_list:
            st.dataframe(pd.DataFrame(pf_list), hide_index=True, use_container_width=True)
            to_del = st.selectbox("Sluiten:", [""] + [p['Ticker'] for p in pf_list])
            if st.button("Verkoop & Log"):
                if to_del:
                    row_d = [p for p in pf_list if p['Ticker'] == to_del][0]
                    requests.post(API_URL, data=json.dumps({"method": "delete", "ticker": to_del, "inleg": row_d['Inleg'], "winst": row_d['Winst']}))
                    st.rerun()
        else: st.info("Geen posities.")

with tab2:
    st.subheader("🔍 Smart Market Scanner")
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        min_trend = st.slider("Minimale 6M Trend (%)", -50, 50, -100)
    with col_f2:
        hide_bad = st.checkbox("Verberg 'VALLEND MES'", value=False)

    watchlist = ['NVDA','TSLA','AAPL','MSFT','AMZN','META','AMD','ASML.AS','ADYEN.AS','INGA.AS','SHELL.AS','PLTR','COIN','GOOGL','NFLX','MARA']
    m_watch = fetch_market(watchlist)
    if m_watch:
        scan_rows = []
        for k, v in m_watch.items():
            status = v['status']
            if status == "BUY":
                if v['trend6m'] < -5: status = "⚠️ VALLEND MES"
                elif v['trend6m'] > 5: status = "✅ STERKE BUY"
            
            if v['trend6m'] >= min_trend:
                if not (hide_bad and "VALLEND MES" in status):
                    scan_rows.append({
                        "Ticker": k, "Prijs": round(v['price'], 2), "RSI": round(v['rsi'], 1),
                        "6M Trend": f"{v['trend6m']:.1f}%", "12M Trend": f"{v['trend12m']:.1f}%", "Advies": status
                    })
        
        df_s = pd.DataFrame(scan_rows).sort_values('RSI')
        st.dataframe(df_s.style.map(style_action, subset=['Advies']).map(style_trend, subset=['6M Trend', '12M Trend']), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Logboek")
    if not df_log.empty:
        st.dataframe(df_log.sort_values('Datum', ascending=False), use_container_width=True, hide_index=True)
        log_opts = [f"{r['Ticker']} (€{r['Winst']:.2f})" for _, r in df_log.iterrows()]
        to_del_log = st.selectbox("Corrigeer historie:", [""] + log_opts)
        if st.button("Wis uit Log"):
            if to_del_log:
                s_t = to_del_log.split(" (")[0]
                s_w = to_del_log.split("€")[-1].replace(")", "")
                requests.post(API_URL, data=json.dumps({"method": "delete_log_entry", "ticker": s_t, "winst": float(s_w)}))
                st.rerun()
