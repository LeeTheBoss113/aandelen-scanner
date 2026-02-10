import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
from datetime import datetime

# Instellingen
st.set_page_config(layout="wide", page_title="Daytrade Pro Dashboard")
API_URL = "https://script.google.com/macros/s/AKfycbxlP2U3_PsLajE1cjn3ZC4G4d7S9hNcSya1bwR_Jk3WFBoRdPpmKFJrtv_Rhb5As54N/exec"

# --- DATA FUNCTIES ---
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

@st.cache_data(ttl=300) # 5 minuten cache voor daytrading
def get_market_data(tickers):
    db = {}
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            h = tk.history(period="2y") # 2 jaar nodig voor 1j trend & MA200
            if h.empty: continue
            
            cp = h['Close'].iloc[-1]
            rsi = ta.rsi(h['Close'], 14).iloc[-1]
            ma200 = h['Close'].tail(200).mean()
            
            # Trend monitoring
            p_6m = h['Close'].iloc[-126] if len(h) > 126 else h['Close'].iloc[0]
            p_1y = h['Close'].iloc[-252] if len(h) > 252 else h['Close'].iloc[0]
            
            perf_6m = ((cp - p_6m) / p_6m) * 100
            perf_1y = ((cp - p_1y) / p_1y) * 100
            
            # Daytrade Logica
            status = "WAIT"
            if rsi < 30: status = "BUY"
            elif rsi > 70: status = "SELL"
            elif cp > ma200 and rsi < 45: status = "ACCUMULATE"
            elif cp < ma200: status = "BEARISH"
            
            db[t] = {"p": cp, "rsi": rsi, "s": status, "6m": perf_6m, "1y": perf_1y}
        except: continue
    return db

# --- START APP ---
st.title("⚡ Daytrade Stability Pro")
df_pf = load_gsheets()

# Tabs voor overzicht
t1, t2, t3 = st.tabs(["📊 Portfolio & Beheer", "🔍 Daytrade Scanner", "📈 Trend Monitor"])

# --- TAB 1: PORTFOLIO & BEHEER ---
with t1:
    col_l, col_r = st.columns([1, 2])
    
    with col_l:
        st.subheader("Trade Toevoegen")
        with st.form("trade_form", clear_on_submit=True):
            ticker = st.text_input("Ticker").upper().strip()
            inleg = st.number_input("Inleg (€)", value=500.0)
            koers = st.number_input("Aankoopkoers", min_value=0.0)
            if st.form_submit_button("Sla Trade Op"):
                if ticker and koers > 0:
                    requests.post(API_URL, data=json.dumps({"ticker":ticker, "inleg":inleg, "koers":koers}))
                    st.success(f"{ticker} opgeslagen!")
                    st.rerun()

    with col_r:
        st.subheader("Huidige Posities")
        if not df_pf.empty:
            tickers_pf = df_pf['T'].tolist()
            data_pf = get_market_data(tickers_pf)
            
            rows = []
            total_profit = 0
            for _, row in df_pf.iterrows():
                t = row['T']
                if t in data_pf:
                    cur = data_pf[t]
                    winst = ((inv := float(row['I'])) / (buy := float(row['P'])) * cur['p']) - inv
                    total_profit += winst
                    rows.append({
                        "Ticker": t, "Inleg": inv, "Koers": buy, 
                        "Nu": round(cur['p'], 2), "Winst": round(winst, 2), "Status": cur['s']
                    })
            
            res_df = pd.DataFrame(rows)
            st.metric("Totaal Saldo Winst/Verlies", f"€ {total_profit:.2f}")
            
            def color_status(v):
                colors = {'BUY': 'background-color: green', 'SELL': 'background-color: red', 
                          'WAIT': 'background-color: orange', 'ACCUMULATE': 'background-color: lightgreen'}
                return colors.get(v, '')

            st.dataframe(res_df.style.applymap(color_status, subset=['Status']), hide_index=True, use_container_width=True)
            
            # Verwijderen sectie
            with st.expander("Trades Sluiten / Verwijderen"):
                for t in tickers_pf:
                    if st.button(f"Sluit {t} Trade", key=f"del_{t}"):
                        requests.post(API_URL, data=json.dumps({"method":"delete", "ticker":t}))
                        st.rerun()
        else:
            st.info("Geen actieve trades.")

