import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
from datetime import datetime

# --- CONFIG ---
AIRTABLE_TOKEN = "patCdgzOgVDPNlGCw.3008de99d994972e122dc62031b3f5aa5f2647cfa75c5ac67215dc72eba2ce07"
BASE_ID = "appgvzDsvbvKi7e45"
PORTFOLIO_TABLE = "Portfolio"
LOG_TABLE = "Logboek"

HEADERS = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}

st.set_page_config(layout="wide", page_title="Trader Dashboard 2026", initial_sidebar_state="expanded")

# --- CUSTOM CSS VOOR DIRECTE ALERTS ---
st.markdown("""
    <style>
    .portfolio-card {
        background-color: #1e1e1e;
        border: 1px solid #333;
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    .sell-alert {
        background-color: #f1c40f;
        color: black;
        font-weight: bold;
        text-align: center;
        padding: 5px;
        border-radius: 5px;
        margin-bottom: 10px;
        animation: pulse 2s infinite;
    }
    @keyframes pulse {
        0% { opacity: 1; }
        50% { opacity: 0.7; }
        100% { opacity: 1; }
    }
    .profit-pos { color: #2ecc71; font-size: 1.2rem; font-weight: bold; }
    .profit-neg { color: #e74c3c; font-size: 1.2rem; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA FUNCTIES ---
def get_airtable_data(table_name):
    try:
        url = f"https://api.airtable.com/v0/{BASE_ID}/{table_name}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            records = r.json().get('records', [])
            return pd.DataFrame([ {**rec['fields'], 'airtable_id': rec['id']} for rec in records if rec['fields'].get('Ticker') ])
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
            "Type": "Growth",
            "Datum": datetime.now().strftime('%Y-%m-%d')
        }
    }
    res = requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{LOG_TABLE}", headers=HEADERS, json=log_payload)
    if res.status_code == 200:
        requests.delete(f"https://api.airtable.com/v0/{BASE_ID}/{PORTFOLIO_TABLE}/{row['airtable_id']}", headers=HEADERS)
        return True
    return False

@st.cache_data(ttl=300)
def get_combo_metrics(ticker):
    try:
        t = yf.Ticker(ticker)
        hist = t.history(period="14mo")
        if len(hist) < 252: return None
        cur = hist['Close'].iloc[-1]
        m6, m12 = hist['Close'].iloc[-126], hist['Close'].iloc[-252]
        rsi = ta.rsi(hist['Close'], length=14).iloc[-1]
        p6, p12 = ((cur-m6)/m6)*100, ((cur-m12)/m12)*100
        advies, score = "⌛ WAIT", 0
        if p12 > 0 and p6 > 10:
            if rsi < 40: advies, score = "🔥 STRONG BUY", 3
            elif rsi < 50: advies, score = "✅ ACCUMULATE", 2
        elif rsi > 75: advies, score = "💰 TAKE PROFIT", -1
        return {"Ticker": ticker, "Prijs": round(cur, 2), "RSI": round(rsi, 1), "6M %": round(p6, 1), "12M %": round(p12, 1), "Advies": advies, "Score": score}
    except: return None

# --- UI START ---
df_p = get_airtable_data(PORTFOLIO_TABLE)
df_l = get_airtable_data(LOG_TABLE)

with st.sidebar:
    st.title("📊 My Assistant")
    if not df_l.empty:
        df_l['Datum'] = pd.to_datetime(df_l['Datum'])
        st.info(f"⏱️ Testduur: **{(datetime.now() - df_l['Datum'].min()).days} dagen**")
    
    with st.form("add_new"):
        t_in = st.text_input("Ticker").upper()
        i_in = st.number_input("Inleg (€)", 10)
        k_in = st.number_input("Aankoopkoers", 0.01)
        if st.form_submit_button("Toevoegen"):
            requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{PORTFOLIO_TABLE}", headers=HEADERS, json={"fields": {"Ticker": t_in, "Inleg": i_in, "Koers": k_in, "Type": "Growth"}})
            st.rerun()

tab1, tab2 = st.tabs(["📈 Dashboard", "📜 Logboek"])

with tab1:
    col_port, col_scan = st.columns([1, 1.3])

    with col_port:
        st.subheader("💼 Portfolio & Alerts")
        if not df_p.empty:
            for _, row in df_p.iterrows():
                ticker = str(row['Ticker']).upper()
                try:
                    p_live = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
                    win_p = ((p_live - row['Koers']) / row['Koers']) * 100
                    win_e = ((row['Inleg']/row['Koers']) * p_live) - row['Inleg']
                    
                    # CARD DESIGN
                    st.markdown(f"""
                    <div class="portfolio-card">
                        <div style="display: flex; justify-content: space-between;">
                            <span style="font-size: 1.5rem; font-weight: bold;">{ticker}</span>
                            <span class="{'profit-pos' if win_e >= 0 else 'profit-neg'}">{win_p:.1f}% (€{win_e:.2f})</span>
                        </div>
                        <p style="color: #888; margin-top: 5px;">Inleg: €{row['Inleg']} | Koers: {row['Koers']:.2f} → {p_live:.2f}</p>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # DIRECTE ALERT BIJ 15%
                    if win_p >= 15:
                        st.markdown('<div class="sell-alert">⚠️ SALAMI TIJD! PAK JE 15% WINST ⚠️</div>', unsafe_allow_html=True)
                        if st.button(f"💰 VERKOOP {ticker} NU", key=f"s_{row['airtable_id']}", use_container_width=True):
                            if sell_position(row, p_live): st.rerun()
                    st.divider()
                except: pass
        else: st.info("Geen actieve posities.")

    with col_scan:
        st.subheader("🔍 Koop-Kansen (Trend + RSI)")
        watchlist = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMD', 'PLTR', 'COIN', 'MSTR', 'META', 'AMZN', 'GOOGL', 'ASML.AS']
        res = [get_combo_metrics(t) for t in watchlist]
        sdf = pd.DataFrame([r for r in res if r]).sort_values(by="Score", ascending=False)
        
        def style_scan(row):
            styles = [''] * len(row)
            if "STRONG BUY" in row['Advies']: styles[5] = 'background-color: #27ae60; color: white; font-weight: bold'
            if row['6M %'] > 0: styles[3] = 'color: #2ecc71'
            if row['12M %'] > 0: styles[4] = 'color: #2ecc71'
            return styles

        st.dataframe(sdf.style.apply(style_scan, axis=1), use_container_width=True, hide_index=True)

with tab2:
    st.header("Maandelijks Resultaat")
    if not df_l.empty:
        df_l['Datum'] = pd.to_datetime(df_l['Datum'])
        df_l['Maand'] = df_l['Datum'].dt.to_period('M').astype(str)
        m_data = df_l.groupby('Maand')['Winst_Euro'].sum().reset_index()
        
        c1, c2 = st.columns(2)
        c1.metric("Totaal Winst", f"€{df_l['Winst_Euro'].sum():.2f}")
        c2.metric("Laatste Maand", f"€{m_data['Winst_Euro'].iloc[-1]:.2f}")
        
        st.bar_chart(data=m_data, x='Maand', y='Winst_Euro')
        st.dataframe(df_l.sort_values(by='Datum', ascending=False), use_container_width=True, hide_index=True)