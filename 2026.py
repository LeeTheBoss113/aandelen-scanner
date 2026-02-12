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

st.set_page_config(layout="wide", page_title="Trader Dashboard 2026", initial_sidebar_state="expanded")

# --- CUSTOM CSS VOOR COMPACTE LAYOUT ---
st.markdown("""
    <style>
    [data-testid="stExpander"] { border: 1px solid #f0f2f6; border-radius: 10px; margin-bottom: -10px; }
    .stMetric { padding: 0px !important; }
    </style>
    """, unsafe_allow_html=True)

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
    except: return pd.DataFrame()

def sell_position(row, current_price):
    aantal = row['Inleg'] / row['Koers'] if row['Koers'] > 0 else 0
    verkoopwaarde = aantal * current_price
    winst_eur = verkoopwaarde - row['Inleg']
    log_payload = {
        "fields": {
            "Ticker": str(row['Ticker']).upper(),
            "Inleg": float(row['Inleg']),
            "Verkoopwaarde": round(float(verkoopwaarde), 2),
            "Winst_Euro": round(float(winst_eur), 2),
            "Rendement_Perc": round((winst_eur/row['Inleg']*100), 2) if row['Inleg'] > 0 else 0,
            "Type": row.get('Type', 'Growth'),
            "Datum": datetime.now().strftime('%Y-%m-%d')
        }
    }
    res = requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{LOG_TABLE}", headers=HEADERS, json=log_payload)
    if res.status_code == 200:
        requests.delete(f"https://api.airtable.com/v0/{BASE_ID}/{PORTFOLIO_TABLE}/{row['airtable_id']}", headers=HEADERS)
        return True
    return False

# --- SCANNER & METRICS LOGICA ---
def get_scan_metrics(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1y")
        if len(hist) < 20: return None
        cur = hist['Close'].iloc[-1]
        m6 = hist['Close'].iloc[-126] if len(hist) > 126 else hist['Close'].iloc[0]
        rsi = ta.rsi(hist['Close'], length=14).iloc[-1]
        return {"Ticker": ticker, "Prijs": cur, "RSI": rsi, "6M": ((cur-m6)/m6)*100}
    except: return None

# --- UI COMPONENTEN ---
def render_portfolio_compact(df, strategy_name):
    subset = df[df['Type'] == strategy_name] if not df.empty and 'Type' in df.columns else pd.DataFrame()
    total_winst = 0
    
    if subset.empty:
        st.info(f"Geen {strategy_name} posities.")
        return 0

    for _, row in subset.iterrows():
        ticker = str(row['Ticker']).upper()
        try:
            t = yf.Ticker(ticker)
            cur = t.history(period="1d")['Close'].iloc[-1]
            aantal = row['Inleg'] / row['Koers']
            winst = (aantal * cur) - row['Inleg']
            total_winst += winst
            
            with st.expander(f"**{ticker}** | Winst: **€{winst:.2f}**"):
                c1, c2, c3, c4 = st.columns([1,1,1,1])
                c1.metric("Inleg", f"€{row['Inleg']:.0f}")
                c2.metric("Koers", f"€{cur:.2f}")
                c3.metric("Resultaat", f"{((winst/row['Inleg'])*100):.1f}%")
                if c4.button("🗑️", key=f"s_{row['airtable_id']}"):
                    if sell_position(row, cur): st.rerun()
        except: pass
    return total_winst

# --- MAIN ---
df_p = get_airtable_data(PORTFOLIO_TABLE)
df_l = get_airtable_data(LOG_TABLE)

# SIDEBAR BEREKENINGEN & ALERTS
with st.sidebar:
    st.title("📊 Overzicht")
    
    # Winsten berekenen voor sidebar
    winst_growth = render_portfolio_compact(df_p, "Growth") if False else 0 # Dummy call om winst te tellen
    # (Bovenstaande is niet efficient, we doen het even opnieuw voor de sidebar)
    
    def calc_sidebar_winst(df, strat):
        if df.empty or 'Type' not in df.columns: return 0
        s = df[df['Type'] == strat]
        tw = 0
        for _, r in s.iterrows():
            try:
                # We gebruiken even een snelle cache of we slaan het op in session_state voor snelheid
                tw += ((r['Inleg']/r['Koers']) * yf.Ticker(r['Ticker']).history(period="1d")['Close'].iloc[-1]) - r['Inleg']
            except: pass
        return tw

    st.subheader("Portefeuille Winst")
    col_a, col_b = st.columns(2)
    # Let op: Dit kan traag zijn bij veel tickers, optimalisatie volgt in gebruik
    gw = calc_sidebar_winst(df_p, "Growth")
    dw = calc_sidebar_winst(df_p, "Dividend")
    col_a.metric("🚀 Growth", f"€{gw:.2f}")
    col_b.metric("💎 Dividend", f"€{dw:.2f}")
    
    st.divider()
    st.subheader("🔔 RSI Alerts (<30)")
    watchlist = ['NVDA', 'TSLA', 'ASML.AS', 'KO', 'PEP']
    for t_name in watchlist:
        m = get_scan_metrics(t_name)
        if m and m['RSI'] < 35:
            st.error(f"ALERT: {t_name} is Oversold! (RSI: {m['RSI']:.1f})")

    st.divider()
    with st.form("add_pos", clear_on_submit=True):
        st.subheader("➕ Nieuwe Order")
        t = st.text_input("Ticker")
        i = st.number_input("Inleg", 10)
        k = st.number_input("Koers", 0.01)
        s = st.selectbox("Type", ["Growth", "Dividend"])
        if st.form_submit_button("Toevoegen"):
            requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{PORTFOLIO_TABLE}", headers=HEADERS, 
                          json={"fields": {"Ticker": t.upper(), "Inleg": i, "Koers": k, "Type": s}})
            st.rerun()

# TABS
tab1, tab2, tab3 = st.tabs(["🚀 Growth", "💎 Dividend", "📜 Logboek"])

with tab1:
    render_portfolio_compact(df_p, "Growth")
    st.divider()
    # Scanner
    results = []
    for t in ['NVDA', 'TSLA', 'PLTR', 'AMD', 'ASML.AS']:
        m = get_scan_metrics(t)
        if m:
            m['Suggestie'] = "🔥 BUY" if m['RSI'] < 35 else "💰 SELL" if m['RSI'] > 70 else "⌛ WAIT"
            results.append(m)
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

with tab2:
    render_portfolio_compact(df_p, "Dividend")
    st.divider()
    div_results = []
    for t in ['KO', 'PEP', 'PG', 'O', 'ABBV']:
        m = get_scan_metrics(t)
        if m:
            m['Suggestie'] = "💎 ACCUMULATE" if m['RSI'] < 45 else "✅ STABLE"
            div_results.append(m)
    st.dataframe(pd.DataFrame(div_results), use_container_width=True, hide_index=True)

with tab3:
    st.subheader("Historie")
    if not df_l.empty:
        st.dataframe(df_l.sort_values(by='Datum', ascending=False), use_container_width=True)
        if st.checkbox("Wis Logboek"):
            if st.button("Bevestig Wissen"):
                for rid in df_l['airtable_id']:
                    requests.delete(f"https://api.airtable.com/v0/{BASE_ID}/{LOG_TABLE}/{rid}", headers=HEADERS)
                st.rerun()