import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json

# 1. Instellingen & Functies (ALTIJD BOVENAAN)
st.set_page_config(layout="wide", page_title="Daytrade Pro 2026")

API_URL = "https://script.google.com/macros/s/AKfycbxlP2U3_PsLajE1cjn3ZC4G4d7S9hNcSya1bwR_Jk3WFBoRdPpmKFJrtv_Rhb5As54N/exec"

def color_status(v):
    colors = {
        'BUY': 'background-color: #008000; color: white;', 
        'SELL': 'background-color: #FF0000; color: white;', 
        'WAIT': 'background-color: #FFA500; color: black;', 
        'ACCUMULATE': 'background-color: #90EE90; color: black;', 
        'BEARISH': 'background-color: #8B0000; color: white;'
    }
    return colors.get(v, '')

def load_gsheets():
    try:
        r = requests.get(API_URL, timeout=10)
        data = r.json()
        if len(data) < 2: return pd.DataFrame(columns=["T", "I", "P"])
        df = pd.DataFrame(data[1:], columns=["T", "I", "P"])
        df[['I', 'P']] = df[['I', 'P']].apply(pd.to_numeric, errors='coerce')
        return df.dropna(subset=['T'])
    except:
        return pd.DataFrame(columns=["T", "I", "P"])

@st.cache_data(ttl=300)
def get_market_data(tickers):
    db = {}
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            h = tk.history(period="2y")
            if h.empty: continue
            cp = h['Close'].iloc[-1]
            rsi = ta.rsi(h['Close'], 14).iloc[-1]
            ma200 = h['Close'].tail(200).mean()
            # Trend data
            p_6m = h['Close'].iloc[-126] if len(h) > 126 else h['Close'].iloc[0]
            p_1y = h['Close'].iloc[-252] if len(h) > 252 else h['Close'].iloc[0]
            
            status = "WAIT"
            if rsi < 35: status = "BUY"
            elif rsi > 65: status = "SELL"
            elif cp > ma200 and rsi < 45: status = "ACCUMULATE"
            
            db[t] = {"p": cp, "rsi": rsi, "s": status, "6m": ((cp-p_6m)/p_6m)*100, "1y": ((cp-p_1y)/p_1y)*100}
        except: continue
    return db

# 2. Data Initialiseren
st.title("⚡ Daytrade Stability Pro")
df_pf = load_gsheets()

# 3. Tabs aanmaken (CRUCIAAL: Hier worden t1, t2, t3 gedefinieerd)
t1, t2, t3 = st.tabs(["📊 Portfolio & Beheer", "🔍 Daytrade Scanner", "📈 Trend Monitor"])

# --- TAB 1: PORTFOLIO ---
with t1:
    col_l, col_r = st.columns([1, 2])
    with col_l:
        st.subheader("Trade Toevoegen")
        with st.form("trade_form", clear_on_submit=True):
            ticker = st.text_input("Ticker (bv. NVDA)").upper().strip()
            inleg = st.number_input("Inleg (€)", value=500.0)
            koers = st.number_input("Aankoopkoers", min_value=0.0)
            if st.form_submit_button("Sla Trade Op"):
                if ticker and koers > 0:
                    requests.post(API_URL, data=json.dumps({"ticker":ticker, "inleg":inleg, "koers":koers}))
                    st.success("Verzonden!")
                    st.rerun()

    with col_r:
        st.subheader("Huidige Posities")
        if not df_pf.empty:
            m_data = get_market_data(df_pf['T'].tolist())
            rows = []
            total_profit = 0
            for _, row in df_pf.iterrows():
                t = row['T']
                if t in m_data:
                    cur = m_data[t]
                    winst = (float(row['I']) / float(row['P']) * cur['p']) - float(row['I'])
                    total_profit += winst
                    rows.append({"Ticker": t, "Winst": round(winst, 2), "Nu": round(cur['p'], 2), "Status": cur['s']})
            
            st.metric("Totaal Resultaat", f"€ {total_profit:.2f}")
            if rows:
                st.dataframe(pd.DataFrame(rows).style.map(color_status, subset=['Status']), hide_index=True)
            
            with st.expander("Verwijderen"):
                for t in df_pf['T'].unique():
                    if st.button(f"🗑️ {t}", key=f"del_{t}"):
                        requests.post(API_URL, data=json.dumps({"method":"delete", "ticker":t}))
                        st.rerun()

# --- TAB 2: SCANNER ---
with t2:
    st.subheader("Top 25 Daytrade Scanner")
    top_25 = ['NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN', 'META', 'AMD', 'NFLX', 'GOOGL', 'ASML.AS', 'INGA.AS', 'SHELL.AS', 'ADYEN.AS', 'JPM', 'BABA', 'PLTR', 'COIN', 'NIO', 'SQ', 'PYPL', 'DIS']
    market_db = get_market_data(top_25)
    scan_rows = [{"Ticker": t, "Prijs": d['p'], "RSI": round(d['rsi'],1), "Actie": d['s']} for t, d in market_db.items()]
    if scan_rows:
        st.dataframe(pd.DataFrame(scan_rows).sort_values(by="RSI").style.map(color_status, subset=['Actie']), use_container_width=True, hide_index=True)

# --- TAB 3: TREND ---
with t3:
    st.subheader("Trend Analyse")
    trend_rows = [{"Ticker": t, "6M %": round(d['6m'],1), "1Y %": round(d['1y'],1)} for t, d in market_db.items()]
    if trend_rows:
        st.table(pd.DataFrame(trend_rows).sort_values(by="6M %", ascending=False))