import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import time
from datetime import datetime

# --- CONFIG ---
AIRTABLE_TOKEN = "patCdgzOgVDPNlGCw.3008de99d994972e122dc62031b3f5aa5f2647cfa75c5ac67215dc72eba2ce07"
BASE_ID = "appgvzDsvbvKi7e45"
PORTFOLIO_TABLE = "Portfolio"
LOG_TABLE = "Logboek"

HEADERS = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}

st.set_page_config(layout="wide", page_title="Professional Trader Dashboard 2026")

# --- DATA FUNCTIES ---
def get_airtable_data(table_name):
    try:
        url = f"https://api.airtable.com/v0/{BASE_ID}/{table_name}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            records = r.json().get('records', [])
            rows = []
            for rec in records:
                row = rec['fields']
                row['airtable_id'] = rec['id']
                rows.append(row)
            return pd.DataFrame(rows)
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def sell_position(row, current_price):
    aantal = row['Inleg'] / row['Koers'] if row['Koers'] > 0 else 0
    verkoopwaarde = aantal * current_price
    winst_eur = verkoopwaarde - row['Inleg']
    rendement = (winst_eur / row['Inleg'] * 100) if row['Inleg'] > 0 else 0
    
    log_payload = {
        "fields": {
            "Ticker": str(row['Ticker']).upper(),
            "Inleg": float(row['Inleg']),
            "Verkoopwaarde": round(float(verkoopwaarde), 2),
            "Winst_Euro": round(float(winst_eur), 2),
            "Rendement_Perc": round(float(rendement), 2),
            "Type": row.get('Type', 'Growth'),
            "Datum": datetime.now().strftime('%Y-%m-%d')
        }
    }
    res = requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{LOG_TABLE}", headers=HEADERS, json=log_payload)
    if res.status_code == 200:
        requests.delete(f"https://api.airtable.com/v0/{BASE_ID}/{PORTFOLIO_TABLE}/{row['airtable_id']}", headers=HEADERS)
        return True
    return False

def clear_logbook(df_log):
    """Verwijdert alle records uit de Logboek tabel in Airtable."""
    with st.spinner("Logboek wordt geleegd..."):
        for record_id in df_log['airtable_id']:
            url = f"https://api.airtable.com/v0/{BASE_ID}/{LOG_TABLE}/{record_id}"
            requests.delete(url, headers=HEADERS)
        return True

