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

st.set_page_config(layout="wide", page_title="Profit Scanner 2026", initial_sidebar_state="expanded")

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
                # Alleen toevoegen als er een Ticker is ingevuld om AttributeError te voorkomen
                if row.get('Ticker'):
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
        hist = t.history(period="6mo")
        if len(hist) < 10: return None
        cur = hist['Close'].iloc[-1]
        rsi = ta.rsi(hist['Close'], length=14).iloc[-1]
        vol_boost = (hist['Volume'].iloc[-1] / hist['Volume'].mean()) 
        day_perc = ((hist['Close'].iloc[-1] - hist['Open'].iloc[-1]) / hist['Open'].iloc[-1]) * 100
        return {"Ticker": ticker, "Prijs": round(cur, 2), "RSI": round(rsi, 1), "Vol_Boost": round(vol_boost, 2), "Day_%": round(day_perc, 2)}
    except: return None

# --- APP START ---
df_p = get_airtable_data(PORTFOLIO_TABLE)
df_l = get_airtable_data(LOG_TABLE)

with st.sidebar:
    st.title("📊 My Assistant")
    # Testduur berekenen
    if not df_l.empty and 'Datum' in df_l.columns:
        df_l['Datum'] = pd.to_datetime(df_l['Datum'])
        start_date = df_l['Datum'].min()
        duur = (datetime.now() - start_date).days
        st.info(f"⏱️ Testduur: **{duur} dagen**")

    st.divider()
    with st.form("add_new"):
        st.subheader("➕ Nieuwe Positie")
        t_in = st.text_input("Ticker (bijv. NVDA)").upper()
        i_in = st.number_input("Inleg", 10)
        k_in = st.number_input("Koers", 0.01)
        s_in = st.selectbox("Type", ["Growth", "Dividend"])
        if st.form_submit_button("Toevoegen"):
            if t_in:
                requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{PORTFOLIO_TABLE}", headers=HEADERS, json={"fields": {"Ticker": t_in, "Inleg": i_in, "Koers": k_in, "Type": s_in}})
                st.rerun()

tab1, tab2 = st.tabs(["🚀 Markt Scanner & Portfolio", "📜 Logboek (Maandwinst)"])

with tab1:
    c1, c2 = st.columns([1.2, 1])
    
    with c1:
        st.subheader("🔥 Dynamische Scanner")
        watchlist = ['NVDA', 'TSLA', 'PLTR', 'AAPL', 'AMD', 'COIN', 'MSTR', 'META', 'AMZN', 'GOOGL', 'ASML.AS']
        scan_results = []
        for t in watchlist:
            m = get_scan_metrics(t)
            if m: scan_results.append(m)
        
        if scan_results:
            sdf = pd.DataFrame(scan_results).sort_values(by="Day_%", ascending=False)
            st.dataframe(sdf, use_container_width=True, hide_index=True)

    with c2:
        st.subheader("💼 Mijn Portfolio")
        if not df_p.empty:
            for _, row in df_p.iterrows():
                ticker = str(row['Ticker']).upper()
                try:
                    p_live = yf.Ticker(ticker).history(period="1d")['Close'].iloc[-1]
                    win_p = ((p_live - row['Koers']) / row['Koers']) * 100
                    win_e = ((row['Inleg']/row['Koers']) * p_live) - row['Inleg']
                    
                    # SALAMI STRATEGIE KLEUREN
                    color = "#ffffff" # wit
                    status = ""
                    if win_p >= 15: 
                        color = "#f1c40f" # goud
                        status = "🎯 TARGET!"
                    elif -2 < win_p < 2:
                        color = "#bdc3c7" # grijs (stagnatie)
                        status = "💤"

                    with st.expander(f"{status} **{ticker}**: {win_p:.1f}%"):
                        st.markdown(f"Huidige winst: <span style='color:{color}; font-weight:bold;'>€{win_e:.2f}</span>", unsafe_allow_html=True)
                        if st.button(f"Verkoop {ticker}", key=f"sell_{row['airtable_id']}"):
                            if sell_position(row, p_live): st.rerun()
                except: st.warning(f"Kon {ticker} niet laden.")
        else:
            st.info("Geen actieve posities.")

with tab2:
    st.header("Maandelijks Resultaat")
    if not df_l.empty:
        df_l['Datum'] = pd.to_datetime(df_l['Datum'])
        df_l['Maand'] = df_l['Datum'].dt.to_period('M').astype(str)
        
        # Metrics
        total = df_l['Winst_Euro'].sum()
        avg_month = df_l.groupby('Maand')['Winst_Euro'].sum().mean()
        
        col1, col2 = st.columns(2)
        col1.metric("Totaal Winst", f"€{total:.2f}")
        col2.metric("Gem. per Maand", f"€{avg_month:.2f}")

        # Maandelijkse grafiek
        maand_data = df_l.groupby('Maand')['Winst_Euro'].sum().reset_index()
        st.bar_chart(data=maand_data, x='Maand', y='Winst_Euro')
        
        st.divider()
        st.dataframe(df_l.sort_values(by='Datum', ascending=False), use_container_width=True)
    else:
        st.info("Nog geen verkopen geregistreerd.")