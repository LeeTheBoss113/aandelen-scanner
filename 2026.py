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
        p12 = ((cur-hist['Close'].iloc[0])/hist['Close'].iloc[0])*100
        trend = "📈 Bullish" if p6 > 5 else "📉 Bearish" if p6 < -5 else "➡️ Side"
        return {"Ticker": ticker, "Trend": trend, "Prijs": round(cur, 2), "RSI": round(rsi, 1), "6M %": round(p6, 1), "12M %": round(p12, 1)}
    except: return None

# --- UI COMPONENTEN ---
def show_scanner(watchlist, mode, df_portfolio):
    results = []
    owned_tickers = df_portfolio['Ticker'].str.upper().tolist() if not df_portfolio.empty and 'Ticker' in df_portfolio.columns else []
    for t in watchlist:
        m = get_scan_metrics(t)
        if m:
            rsi, p12 = m['RSI'], m['12M %']
            if mode == "Growth":
                if rsi < 35: m['Suggestie'] = "🔥 BUY DIP"
                elif rsi > 75: m['Suggestie'] = "💰 TAKE PROFIT"
                elif rsi > 70 and p12 > 40: m['Suggestie'] = "⚠️ PEAK ALERT"
                elif m['6M %'] > 15: m['Suggestie'] = "🚀 MOMENTUM"
                else: m['Suggestie'] = "⌛ WAIT"
            else:
                if rsi < 45: m['Suggestie'] = "💎 ACCUMULATE"
                elif rsi > 68: m['Suggestie'] = "🛡️ HOLD/REDUCE"
                else: m['Suggestie'] = "✅ STABLE"
            results.append(m)
    if results:
        df = pd.DataFrame(results)
        def style_scanner(row):
            styles = [''] * len(row)
            if row['Ticker'] in owned_tickers: styles[0] = 'background-color: #f39c12; color: white; font-weight: bold'
            val = row['Suggestie']
            sug_c = '#27ae60' if 'BUY' in val or 'ACCUMULATE' in val else '#e67e22' if 'PROFIT' in val or 'PEAK' in val else '#3498db' if 'MOMENTUM' in val else '#7f8c8d'
            styles[-1] = f'background-color: {sug_c}; color: white; font-weight: bold'
            return styles
        st.dataframe(df.style.apply(style_scanner, axis=1), use_container_width=True, hide_index=True)

def render_portfolio_compact(df, strategy_name):
    subset = df[df['Type'] == strategy_name] if not df.empty and 'Type' in df.columns else pd.DataFrame()
    if subset.empty:
        st.info(f"Geen {strategy_name} posities.")
        return
    for _, row in subset.iterrows():
        ticker = str(row['Ticker']).upper()
        try:
            p = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
            winst = ((row['Inleg']/row['Koers']) * p) - row['Inleg']
            with st.expander(f"**{ticker}** | Winst: **€{winst:.2f}**"):
                c1, c2, c3 = st.columns([1,1,0.5])
                c1.write(f"Inleg: €{row['Inleg']:.0f}")
                c2.write(f"Res: {((winst/row['Inleg'])*100):.1f}%")
                if c3.button("🗑️", key=f"del_{row['airtable_id']}"):
                    if sell_position(row, p): st.rerun()
        except: pass

# --- MAIN DASHBOARD ---
df_p = get_airtable_data(PORTFOLIO_TABLE)
df_l = get_airtable_data(LOG_TABLE)

GROWTH_WATCH = ['NVDA', 'TSLA', 'PLTR', 'AMD', 'ASML.AS', 'ADYEN.AS', 'COIN', 'MSTR', 'META', 'AMZN', 'GOOGL', 'NFLX', 'SHOP', 'SNOW', 'ARM']
DIVIDEND_WATCH = ['KO', 'PEP', 'PG', 'O', 'ABBV', 'JNJ', 'MMM', 'LOW', 'TGT', 'MO', 'T', 'CVX', 'XOM', 'SCHD', 'VICI']