# --- SCANNER LOGICA ---
def get_scan_metrics(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1y")
        if len(hist) < 20: return None
        cur_price = hist['Close'].iloc[-1]
        m6_price = hist['Close'].iloc[-126] if len(hist) > 126 else hist['Close'].iloc[0]
        m12_price = hist['Close'].iloc[0]
        perf_6m = ((cur_price - m6_price) / m6_price) * 100
        perf_12m = ((cur_price - m12_price) / m12_price) * 100
        rsi = ta.rsi(hist['Close'], length=14).iloc[-1]
        return {
            "Ticker": ticker, "Prijs": round(cur_price, 2), "RSI": round(rsi, 1),
            "6M %": round(perf_6m, 1), "12M %": round(perf_12m, 1)
        }
    except: return None

def render_scanner_table(watchlist, strategy_mode):
    st.subheader(f"🔍 {strategy_mode} Scanner & Suggesties")
    results = []
    for ticker in watchlist:
        data = get_scan_metrics(ticker)
        if data:
            rsi, p6 = data['RSI'], data['6M %']
            if strategy_mode == "Growth":
                if rsi < 35: sug = "🔥 BUY THE DIP"
                elif rsi > 75: sug = "💰 TAKE PROFIT"
                elif p6 > 20: sug = "🚀 MOMENTUM"
                else: sug = "⌛ WAIT"
            else:
                if rsi < 45: sug = "💎 ACCUMULATE"
                elif rsi > 65: sug = "🛡️ HOLD"
                else: sug = "✅ STABLE"
            data['Suggestie'] = sug
            results.append(data)
    
    if results:
        df_scan = pd.DataFrame(results)
        def highlight_sug(val):
            color = '#2ecc71' if 'BUY' in val or 'ACCUMULATE' in val else '#e74c3c' if 'PROFIT' in val else '#3498db' if 'MOMENTUM' in val else '#7f8c8d'
            return f'background-color: {color}; color: white'
        st.dataframe(df_scan.style.applymap(highlight_sug, subset=['Suggestie']), use_container_width=True, hide_index=True)

def render_portfolio_section(data, strategy_name):
    subset = data[data['Type'] == strategy_name] if 'Type' in data.columns else pd.DataFrame()
    if subset.empty:
        st.info(f"Geen actieve {strategy_name} posities.")
        return
    for _, row in subset.iterrows():
        ticker = str(row['Ticker']).upper()
        try:
            t = yf.Ticker(ticker)
            cur_price = t.history(period="1d")['Close'].iloc[-1]
            aantal = row['Inleg'] / row['Koers']
            waarde = aantal * cur_price
            winst = waarde - row['Inleg']
            with st.expander(f"{ticker} | Winst: €{winst:.2f}", expanded=True):
                c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                c1.metric("Inleg", f"€{row['Inleg']:.2f}")
                c2.metric("Huidige Waarde", f"€{waarde:.2f}")
                c3.metric("Koers", f"€{cur_price:.2f}")
                if c4.button("⚡ Verkoop", key=f"s_{strategy_name}_{row['airtable_id']}"):
                    if sell_position(row, cur_price):
                        st.success("Verkocht!")
                        time.sleep(0.5)
                        st.rerun()
        except: st.warning(f"Kon {ticker} niet laden.")

# --- MAIN APP ---
st.title("💼 My Trading Station 2026")
df_p = get_airtable_data(PORTFOLIO_TABLE)
df_l = get_airtable_data(LOG_TABLE)

tab1, tab2, tab3 = st.tabs(["🚀 Daytrade / Growth", "💎 Dividend Aristocrats", "📜 Logboek"])

with tab1:
    render_portfolio_section(df_p, "Growth")
    st.divider()
    render_scanner_table(['NVDA', 'TSLA', 'PLTR', 'AMD', 'COIN', 'MSTR', 'ASML.AS'], "Growth")

with tab2:
    render_portfolio_section(df_p, "Dividend")
    st.divider()
    render_scanner_table(['KO', 'PEP', 'PG', 'JNJ', 'MMM', 'ABBV', 'O', 'LOW', 'MO', 'T'], "Dividend")

with tab3:
    st.header("Gerealiseerde Resultaten")
    if not df_l.empty:
        cols = ['Ticker', 'Inleg', 'Verkoopwaarde', 'Winst_Euro', 'Rendement_Perc', 'Type', 'Datum']
        existing = [c for c in cols if c in df_l.columns]
        st.dataframe(df_l[existing].sort_values(by='Datum', ascending=False) if 'Datum' in df_l.columns else df_l[existing], use_container_width=True, hide_index=True)
        
        # --- WIS KNOP SECTIE ---
        st.divider()
        st.subheader("⚠️ Gegevensbeheer")
        col_abc, col_def = st.columns([1, 2])
        confirm = col_abc.checkbox("Ik wil het logboek definitief wissen")
        if confirm:
            if col_abc.button("🗑️ Wis nu alle records"):
                if clear_logbook(df_l):
                    st.success("Logboek volledig gewist!")
                    time.sleep(1)
                    st.rerun()
    else:
        st.info("Nog geen verkopen geregistreerd.")

with st.sidebar:
    st.header("➕ Nieuwe Positie")
    with st.form("add_pos", clear_on_submit=True):
        t = st.text_input("Ticker").upper()
        i = st.number_input("Inleg (€)", 10)
        k = st.number_input("Aankoopkoers", 0.01)
        s = st.selectbox("Type", ["Growth", "Dividend"])
        if st.form_submit_button("Toevoegen"):
            requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{PORTFOLIO_TABLE}", headers=HEADERS, 
                          json={"fields": {"Ticker": t, "Inleg": i, "Koers": k, "Type": s}})
            st.success("Toegevoegd!")
            time.sleep(1)
            st.rerun()