import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import time

# --- CONFIG ---
AIRTABLE_TOKEN = "patCdgzOgVDPNlGCw.3008de99d994972e122dc62031b3f5aa5f2647cfa75c5ac67215dc72eba2ce07"
BASE_ID = "appgvzDsvbvKi7e45"
TABLE_NAME = "Portfolio"

WATCHLIST_GROWTH = ['NVDA', 'TSLA', 'PLTR', 'AMD', 'COIN', 'ASML.AS']
WATCHLIST_DIVIDEND = ['KO', 'PEP', 'O', 'ABBV', 'JNJ', 'INGA.AS']

URL = f"https://api.airtable.com/v0/{BASE_ID}/{TABLE_NAME}"
HEADERS = {"Authorization": f"Bearer {AIRTABLE_TOKEN}"}

st.set_page_config(layout="wide", page_title="Portfolio & Market Scanner")

# --- STYLING HELPERS ---
def style_pnl(val):
    if isinstance(val, (int, float)):
        color = '#27ae60' if val >= 0 else '#e74c3c'
        return f'color: {color}; font-weight: bold'
    return ''

# --- DATA FUNCTIES ---
@st.cache_data(ttl=600)
def get_live_data(ticker):
    try:
        t = yf.Ticker(ticker)
        df = t.history(period="1y")
        if df.empty: return None
        return {
            "price": df['Close'].iloc[-1],
            "rsi": ta.rsi(df['Close'], length=14).iloc[-1],
            "6m": ((df['Close'].iloc[-1] - df['Close'].iloc[-126]) / df['Close'].iloc[-126] * 100) if len(df) > 126 else 0
        }
    except: return None

def get_airtable_portfolio():
    try:
        r = requests.get(URL, headers=HEADERS).json()
        records = r.get('records', [])
        if not records: return pd.DataFrame()
        rows = []
        for r in records:
            row = r['fields']
            row['id'] = r['id']
            rows.append(row)
        return pd.DataFrame(rows)
    except: return pd.DataFrame()

# --- MAIN APP ---
st.title("📈 Mijn Vermogen & Market Scanner")

# 1. Haal Portfolio op
df_portfolio = get_airtable_portfolio()

# --- SECTIE 1: PORTFOLIO PERFORMANCE ---
st.subheader("💰 Mijn Open Posities")
if not df_portfolio.empty:
    portfolio_results = []
    totale_inleg = 0
    huidige_waarde_totaal = 0

    for _, row in df_portfolio.iterrows():
        live = get_live_data(row['Ticker'])
        if live:
            inleg = row['Inleg']
            aankoop = row['Koers']
            huidig = live['price']
            
            # Berekeningen
            aantal = inleg / aankoop if aankoop > 0 else 0
            waarde = aantal * huidig
            winst_eur = waarde - inleg
            winst_perc = (winst_eur / inleg * 100) if inleg > 0 else 0
            
            totale_inleg += inleg
            huidige_waarde_totaal += waarde
            
            portfolio_results.append({
                "Ticker": row['Ticker'],
                "Inleg": inleg,
                "Huidige Prijs": round(huidig, 2),
                "Waarde": round(waarde, 2),
                "Winst/Verlies €": round(winst_eur, 2),
                "Rendement %": round(winst_perc, 2),
                "RSI": round(live['rsi'], 1),
                "Type": row.get('Type', 'Onbekend')
            })

    # Metrics bovenaan
    m1, m2, m3 = st.columns(3)
    m1.metric("Totale Inleg", f"€{totale_inleg:,.2f}")
    m2.metric("Huidige Waarde", f"€{huidige_waarde_totaal:,.2f}", f"{((huidige_waarde_totaal-totale_inleg)/totale_inleg*100):.2f}%" if totale_inleg > 0 else "0%")
    m3.metric("Netto Resultaat", f"€{(huidige_waarde_totaal - totale_inleg):,.2f}")

    # Toon Portfolio Tabel
    df_p = pd.DataFrame(portfolio_results)
    st.dataframe(
        df_p.style.applymap(style_pnl, subset=['Winst/Verlies €', 'Rendement %']),
        use_container_width=True, hide_index=True
    )
else:
    st.info("Nog geen aandelen in je portfolio. Voeg ze toe via de scanner hieronder.")

# --- SECTIE 2: MARKET EXPLORER ---
st.divider()
tab1, tab2 = st.tabs(["🚀 Growth Explorer", "💎 Dividend Watcher"])

def render_explorer(watchlist, strategy):
    results = []
    for ticker in watchlist:
        info = get_live_data(ticker)
        if info:
            in_bezit = '✅' if not df_portfolio.empty and ticker in df_portfolio['Ticker'].values else '⚪'
            results.append({
                "Ticker": f"{in_bezit} {ticker}",
                "Prijs": round(info['price'], 2),
                "RSI": round(info['rsi'], 1),
                "6M Trend": f"{info['6m']:.1f}%",
                "Status": "KOOP KANS" if (strategy == "Growth" and info['rsi'] < 35) or (strategy == "Dividend" and info['rsi'] < 45) else "HOLD"
            })
    st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

with tab1: render_explorer(WATCHLIST_GROWTH, "Growth")
with tab2: render_explorer(WATCHLIST_DIVIDEND, "Dividend")

# --- TOEVOEGEN ---
with st.sidebar:
    st.header("➕ Nieuwe Aankoop")
    with st.form("add"):
        t = st.text_input("Ticker").upper()
        i = st.number_input("Inleg (€)", 100)
        k = st.number_input("Koers", 0.0)
        s = st.selectbox("Type", ["Growth", "Dividend"])
        if st.form_submit_button("Toevoegen"):
            requests.post(URL, headers=HEADERS, json={"fields": {"Ticker": t, "Inleg": i, "Koers": k, "Type": s}})
            st.rerun()