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

# --- CUSTOM CSS VOOR EXTRA COMPACTE LOOK ---
st.markdown("""
    <style>
    [data-testid="stExpander"] { border: 1px solid #f0f2f6; border-radius: 8px; margin-bottom: -15px; }
    .stMetric { padding: 0px !important; }
    div[data-testid="stVerticalBlock"] > div { spacing: 0rem; }
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

@st.cache_data(ttl=300) # Cache koersdata voor 5 minuten voor snelheid
def get_scan_metrics(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1y")
        if len(hist) < 20: return None
        cur = hist['Close'].iloc[-1]
        m6 = hist['Close'].iloc[-126] if len(hist) > 126 else hist['Close'].iloc[0]
        m12 = hist['Close'].iloc[0]
        rsi = ta.rsi(hist['Close'], length=14).iloc[-1]
        return {
            "Ticker": ticker, 
            "Prijs": round(cur, 2), 
            "RSI": round(rsi, 1), 
            "6M %": round(((cur-m6)/m6)*100, 1),
            "12M %": round(((cur-m12)/m12)*100, 1)
        }
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
                c1, c2, c3, c4 = st.columns([1,1,1,0.5])
                c1.write(f"Inleg: €{row['Inleg']:.0f}")
                c2.write(f"Koers: €{cur:.2f}")
                c3.write(f"Res: {((winst/row['Inleg'])*100):.1f}%")
                if c4.button("🗑️", key=f"del_{row['airtable_id']}"):
                    if sell_position(row, cur): st.rerun()
        except: pass
    return total_winst

# --- MAIN DASHBOARD ---
df_p = get_airtable_data(PORTFOLIO_TABLE)
df_l = get_airtable_data(LOG_TABLE)

# WATCHLISTS (15 per categorie)
GROWTH_WATCH = ['NVDA', 'TSLA', 'PLTR', 'AMD', 'ASML.AS', 'ADYEN.AS', 'COIN', 'MSTR', 'META', 'AMZN', 'GOOGL', 'NFLX', 'SHOP', 'SNOW', 'ARM']
DIVIDEND_WATCH = ['KO', 'PEP', 'PG', 'O', 'ABBV', 'JNJ', 'MMM', 'LOW', 'TGT', 'MO', 'T', 'CVX', 'XOM', 'SCHD', 'VICI']

# --- SIDEBAR ---
with st.sidebar:
    st.title("📊 Portfolio")
    
    # Bereken winsten voor sidebar (zonder zware API calls indien mogelijk)
    st.subheader("Winst Overzicht")
    # Voor de sidebar gebruiken we even een snelle loop over de huidige posities
    gw, dw = 0, 0
    if not df_p.empty:
        for _, r in df_p.iterrows():
            try:
                p = yf.Ticker(r['Ticker']).history(period="1d")['Close'].iloc[-1]
                w = ((r['Inleg']/r['Koers']) * p) - r['Inleg']
                if r['Type'] == "Growth": gw += w
                else: dw += w
            except: pass
            
    c_g, c_d = st.columns(2)
    c_g.metric("🚀 Growth", f"€{gw:.2f}")
    c_d.metric("💎 Div.", f"€{dw:.2f}")
    
    st.divider()
    st.subheader("🔔 RSI Alerts (<35)")
    # Check alleen de top 5 van elke lijst voor de sidebar alerts om snelheid te houden
    for t in (GROWTH_WATCH[:5] + DIVIDEND_WATCH[:5]):
        m = get_scan_metrics(t)
        if m and m['RSI'] < 35:
            st.error(f"{t}: RSI {m['RSI']} 🔥")

    st.divider()
    with st.form("add"):
        t_in = st.text_input("Ticker").upper()
        i_in = st.number_input("Inleg", 10)
        k_in = st.number_input("Koers", 0.01)
        s_in = st.selectbox("Type", ["Growth", "Dividend"])
        if st.form_submit_button("Toevoegen"):
            requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{PORTFOLIO_TABLE}", headers=HEADERS, 
                          json={"fields": {"Ticker": t_in, "Inleg": i_in, "Koers": k_in, "Type": s_in}})
            st.rerun()

# --- TABS ---
tab1, tab2, tab3 = st.tabs(["🚀 Growth Strategy", "💎 Dividend Wealth", "📜 Logboek"])

def process_scanner(watchlist, mode):
    results = []
    for t in watchlist:
        m = get_scan_metrics(t)
        if m:
            if mode == "Growth":
                m['Suggestie'] = "🔥 BUY" if m['RSI'] < 35 else "💰 SELL" if m['RSI'] > 70 else "🚀 MOMENTUM" if m['6M %'] > 20 else "⌛ WAIT"
            else:
                m['Suggestie'] = "💎 ACCUMULATE" if m['RSI'] < 45 else "🛡️ HOLD" if m['RSI'] > 65 else "✅ STABLE"
            results.append(m)
    return pd.DataFrame(results)

with tab1:
    col_p, col_s = st.columns([1, 2])
    with col_p:
        st.subheader("Mijn Posities")
        render_portfolio_compact(df_p, "Growth")
    with col_s:
        st.subheader("Market Scanner (Top 15)")
        df_growth = process_scanner(GROWTH_WATCH, "Growth")
        st.dataframe(df_growth, use_container_width=True, hide_index=True)

with tab2:
    col_p2, col_s2 = st.columns([1, 2])
    with col_p2:
        st.subheader("Mijn Posities")
        render_portfolio_compact(df_p, "Dividend")
    with col_s2:
        st.subheader("Dividend Aristocrats Scanner")
        df_div = process_scanner(DIVIDEND_WATCH, "Dividend")
        st.dataframe(df_div, use_container_width=True, hide_index=True)

with tab3:
    if not df_l.empty:
        st.dataframe(df_l.sort_values(by='Datum', ascending=False), use_container_width=True, hide_index=True)
        if st.button("Wis Logboek"):
            for rid in df_l['airtable_id']: requests.delete(f"https://api.airtable.com/v0/{BASE_ID}/{LOG_TABLE}/{rid}", headers=HEADERS)
            st.rerun()