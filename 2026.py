import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="Daytrade Simulator Pro 2026")
API_URL = "https://script.google.com/macros/s/AKfycbzU-jPm0qN-qMcucZ7pPklhWhAPyR7A3izSfW9UTtISrnSyHETK5ngTg8tS1-gEMVQ/exec"

# --- SIDEBAR: SIMULATOR & RESET ---
with st.sidebar:
    st.header("⚙️ Dashboard Instellingen")
    # DE TERUGGEKEERDE KNOP:
    sim_mode = st.toggle("🛠️ Simulator Modus", value=True, help="Schakel tussen test-traden en serieus werk.")
    
    st.divider()
    st.subheader("Data Beheer")
    if st.button("🚨 RESET ALLES (Log + Active)", help="Wist de volledige Google Sheet"):
        requests.post(API_URL, data=json.dumps({"method": "reset_all"}))
        st.warning("Data wordt gewist...")
        time.sleep(1.5)
        st.rerun()

# Visuele indicatie voor modus
if sim_mode:
    st.info("🔵 **SIMULATOR MODUS ACTIEF** - Je werkt met fictief kapitaal.")
else:
    st.warning("🔴 **LIVE MODUS** - Let op: Dit zijn je werkelijke posities.")

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
        
        # Actieve trades
        active_raw = res.get('active', [])
        if len(active_raw) < 2:
            df_active = pd.DataFrame(columns=["Ticker", "Inleg", "Koers"])
        else:
            df_active = pd.DataFrame(active_raw[1:], columns=["Ticker", "Inleg", "Koers"])
            df_active['Ticker'] = df_active['Ticker'].astype(str).str.strip().str.upper()
            df_active['Inleg'] = pd.to_numeric(df_active['Inleg'], errors='coerce')
            df_active['Koers'] = pd.to_numeric(df_active['Koers'], errors='coerce')

        # Logboek
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

# --- UI OPBOUW ---
st.title("⚡ Pro Daytrade Dashboard")

# Live koersen voor actieve portfolio
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
        # FX correctie (0.3% voor US aandelen)
        waarde_bruto = (inv / buy) * cur['price']
        netto_waarde = waarde_bruto * (0.997 if "." not in t else 1.0)
        winst = netto_waarde - inv
        openstaande_winst += winst
        pf_list.append({
            "Ticker": t, "Inleg": inv, "Aankoop": buy, "Nu": round(cur['price'], 2), 
            "Netto Winst": round(winst, 2), "Status": cur['status']
        })

# Metrics bovenaan
m1, m2, m3 = st.columns(3)
m1.metric("Gerealiseerde Winst (Log)", f"€{gerealiseerde_winst:.2f}")
m2.metric("Openstaande Winst", f"€{openstaande_winst:.2f}", delta=f"{openstaande_winst:.2f}")
m3.metric("TOTAAL RESULTAAT", f"€{(gerealiseerde_winst + openstaande_winst):.2f}")

st.divider()

tab1, tab2, tab3 = st.tabs(["📊 Portfolio Beheer", "🔍 Market Scanner", "📜 Historie (Log)"])

with tab1:
    c_in, c_out = st.columns([1, 2])
    with c_in:
        st.subheader("Nieuwe Positie")
        with st.form("add_trade", clear_on_submit=True):
            t_in = st.text_input("Ticker").upper().strip()
            i_in = st.number_input("Inleg (€)", value=100.0)
            k_in = st.number_input("Koers", value=0.0)
            if st.form_submit_button("Voeg toe aan Portfolio"):
                if t_in and k_in > 0:
                    requests.post(API_URL, data=json.dumps({"ticker": t_in, "inleg": i_in, "koers": k_in}))
                    st.rerun()

    with c_out:
        st.subheader("Actuele Posities")
        if pf_list:
            df_p = pd.DataFrame(pf_list)
            st.dataframe(df_p.style.map(style_action, subset=['Status']), hide_index=True, use_container_width=True)
            
            st.divider()
            to_del = st.selectbox("Trade beëindigen?", [""] + df_p['Ticker'].tolist())
            if st.button("Trade Sluiten & Resultaat Loggen"):
                if to_del:
                    row_data = df_p[df_p['Ticker'] == to_del].iloc[0]
                    requests.post(API_URL, data=json.dumps({
                        "method": "delete", 
                        "ticker": to_del, 
                        "inleg": row_data['Inleg'],
                        "winst": row_data['Netto Winst']
                    }))
                    st.success(f"{to_del} verplaatst naar Logboek.")
                    time.sleep(1)
                    st.rerun()
        else:
            st.info("Geen actieve posities gevonden.")

with tab2:
    st.subheader("Top 25 Scanner")
    watchlist = ['NVDA','TSLA','AAPL','MSFT','AMZN','META','AMD','ASML.AS','ADYEN.AS','INGA.AS','SHELL.AS','PLTR','COIN']
    m_watch = fetch_market(watchlist)
    scan_rows = [{"Ticker": k, "RSI": round(v['rsi'], 1), "Actie": v['status']} for k, v in m_watch.items()]
    if scan_rows:
        st.dataframe(pd.DataFrame(scan_rows).sort_values('RSI').style.map(style_action, subset=['Actie']), use_container_width=True)

with tab3:
    st.subheader("Logboek (Gesloten Trades)")
    if not df_log.empty:
        # Toon historie met nieuwste bovenaan
        st.dataframe(df_log.iloc[::-1], use_container_width=True, hide_index=True)
        st.metric("Cumulatief Resultaat", f"€{gerealiseerde_winst:.2f}")
    else:

        st.info("Het logboek is nog leeg. Sluit een trade om de historie te vullen.")