with st.sidebar:
    st.title("📊 My Assistant")
    with st.expander("ℹ️ Spiekbriefje", expanded=True):
        st.write("**💰 Take Profit:** RSI >75. Verkoop-zone.")
        st.write("**⚠️ Peak Alert:** RSI >70 & Jaar-top.")
        st.write("**🔥 Buy Dip:** RSI < 35. Koop-zone.")
        st.write("**Oranje Ticker:** Reeds in bezit.")
    st.divider()
    # Berekening lopende winst
    gw, dw = 0, 0
    if not df_p.empty:
        for _, r in df_p.iterrows():
            try:
                cur_p = yf.Ticker(r['Ticker']).history(period="1d")['Close'].iloc[-1]
                w = ((r['Inleg']/r['Koers']) * cur_p) - r['Inleg']
                if r['Type'] == "Growth": gw += w
                else: dw += w
            except: pass
    st.metric("🚀 Lopende Winst Growth", f"€{gw:.2f}")
    st.metric("💎 Lopende Winst Dividend", f"€{dw:.2f}")
    st.divider()
    with st.form("add_new"):
        st.subheader("➕ Nieuwe Positie")
        t_in = st.text_input("Ticker").upper()
        i_in = st.number_input("Inleg", 10)
        k_in = st.number_input("Koers", 0.01)
        s_in = st.selectbox("Type", ["Growth", "Dividend"])
        if st.form_submit_button("Toevoegen"):
            requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{PORTFOLIO_TABLE}", headers=HEADERS, json={"fields": {"Ticker": t_in, "Inleg": i_in, "Koers": k_in, "Type": s_in}})
            st.rerun()

tab1, tab2, tab3 = st.tabs(["🚀 Growth Strategy", "💎 Dividend Wealth", "📜 Logboek"])

with tab1:
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Portefeuille")
        render_portfolio_compact(df_p, "Growth")
    with c2:
        st.subheader("Market Scanner")
        show_scanner(GROWTH_WATCH, "Growth", df_p)

with tab2:
    c1b, c2b = st.columns([1, 2])
    with c1b:
        st.subheader("Portefeuille")
        render_portfolio_compact(df_p, "Dividend")
    with c2b:
        st.subheader("Aristocrats Scanner")
        show_scanner(DIVIDEND_WATCH, "Dividend", df_p)

with tab3:
    st.header("📜 Historisch Overzicht")
    if not df_l.empty:
        # Data preparatie
        df_l['Datum'] = pd.to_datetime(df_l['Datum'])
        total_profit = df_l['Winst_Euro'].sum()
        avg_ret = df_l['Rendement_Perc'].mean()
        win_rate = (len(df_l[df_l['Winst_Euro'] > 0]) / len(df_l)) * 100
        
        # Dashboard Metrics
        c_p1, c_p2, c_p3 = st.columns(3)
        c_p1.metric("💰 Totaal Gerealiseerd", f"€{total_profit:.2f}", delta=f"{len(df_l)} trades")
        c_p2.metric("📈 Gem. Rendement", f"{avg_ret:.2f}%")
        c_p3.metric("🎯 Win Rate", f"{win_rate:.1f}%")
        
        st.divider()
        
        # Winstverloop Grafiek
        st.subheader("Winstverloop per dag")
        chart_data = df_l.groupby('Datum')['Winst_Euro'].sum().reset_index()
        st.bar_chart(data=chart_data, x='Datum', y='Winst_Euro', use_container_width=True)
        
        st.divider()
        st.dataframe(df_l.sort_values(by='Datum', ascending=False), use_container_width=True, hide_index=True)
        
        st.divider()
        if st.checkbox("Systeembeheer: Wis Logboek"):
            if st.button("Definitief Verwijderen"):
                for rid in df_l['airtable_id']: requests.delete(f"https://api.airtable.com/v0/{BASE_ID}/{LOG_TABLE}/{rid}", headers=HEADERS)
                st.rerun()
    else:
        st.info("Het logboek is nog leeg. Zodra je posities verkoopt, zie je hier de resultaten.")