# --- TAB 2: DAYTRADE SCANNER (TOP 25) ---
with t2:
    st.subheader("Top 25 Liquide Aandelen (RSI Focus)")
    top_25 = [
        'NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN', 'META', 'AMD', 'NFLX', 'GOOGL', 'ASML.AS',
        'INGA.AS', 'SHELL.AS', 'ADYEN.AS', 'JPM', 'V', 'MA', 'BABA', 'PLTR', 'COIN', 'NIO',
        'MARA', 'RIOT', 'SQ', 'PYPL', 'DIS'
    ]
    market_db = get_market_data(top_25)
    
    scan_rows = []
    for t in top_25:
        if t in market_db:
            m = market_db[t]
            scan_rows.append({"Ticker": t, "Prijs": m['p'], "RSI (14)": round(m['rsi'],1), "Actie": m['s']})
    
    scan_df = pd.DataFrame(scan_rows).sort_values(by="RSI (14)")
    st.dataframe(scan_df.style.applymap(color_status, subset=['Actie']), use_container_width=True, hide_index=True)

# --- TAB 3: TREND MONITOR ---
with t3:
    st.subheader("Trend Analyse (6 Maanden vs 1 Jaar)")
    trend_rows = []
    for t in top_25:
        if t in market_db:
            m = market_db[t]
            trend_rows.append({
                "Ticker": t, "Nu": round(m['p'],2), 
                "6 Maanden %": round(m['6m'], 1), "1 Jaar %": round(m['1y'], 1)
            })
    
    st.table(pd.DataFrame(trend_rows).sort_values(by="6 Maanden %", ascending=False))import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
from datetime import datetime

# Instellingen
st.set_page_config(layout="wide", page_title="Daytrade Pro Dashboard")
API_URL = "https://script.google.com/macros/s/AKfycbxlP2U3_PsLajE1cjn3ZC4G4d7S9hNcSya1bwR_Jk3WFBoRdPpmKFJrtv_Rhb5As54N/exec"

# --- DATA FUNCTIES ---
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

@st.cache_data(ttl=300) # 5 minuten cache voor daytrading
def get_market_data(tickers):
    db = {}
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            h = tk.history(period="2y") # 2 jaar nodig voor 1j trend & MA200
            if h.empty: continue
            
            cp = h['Close'].iloc[-1]
            rsi = ta.rsi(h['Close'], 14).iloc[-1]
            ma200 = h['Close'].tail(200).mean()
            
            # Trend monitoring
            p_6m = h['Close'].iloc[-126] if len(h) > 126 else h['Close'].iloc[0]
            p_1y = h['Close'].iloc[-252] if len(h) > 252 else h['Close'].iloc[0]
            
            perf_6m = ((cp - p_6m) / p_6m) * 100
            perf_1y = ((cp - p_1y) / p_1y) * 100
            
            # Daytrade Logica
            status = "WAIT"
            if rsi < 30: status = "BUY"
            elif rsi > 70: status = "SELL"
            elif cp > ma200 and rsi < 45: status = "ACCUMULATE"
            elif cp < ma200: status = "BEARISH"
            
            db[t] = {"p": cp, "rsi": rsi, "s": status, "6m": perf_6m, "1y": perf_1y}
        except: continue
    return db

# --- START APP ---
st.title("⚡ Daytrade Stability Pro")
df_pf = load_gsheets()

# Tabs voor overzicht
t1, t2, t3 = st.tabs(["📊 Portfolio & Beheer", "🔍 Daytrade Scanner", "📈 Trend Monitor"])

