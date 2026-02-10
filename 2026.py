import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="Daytrade Simulator Pro 2026")

# Jouw nieuwe API URL
API_URL = "https://script.google.com/macros/s/AKfycby_mNzpbSGjHsam9x6IXAK_mJBdwbImbTYTa3oErSZ-SNqHQ1e7VU2NVKzh_Ptk5rbN/exec"

# --- SIDEBAR: SIMULATOR & RESET ---
with st.sidebar:
    st.header("⚙️ Dashboard Instellingen")
    sim_mode = st.toggle("🛠️ Simulator Modus", value=True, help="Schakel tussen test-traden en echt werk.")
    
    st.divider()
    st.subheader("Data Beheer")
    if st.button("🚨 RESET ALLES (Log + Active)", help="Wist de volledige Google Sheet geschiedenis"):
        try:
            requests.post(API_URL, data=json.dumps({"method": "reset_all"}))
            st.warning("Data wordt gewist...")
            time.sleep(1.5)
            st.rerun()
        except:
            st.error("Reset mislukt. Controleer API.")

if sim_mode:
    st.info("🔵 **SIMULATOR MODUS ACTIEF**")
else:
    st.warning("🔴 **LIVE MODUS ACTIEF**")

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
        
        active_raw = res.get('active', [])
        log_raw = res.get('log', [])

        if len(active_raw) < 2:
            df_active = pd.DataFrame(columns=["Ticker", "Inleg", "Koers"])
        else:
            df_active = pd.DataFrame(active_raw[1:], columns=["Ticker", "Inleg", "Koers"])
            df_active['Inleg'] = pd.to_numeric(df_active['Inleg'], errors='coerce')
            df_active['Koers'] = pd.to_numeric(df_active['Koers'], errors='coerce')

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
            
            # Trend Berekeningen
            p6m = h['Close'].iloc[-126] if len(h) >= 126 else h['Close'].iloc[0]
            trend6m = ((price - p6m) / p6m) * 100
            
            p12m = h['Close'].iloc[0]
            trend12m = ((price - p12m) / p12m) * 100
            
            status = "WAIT"
            if rsi < 35: status = "BUY"
            elif rsi > 65: status = "SELL"
            
            results[t] = {
                "price": price, "rsi": rsi, "status": status, 
                "trend6m": trend6m, "trend12m": trend12m
            }
        except: continue
    return results

# --- DATA OPHALEN ---
df_active, df_log = get_all_data()
gerealiseerde_winst = df_log['Winst'].sum() if not df_log.empty else 0.0

# --- UI OPBOUW ---
st.title("⚡ Pro Daytrade Dashboard")

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
        waarde_bruto = (inv / buy) * cur['price']
        netto_waarde = waarde_bruto * (0.997 if "." not in t else 1.0)
        winst = netto_waarde - inv
        openstaande_winst += winst
        pf_list.append({
            "Ticker": t, "Inleg": inv, "Aankoop": buy, "Nu": round(cur['price'], 2), 
            "Netto Winst": round(winst, 2), "Status": cur['status']
        })

# Metrics
m1, m2, m3 = st.columns(3)
m1.metric("Gerealiseerde Winst", f"€{gerealiseerde_winst:.2f}")
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
            to_del = st.selectbox("Trade beëindigen?", [""] + df_p['Ticker'].tolist())
            if st.button("Trade Sluiten & Resultaat Loggen"):
                if to_del:
                    row_data = df_p[df_p['Ticker'] == to_del].iloc[0]
                    requests.post(API_URL, data=json.dumps({
                        "method": "delete", "ticker": to_del, 
                        "inleg": row_data['Inleg'], "winst": row_data['Netto Winst']
                    }))
                    st.rerun()
        else: st.info("Geen actieve posities.")

with tab2:
    st.subheader("🔍 Market Scanner met Trends")
    watchlist = ['NVDA','TSLA','AAPL','MSFT','AMZN','META','AMD','ASML.AS','ADYEN.AS','INGA.AS','SHELL.AS','PLTR','COIN']
    m_watch = fetch_market(watchlist)
    if m_watch:
        scan_rows = [{"Ticker": k, "Prijs": round(v['price'], 2), "RSI": round(v['rsi'], 1), 
                      "6M Trend": f"{v['trend6m']:.1f}%", "12M Trend": f"{v['trend12m']:.1f}%", 
                      "Actie": v['status']} for k, v in m_watch.items()]
        st.dataframe(pd.DataFrame(scan_rows).sort_values('RSI').style.map(style_action, subset=['Actie']), 
                     use_container_width=True, hide_index=True)

with tab3:
    st.subheader("📜 Gerealiseerd overzicht")
    if not df_log.empty:
        # Toon het logboek
        st.dataframe(df_log.sort_values('Datum', ascending=False), use_container_width=True, hide_index=True)
        
        st.divider()
        st.subheader("🛠️ Historie bewerken")
        
        # Maak een lijst van trades om te kunnen verwijderen (Ticker + Winst voor identificatie)
        log_options = []
        for i, r in df_log.iterrows():
            log_options.append(f"{r['Ticker']} (Winst: €{r['Winst']:.2f})")
        
        to_delete_log = st.selectbox("Selecteer een trade om te verwijderen uit de historie:", [""] + log_options)
        
        if st.button("❌ Verwijder geselecteerde trade uit Log"):
            if to_delete_log:
                # Extraheer ticker en winst uit de selectie
                selected_ticker = to_delete_log.split(" (")[0]
                selected_winst = to_delete_log.split("€")[-1].replace(")", "")
                
                requests.post(API_URL, data=json.dumps({
                    "method": "delete_log_entry",
                    "ticker": selected_ticker,
                    "winst": float(selected_winst)
                }))
                st.toast(f"{selected_ticker} verwijderd uit historie")
                time.sleep(1)
                st.rerun()
    else:
        st.info("Het logboek is nog leeg.")

