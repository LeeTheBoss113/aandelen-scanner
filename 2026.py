import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG & STYLING ---
st.set_page_config(layout="wide", page_title="Pure Dual-Strategy 2026")

API_URL = "https://script.google.com/macros/s/AKfycbzYOecTWF2OOz6hOcgqMwClU3IIFSlY32oVPWmmrJdcNgjx7PhV_f0eXOqsbyEabAjc/exec"

def style_action(val):
    if '✅' in val or '💎' in val: color = '#1e8449'
    elif 'BUY' in val: color = '#2ecc71'
    elif 'SELL' in val: color = '#e74c3c'
    elif '⚠️' in val or '❌' in val: color = '#9b59b6'
    else: color = '#3498db'
    return f'background-color: {color}; color: white; font-weight: bold'

# --- DATA FUNCTIES ---
def get_data():
    try:
        r = requests.get(f"{API_URL}?t={int(time.time())}", timeout=10).json()
        
        def clean(raw, cols):
            if not raw or len(raw) <= 1: return pd.DataFrame(columns=cols)
            df = pd.DataFrame(raw[1:], columns=raw[0])
            for col in ['Inleg', 'Koers', 'Winst']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            return df.dropna(subset=['Ticker'])

        df_a = clean(r.get('active', []), ["Ticker", "Inleg", "Koers", "Type"])
        df_l = clean(r.get('log', []), ["Datum", "Ticker", "Inleg", "Winst", "Type"])
        return df_a, df_l
    except:
        return pd.DataFrame(columns=["Ticker", "Inleg", "Koers", "Type"]), pd.DataFrame()

@st.cache_data(ttl=300)
def fetch_market(tickers, is_div=False):
    results = {}
    for t in list(set(tickers)):
        try:
            tk = yf.Ticker(t)
            h = tk.history(period="1y")
            if h.empty: continue
            price = h['Close'].iloc[-1]
            rsi = ta.rsi(h['Close'], 14).iloc[-1]
            trend12m = ((price - h['Close'].iloc[0]) / h['Close'].iloc[0]) * 100
            div = tk.info.get('dividendYield', 0) * 100 if is_div else 0
            results[t] = {"price": price, "rsi": rsi, "trend": trend12m, "div": div}
        except: continue
    return results

# --- DATA LADEN ---
df_a, df_l = get_data()

# --- UI ---
st.title("⚡ Strategy Dashboard Pro 2026")

# Metrics Sectie
c1, c2, c3 = st.columns(3)
winst_growth = df_l[df_l['Type'] == 'Growth']['Winst'].sum()
winst_div = df_l[df_l['Type'] == 'Dividend']['Winst'].sum()
c1.metric("🔥 Growth Resultaat", f"€{winst_growth:.2f}")
c2.metric("🛡️ Dividend Resultaat", f"€{winst_div:.2f}")
c3.metric("💰 Totaal", f"€{(winst_growth + winst_div):.2f}")

st.divider()

t1, t2, t3 = st.tabs(["🚀 Growth Strategy", "💎 Dividend Strategy", "📜 Totaal Logboek"])

def render_strategy(p_type, watchlist):
    df_p = df_a[df_a['Type'] == p_type]
    all_tickers = list(set(watchlist + df_p['Ticker'].tolist()))
    m_data = fetch_market(all_tickers, is_div=(p_type == "Dividend"))
    
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.subheader(f"Nieuwe {p_type} Trade")
        with st.form(f"add_{p_type}"):
            t_in = st.text_input("Ticker").upper().strip()
            i_in = st.number_input("Inleg (€)", 100.0)
            k_in = st.number_input("Koers", 0.0)
            if st.form_submit_button("Openen"):
                if t_in and k_in > 0:
                    requests.post(API_URL, data=json.dumps({"ticker":t_in, "inleg":i_in, "koers":k_in, "type":p_type}))
                    st.rerun()
    
    with col_b:
        st.subheader("Actieve Posities")
        pf = []
        for _, r in df_p.iterrows():
            if r['Ticker'] in m_data:
                cur = m_data[r['Ticker']]
                netto = ((r['Inleg']/r['Koers'])*cur['price']) * (1.0 if "." in r['Ticker'] else 0.997) - r['Inleg']
                pf.append({"Ticker": r['Ticker'], "Inleg": r['Inleg'], "Nu": round(cur['price'],2), "Winst": round(netto,2), "RSI": round(cur['rsi'],1)})
        
        if pf:
            df_pf = pd.DataFrame(pf)
            st.dataframe(df_pf, use_container_width=True, hide_index=True)
            sel = st.selectbox("Sluiten:", [""] + df_pf['Ticker'].tolist(), key=f"s_{p_type}")
            if st.button("Verkoop & Log", key=f"b_{p_type}"):
                row = df_pf[df_pf['Ticker'] == sel].iloc[0]
                requests.post(API_URL, data=json.dumps({"method":"delete", "ticker":sel, "inleg":row['Inleg'], "winst":row['Winst'], "type":p_type}))
                st.rerun()
        else: st.info("Geen posities.")

    st.divider()
    st.subheader(f"🔍 {p_type} Scanner")
    scan_rows = []
    for t in watchlist:
        if t in m_data:
            v = m_data[t]
            status = "BUY" if v['rsi'] < 35 else "SELL" if v['rsi'] > 65 else "WAIT"
            if p_type == "Dividend":
                status = "💎 SAFE BUY" if (status == "BUY" and v['trend'] > 0) else "❌ ZWAK" if v['trend'] < 0 else status
            
            row = {"Ticker": t, "Prijs": round(v['price'],2), "RSI": round(v['rsi'],1), "12M Trend": f"{v['trend']:.1f}%", "Advies": status}
            if p_type == "Dividend": row["Div %"] = f"{v['div']:.1f}%"
            scan_rows.append(row)
    
    st.dataframe(pd.DataFrame(scan_rows).style.map(style_action, subset=['Advies']), use_container_width=True, hide_index=True)

with t1:
    render_strategy("Growth", ['NVDA','TSLA','AAPL','MSFT','AMD','PLTR'])
with t2:
    render_strategy("Dividend", ['KO','PEP','O','JNJ','PG','INGA.AS'])
with t3:
    st.subheader("Historisch Logboek")
    if not df_log.empty:
        st.dataframe(df_log.sort_values('Datum', ascending=False), use_container_width=True, hide_index=True)

    else: st.info("Nog geen afgesloten trades.")
