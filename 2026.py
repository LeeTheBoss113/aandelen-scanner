import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="Daytrade Simulator Pro")
API_URL = "https://script.google.com/macros/s/AKfycbyhZxfS0WjCo-oT9n1j9fXrGd5Y7gE2ymU2g2SNSBv49P0be9W6ySsKFgc7QjCySnKm/exec"

# --- SIDEBAR: RESET ---
with st.sidebar:
    st.header("⚙️ Simulator Beheer")
    if st.button("🚨 RESET VOLLEDIGE HISTORIE", help="Wist actieve trades én het logboek"):
        requests.post(API_URL, data=json.dumps({"method": "reset_all"}))
        st.warning("Alles is gewist...")
        time.sleep(1.5)
        st.rerun()

# --- DATA FUNCTIES ---
def style_action(val):
    if val == 'BUY': color = '#2ecc71'
    elif val == 'SELL': color = '#e74c3c'
    elif val == 'WAIT': color = '#f1c40f'
    else: color = '#3498db'
    return f'background-color: {color}; color: white; font-weight: bold'

def get_all_data():
    try:
        r = requests.get(f"{API_URL}?t={int(time.time())}", timeout=10)
        res = r.json()
        
        # Actieve trades verwerken
        active_raw = res.get('active', [])
        if len(active_raw) < 2:
            df_active = pd.DataFrame(columns=["Ticker", "Inleg", "Koers"])
        else:
            df_active = pd.DataFrame(active_raw[1:], columns=["Ticker", "Inleg", "Koers"])
            df_active['Ticker'] = df_active['Ticker'].astype(str).str.strip().str.upper()
            df_active['Inleg'] = pd.to_numeric(df_active['Inleg'], errors='coerce')
            df_active['Koers'] = pd.to_numeric(df_active['Koers'], errors='coerce')

        # Logboek (Gerealiseerde winst) verwerken
        log_raw = res.get('log', [])
        if len(log_raw) < 2:
            df_log = pd.DataFrame(columns=["Datum", "Ticker", "Inleg", "Winst"])
        else:
            df_log = pd.DataFrame(log_raw[1:], columns=["Datum", "Ticker", "Inleg", "Winst"])
            df_log['Winst'] = pd.to_numeric(df_log['Winst'], errors='coerce')
            
        return df_active.dropna(subset=['Ticker']), df_log
    except:
        return pd.DataFrame(columns=["Ticker", "Inleg", "Koers"]), pd.DataFrame(columns=["Datum", "Ticker", "Inleg", "Winst"])

@st.cache_data(ttl=300)
def fetch_market(tickers):
    results = {}
    if not tickers: return results
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            h = tk.history(period="1y")
            if h.empty: continue
            price = h['Close'].iloc[-1]
            rsi = ta.rsi(h['Close'], 14).iloc[-1]
            status = "WAIT"
            if rsi < 35: status = "BUY"
            elif rsi > 65: status = "SELL"
            results[t] = {"price": price, "rsi": rsi, "status": status}
        except: continue
    return results

# --- DATA OPHALEN ---
df_active, df_log = get_all_data()
gerealiseerde_winst = df_log['Winst'].sum() if not df_log.empty else 0.0

# --- UI ---
st.title("⚡ Daytrade Simulator & Tracker")

# TOTAAL OVERZICHT BOVENAAN
tickers_in_sheet = [t for t in df_active['Ticker'].unique().tolist() if t and t != 'NONE']
m_data = fetch_market(tickers_in_sheet)

openstaande_winst = 0.0
pf_list = []

for _, row in df_active.iterrows():
    t = row['Ticker']
    if t in m_data:
        cur = m_data[t]
        inv = float(row['Inleg'])
        buy = float(row['Koers'])
        netto_waarde = ((inv / buy) * cur['price']) * (0.997 if "." not in t else 1.0)
        winst = netto_waarde - inv
        openstaande_winst += winst
        pf_list.append({
            "Ticker": t, "Inleg": inv, "Aankoop": buy, "Nu": round(cur['price'], 2), 
            "Netto Winst": round(winst, 2), "Status": cur['status']
        })

# Metrics
c1, c2, c3 = st.columns(3)
c1.metric("Gerealiseerde Winst (Log)", f"€{gerealiseerde_winst:.2f}")
c2.metric("Openstaande Winst", f"€{openstaande_winst:.2f}", delta=f"{openstaande_winst:.2f}")
c3.metric("TOTAAL RESULTAAT", f"€{(gerealiseerde_winst + openstaande_winst):.2f}")

st.divider()

tab1, tab2, tab3 = st.tabs(["📊 Actieve Trades", "🔍 Scanner", "📜 Historie (Log)"])

with tab1:
    col_in, col_out = st.columns([1, 2])
    with col_in:
        st.subheader("Nieuwe Trade")
        with st.form("add_sim", clear_on_submit=True):
            t_in = st.text_input("Ticker").upper().strip()
            i_in = st.number_input("Inleg (€)", value=100.0)
            k_in = st.number_input("Koers", value=0.0)
            if st.form_submit_button("Open Positie"):
                requests.post(API_URL, data=json.dumps({"ticker": t_in, "inleg": i_in, "koers": k_in}))
                st.rerun()

    with col_out:
        st.subheader("Lopende Posities")
        if pf_list:
            df_p = pd.DataFrame(pf_list)
            st.dataframe(df_p.style.map(style_action, subset=['Status']), hide_index=True)
            
            # SLUITEN & LOGGEN
            to_del = st.selectbox("Welke trade sluiten?", [""] + df_p['Ticker'].tolist())
            if st.button("Trade Sluiten & Winst Verzilveren"):
                if to_del:
                    # Zoek de huidige winst op om te loggen
                    current_winst = df_p[df_p['Ticker'] == to_del]['Netto Winst'].values[0]
                    requests.post(API_URL, data=json.dumps({
                        "method": "delete", 
                        "ticker": to_del, 
                        "inleg": df_p[df_p['Ticker'] == to_del]['Inleg'].values[0],
                        "winst": current_winst
                    }))
                    st.success(f"Gelogd: €{current_winst} winst!")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("Geen actieve trades.")

with tab2:
    st.subheader("Markt Scanner")
    watchlist = ['NVDA','TSLA','AAPL','MSFT','AMZN','ASML.AS','ADYEN.AS','INGA.AS','PLTR','COIN']
    m_watch = fetch_market(watchlist)
    scan_rows = [{"Ticker": k, "RSI": round(v['rsi'], 1), "Actie": v['status']} for k, v in m_watch.items()]
    st.dataframe(pd.DataFrame(scan_rows).sort_values('RSI').style.map(style_action, subset=['Actie']), use_container_width=True)

with tab3:
    st.subheader("Gesloten Trades")
    if not df_log.empty:
        st.dataframe(df_log.sort_values("Datum", ascending=False), use_container_width=True)
        st.metric("Totaal verdiend in deze periode", f"€{gerealiseerde_winst:.2f}")
    else:
        st.info("Nog geen gesloten trades in het logboek.")