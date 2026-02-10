import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="Daytrade Dashboard Pro 2026")
API_URL = "https://script.google.com/macros/s/AKfycbyhZxfS0WjCo-oT9n1j9fXrGd5Y7gE2ymU2g2SNSBv49P0be9W6ySsKFgc7QjCySnKm/exec"

# --- SIDEBAR: SIMULATOR & RESET ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    sim_mode = st.toggle("🛠️ Simulator Modus", value=False, help="Indien aan, wordt de data als test gemarkeerd.")
    
    st.divider()
    st.subheader("Schoonmaken")
    if st.button("🚨 RESET ALL DATA", help="Verwijder alle trades uit de Google Sheet"):
        # We sturen een speciaal commando naar ons script om alles te wissen
        requests.post(API_URL, data=json.dumps({"method": "reset_all"}))
        st.warning("Sheet wordt geleegd...")
        time.sleep(2)
        st.rerun()

if sim_mode:
    st.info("🟡 JE BENT NU IN SIMULATOR MODUS. Geen echt geld risico.")

# --- DATA FUNCTIES ---
def style_action(val):
    if val == 'BUY': color = '#2ecc71'
    elif val == 'SELL': color = '#e74c3c'
    elif val == 'WAIT': color = '#f1c40f'
    else: color = '#3498db'
    return f'background-color: {color}; color: white; font-weight: bold'

def get_sheet_data():
    try:
        r = requests.get(f"{API_URL}?t={int(time.time())}", timeout=10)
        data = r.json()
        if not data or len(data) < 2: return pd.DataFrame(columns=["Ticker", "Inleg", "Koers"])
        df = pd.DataFrame(data[1:], columns=["Ticker", "Inleg", "Koers"])
        df['Ticker'] = df['Ticker'].astype(str).str.strip().str.upper()
        df['Inleg'] = pd.to_numeric(df['Inleg'], errors='coerce')
        df['Koers'] = pd.to_numeric(df['Koers'], errors='coerce')
        return df.dropna(subset=['Ticker'])
    except:
        return pd.DataFrame(columns=["Ticker", "Inleg", "Koers"])

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
            p6m = h['Close'].iloc[-126] if len(h) > 126 else h['Close'].iloc[0]
            trend = ((price - p6m) / p6m) * 100
            results[t] = {"price": price, "rsi": rsi, "status": status, "trend": trend}
        except: continue
    return results

# --- UI ---
st.title("⚡ Pro Daytrade Connector 2026")

tab1, tab2 = st.tabs(["📊 Portfolio / Simulator", "🔍 Market Scanner"])

with tab1:
    col_input, col_display = st.columns([1, 2.5])
    
    with col_input:
        label = "Nieuwe Test Positie" if sim_mode else "Nieuwe Echte Positie"
        st.subheader(label)
        with st.form("add_trade", clear_on_submit=True):
            t_in = st.text_input("Ticker (bv. NVDA)").upper().strip()
            i_in = st.number_input("Virtuele Inleg (€)" if sim_mode else "Inleg (€)", value=100.0, step=50.0)
            k_in = st.number_input("Huidige Koers", value=0.0, format="%.2f")
            if st.form_submit_button("Opslaan"):
                if t_in and k_in > 0:
                    requests.post(API_URL, data=json.dumps({"ticker": t_in, "inleg": i_in, "koers": k_in}))
                    st.success(f"{t_in} toegevoegd aan de lijst!")
                    time.sleep(1)
                    st.rerun()

    with col_display:
        st.subheader("Huidige Stand van Zaken")
        df_sheet = get_sheet_data()
        
        if not df_sheet.empty:
            tickers_in_sheet = [t for t in df_sheet['Ticker'].unique().tolist() if t and t != 'NONE']
            if tickers_in_sheet:
                m_data = fetch_market(tickers_in_sheet)
                pf_list = []
                total_inleg = 0
                total_waarde_netto = 0
                
                for _, row in df_sheet.iterrows():
                    t = row['Ticker']
                    if t in m_data:
                        cur = m_data[t]
                        inv = float(row['Inleg'])
                        buy = float(row['Koers'])
                        
                        waarde_bruto = (inv / buy) * cur['price']
                        kosten_factor = 0.0030 if "." not in t else 0.0
                        netto_waarde = waarde_bruto * (1 - kosten_factor)
                        netto_winst = netto_waarde - inv
                        
                        total_inleg += inv
                        total_waarde_netto += netto_waarde
                        
                        pf_list.append({
                            "Ticker": t, "Inleg": inv, "Nu": round(cur['price'], 2), 
                            "Netto Waarde": round(netto_waarde, 2), "Netto Winst": round(netto_winst, 2), "Status": cur['status']
                        })
                
                if pf_list:
                    total_pnl = total_waarde_netto - total_inleg
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Totale Inleg", f"€{total_inleg:.2f}")
                    c2.metric("Netto Waarde", f"€{total_waarde_netto:.2f}")
                    c3.metric("Netto Resultaat", f"€{total_pnl:.2f}", delta=f"{((total_pnl/total_inleg)*100 if total_inleg > 0 else 0):.2f}%")
                    
                    st.divider()
                    st.dataframe(
                        pd.DataFrame(pf_list).style.map(style_action, subset=['Status'])
                        .format({"Inleg": "€{:.2f}", "Netto Waarde": "€{:.2f}", "Netto Winst": "€{:.2f}"}), 
                        hide_index=True, use_container_width=True
                    )
                    
                    to_del = st.selectbox("Ticker verwijderen?", [""] + [p['Ticker'] for p in pf_list])
                    if st.button("🗑️ Verwijder") and to_del:
                        requests.post(API_URL, data=json.dumps({"method": "delete", "ticker": to_del}))
                        st.rerun()

with tab2:
    st.subheader("Market Scanner")
    watchlist = ['NVDA','TSLA','AAPL','MSFT','AMZN','META','AMD','ASML.AS','ADYEN.AS','INGA.AS','SHELL.AS','PLTR','COIN']
    m_watch = fetch_market(watchlist)
    scan_rows = [{"Ticker": k, "Prijs": round(v['price'], 2), "RSI": round(v['rsi'], 1), "6M Trend": f"{v['trend']:.1f}%", "Actie": v['status']} for k, v in m_watch.items()]
    if scan_rows:
        st.dataframe(pd.DataFrame(scan_rows).sort_values('RSI').style.map(style_action, subset=['Actie']), hide_index=True, use_container_width=True)