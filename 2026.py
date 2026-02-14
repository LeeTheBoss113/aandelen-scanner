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

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    [data-testid="stExpander"] { border: 1px solid #f0f2f6; border-radius: 8px; margin-bottom: -15px; }
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
    vw = aantal * current_price
    winst = vw - row['Inleg']
    log_payload = {
        "fields": {
            "Ticker": str(row['Ticker']).upper(),
            "Inleg": float(row['Inleg']),
            "Verkoopwaarde": round(float(vw), 2),
            "Winst_Euro": round(float(winst), 2),
            "Rendement_Perc": round((winst/row['Inleg']*100), 2) if row['Inleg'] > 0 else 0,
            "Type": row.get('Type', 'Growth'),
            "Datum": datetime.now().strftime('%Y-%m-%d')
        }
    }
    res = requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{LOG_TABLE}", headers=HEADERS, json=log_payload)
    if res.status_code == 200:
        requests.delete(f"https://api.airtable.com/v0/{BASE_ID}/{PORTFOLIO_TABLE}/{row['airtable_id']}", headers=HEADERS)
        return True
    return False

@st.cache_data(ttl=300)
def get_scan_metrics(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="1y")
        if len(hist) < 20: return None
        cur = hist['Close'].iloc[-1]
        m6 = hist['Close'].iloc[-126] if len(hist) > 126 else hist['Close'].iloc[0]
        rsi = ta.rsi(hist['Close'], length=14).iloc[-1]
        p6 = ((cur-m6)/m6)*100
        
        # Trend bepalen op basis van Momentum (6 maanden)
        trend_icon = "📈 Bullish" if p6 > 5 else "📉 Bearish" if p6 < -5 else "➡️ Side"
        
        return {
            "Ticker": ticker, 
            "Trend": trend_icon,
            "Prijs": round(cur, 2), 
            "RSI": round(rsi, 1), 
            "6M %": round(p6, 1),
            "12M %": round(((cur-hist['Close'].iloc[0])/hist['Close'].iloc[0])*100, 1)
        }
    except: return None

# --- UI ---
df_p = get_airtable_data(PORTFOLIO_TABLE)
df_l = get_airtable_data(LOG_TABLE)

GROWTH_WATCH = ['NVDA', 'TSLA', 'PLTR', 'AMD', 'ASML.AS', 'ADYEN.AS', 'COIN', 'MSTR', 'META', 'AMZN', 'GOOGL', 'NFLX', 'SHOP', 'SNOW', 'ARM']
DIVIDEND_WATCH = ['KO', 'PEP', 'PG', 'O', 'ABBV', 'JNJ', 'MMM', 'LOW', 'TGT', 'MO', 'T', 'CVX', 'XOM', 'SCHD', 'VICI']

with st.sidebar:
    st.title("📊 My Brain Helper")
    
    # SNELLE SPIEKBRIEF VOOR HET BREIN
    with st.expander("ℹ️ Wat betekende het ook alweer?", expanded=False):
        st.write("**Momentum:** De vaart van de koers. Als de trein eenmaal rijdt (6M > 20%), denderen we vaak door.")
        st.write("**RSI < 35:** Aandeel is 'onderkoeld'. Vaak een mooi koopmoment (Dip).")
        st.write("**RSI > 70:** Aandeel is 'oververhit'. Misschien tijd om wat winst te pakken.")

    st.divider()
    # Totaal Winst berekening
    gw, dw = 0, 0
    if not df_p.empty:
        for _, r in df_p.iterrows():
            try:
                p = yf.Ticker(r['Ticker']).history(period="1d")['Close'].iloc[-1]
                w = ((r['Inleg']/r['Koers']) * p) - r['Inleg']
                if r['Type'] == "Growth": gw += w
                else: dw += w
            except: pass
    
    st.metric("🚀 Totaal Growth Winst", f"€{gw:.2f}")
    st.metric("💎 Totaal Dividend Winst", f"€{dw:.2f}")
    
    st.divider()
    st.subheader("🔔 RSI Alerts (<35)")
    for t in (GROWTH_WATCH[:5] + DIVIDEND_WATCH[:5]):
        m = get_scan_metrics(t)
        if m and m['RSI'] < 35:
            st.error(f"KOOPKANS: {t} (RSI: {m['RSI']})")

tab1, tab2, tab3 = st.tabs(["🚀 Growth", "💎 Dividend", "📜 Logboek"])

def show_scanner(watchlist, mode, df_portfolio):
    results = []
    # Maak een lijst van tickers die we al bezitten voor snelle check
    owned_tickers = []
    if not df_portfolio.empty:
        owned_tickers = df_portfolio['Ticker'].str.upper().tolist()

    for t in watchlist:
        m = get_scan_metrics(t)
        if m:
            if mode == "Growth":
                m['Suggestie'] = "🔥 BUY DIP" if m['RSI'] < 35 else "💰 SELL" if m['RSI'] > 75 else "🚀 MOMENTUM" if m['6M %'] > 15 else "⌛ WAIT"
            else:
                m['Suggestie'] = "💎 ACCUMULATE" if m['RSI'] < 45 else "🛡️ HOLD"
            results.append(m)
    
    df = pd.DataFrame(results)
    
    # Styling functie
    def style_scanner(row):
        styles = [''] * len(row)
        # Check of ticker in bezit is (1e kolom)
        if row['Ticker'] in owned_tickers:
            styles[0] = 'background-color: #f39c12; color: white; font-weight: bold' # Oranje voor 'In bezit'
        
        # Kleur voor Suggestie (laatste kolom)
        val = row['Suggestie']
        sug_color = '#27ae60' if 'BUY' in val or 'ACCUMULATE' in val else '#e74c3c' if 'SELL' in val else '#3498db' if 'MOMENTUM' in val else '#7f8c8d'
        styles[-1] = f'background-color: {sug_color}; color: white; font-weight: bold'
        
        return styles

    st.dataframe(df.style.apply(style_scanner, axis=1), use_container_width=True, hide_index=True)