# --- TAB 1: PORTFOLIO & BEHEER ---
with t1:
    col_l, col_r = st.columns([1, 2])
    
    with col_l:
        st.subheader("Trade Toevoegen")
        with st.form("trade_form", clear_on_submit=True):
            ticker = st.text_input("Ticker").upper().strip()
            inleg = st.number_input("Inleg (€)", value=500.0)
            koers = st.number_input("Aankoopkoers", min_value=0.0)
            if st.form_submit_button("Sla Trade Op"):
                if ticker and koers > 0:
                    requests.post(API_URL, data=json.dumps({"ticker":ticker, "inleg":inleg, "koers":koers}))
                    st.success(f"{ticker} opgeslagen!")
                    st.rerun()

    with col_r:
        st.subheader("Huidige Posities")
        if not df_pf.empty:
            tickers_pf = df_pf['T'].tolist()
            data_pf = get_market_data(tickers_pf)
            
            rows = []
            total_profit = 0
            for _, row in df_pf.iterrows():
                t = row['T']
                if t in data_pf:
                    cur = data_pf[t]
                    winst = ((inv := float(row['I'])) / (buy := float(row['P'])) * cur['p']) - inv
                    total_profit += winst
                    rows.append({
                        "Ticker": t, "Inleg": inv, "Koers": buy, 
                        "Nu": round(cur['p'], 2), "Winst": round(winst, 2), "Status": cur['s']
                    })
            
            res_df = pd.DataFrame(rows)
            st.metric("Totaal Saldo Winst/Verlies", f"€ {total_profit:.2f}")
            
            def color_status(v):
                colors = {'BUY': 'background-color: green', 'SELL': 'background-color: red', 
                          'WAIT': 'background-color: orange', 'ACCUMULATE': 'background-color: lightgreen'}
                return colors.get(v, '')

            st.dataframe(res_df.style.applymap(color_status, subset=['Status']), hide_index=True, use_container_width=True)
            
            # Verwijderen sectie
            with st.expander("Trades Sluiten / Verwijderen"):
                for t in tickers_pf:
                    if st.button(f"Sluit {t} Trade", key=f"del_{t}"):
                        requests.post(API_URL, data=json.dumps({"method":"delete", "ticker":t}))
                        st.rerun()
        else:
            st.info("Geen actieve trades.")

# --- TAB 2: DAYTRADE SCANNER (TOP 25) ---
with t2:
    st.subheader("Top 25 Liquide Aandelen (RSI Focus)")
    top_25 = [
        'NVDA', 'TSLA', 'AAPL', 'MSFT', 'AMZN', 'META', 'AMD', 'NFLX', 'GOOGL', 'ASML.AS',
        'INGA.AS', 'SHELL.AS', 'ADYEN.AS', 'JPM', 'V', 'MA', 'BABA', 'PLTR', 'COIN', 'NIO',
        'MARA', 'RIOT', 'SQ', 'PYPL', 'DIS'
    ]
    market_db = get_market_data(top_25)
    
    scan_rows = []
    for t in top_25:
        if t in market_db:
            m = market_db[t]
            scan_rows.append({"Ticker": t, "Prijs": m['p'], "RSI (14)": round(m['rsi'],1), "Actie": m['s']})
    
    scan_df = pd.DataFrame(scan_rows).sort_values(by="RSI (14)")
    st.dataframe(scan_df.style.applymap(color_status, subset=['Actie']), use_container_width=True, hide_index=True)

# --- TAB 3: TREND MONITOR ---
with t3:
    st.subheader("Trend Analyse (6 Maanden vs 1 Jaar)")
    trend_rows = []
    for t in top_25:
        if t in market_db:
            m = market_db[t]
            trend_rows.append({
                "Ticker": t, "Nu": round(m['p'],2), 
                "6 Maanden %": round(m['6m'], 1), "1 Jaar %": round(m['1y'], 1)
            })
    
    st.table(pd.DataFrame(trend_rows).sort_values(by="6 Maanden %", ascending=False))
