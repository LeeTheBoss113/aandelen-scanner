import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG & VEILIGHEID ---
st.set_page_config(layout="wide", page_title="Daytrade Simulator Pro 2026")

try:
    API_URL = st.secrets["google_api_url"]
except:
    st.error("⚠️ API_URL niet gevonden in Secrets!")
    st.stop()

# --- STYLING FUNCTIES ---
def style_action(val):
    if '✅ STERKE BUY' in val or '💎 SAFE BUY' in val: color = '#1e8449'
    elif 'BUY' in val: color = '#2ecc71'
    elif 'SELL' in val: color = '#e74c3c'
    elif '⚠️ VALLEND MES' in val or '❌ ZWAK' in val: color = '#9b59b6'
    elif 'WAIT' in val: color = '#f1c40f'
    else: color = '#3498db'
    return f'background-color: {color}; color: white; font-weight: bold'

def style_trend(val):
    try:
        num = float(val.replace('%', ''))
        color = '#2ecc71' if num > 0 else '#e74c3c'
        return f'color: {color}; font-weight: bold'
    except: return ''

def style_portfolio(ticker, portfolio_list):
    if ticker in portfolio_list:
        return 'background-color: #ffcc80; color: black; font-weight: bold'
    return ''

# --- DATA FUNCTIES ---
def get_all_data():
    try:
        r = requests.get(f"{API_URL}?t={int(time.time())}", timeout=10)
        res = r.json()
        active_raw = res.get('active', [])
        log_raw = res.get('log', [])
        df_active = pd.DataFrame(active_raw[1:], columns=["Ticker", "Inleg", "Koers"]) if len(active_raw) > 1 else pd.DataFrame(columns=["Ticker", "Inleg", "Koers"])
        df_active['Inleg'] = pd.to_numeric(df_active['Inleg'], errors='coerce')
        df_active['Koers'] = pd.to_numeric(df_active['Koers'], errors='coerce')
        df_log = pd.DataFrame(log_raw[1:], columns=["Datum", "Ticker", "Inleg", "Winst"]) if len(log_raw) > 1 else pd.DataFrame(columns=["Datum", "Ticker", "Inleg", "Winst"])
        if not df_log.empty: df_log['Winst'] = pd.to_numeric(df_log['Winst'], errors='coerce')
        return df_active.dropna(subset=['Ticker']), df_log
    except:
        return pd.DataFrame(columns=["Ticker", "Inleg", "Koers"]), pd.DataFrame(columns=["Datum", "Ticker", "Inleg", "Winst"])

@st.cache_data(ttl=300)
def fetch_market(tickers, include_div=False):
    results = {}
    for t in tickers:
        try:
            tk = yf.Ticker(t)
            h = tk.history(period="1y") 
            if h.empty: continue
            price = h['Close'].iloc[-1]
            rsi = ta.rsi(h['Close'], 14).iloc[-1]
            p6m = h['Close'].iloc[-126] if len(h) >= 126 else h['Close'].iloc[0]
            trend6m = ((price - p6m) / p6m) * 100
            p12m = h['Close'].iloc[0]
            trend12m = ((price - p12m) / p12m) * 100
            
            div_yield = 0.0
            if include_div:
                div_yield = tk.info.get('dividendYield', 0.0) * 100 if tk.info.get('dividendYield') else 0.0
            
            status = "WAIT"
            if rsi < 35: status = "BUY"
            elif rsi > 65: status = "SELL"
            
            results[t] = {"price": price, "rsi": rsi, "status": status, "trend6m": trend6m, "trend12m": trend12m, "div": div_yield}
        except: continue
    return results

# --- MAIN ---
df_active, df_log = get_all_data()
gerealiseerde_winst = df_log['Winst'].sum() if not df_log.empty else 0.0
tickers_in_sheet = [t for t in df_active['Ticker'].unique().tolist() if t and t != 'NONE']

st.title("⚡ Pro Daytrade & Dividend Dashboard")

m1, m2, m3 = st.columns(3)
m1.metric("Gerealiseerd", f"€{gerealiseerde_winst:.2f}")
# (Berekening openstaande winst zoals voorheen...)

st.divider()

tab1, tab2, tab3, tab4 = st.tabs(["📊 Portfolio", "🔍 Smart Scanner", "🛡️ Safe Haven (Div)", "📜 Historie"])

with tab2:
    st.subheader("🔍 Momentum Scanner (Groeiaandelen)")
    # Bestaande scanner code...
    watchlist = ['NVDA','TSLA','AAPL','MSFT','AMZN','META','AMD','ASML.AS','PLTR','COIN']
    # ... (styling en weergave)

with tab3:
    st.subheader("🛡️ Dividend Safe Haven")
    st.caption("Focus op passief inkomen en stabiliteit. Alleen kopen bij positieve 12M trend.")
    
    div_watch = ['KO', 'PEP', 'JNJ', 'PG', 'O', 'ABBV', 'MMM', 'INGA.AS', 'NN.AS', 'ASRNL.AS', 'RDSA.AS']
    m_div = fetch_market(div_watch, include_div=True)
    
    if m_div:
        div_rows = []
        for k, v in m_div.items():
            status = v['status']
            if v['trend12m'] < 0:
                status = "❌ ZWAK"
            elif v['status'] == "BUY" and v['trend12m'] > 0:
                status = "💎 SAFE BUY"
            
            div_rows.append({
                "Ticker": k, "Prijs": round(v['price'], 2), "Div %": f"{v['div']:.1f}%",
                "RSI": round(v['rsi'], 1), "12M Trend": f"{v['trend12m']:.1f}%", "Advies": status
            })
        
        df_d = pd.DataFrame(div_rows).sort_values('Div %', ascending=False)
        st.dataframe(
            df_d.style.map(style_action, subset=['Advies'])
                .map(style_trend, subset=['12M Trend'])
                .apply(lambda x: [style_portfolio(val, tickers_in_sheet) if x.name == 'Ticker' else '' for val in x]),
            use_container_width=True, hide_index=True
        )

# (Rest van de tabs: Portfolio en Historie zoals voorheen...)