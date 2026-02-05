import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time
import os

# --- 1. CONFIGURATIE & SETUP ---
st.set_page_config(page_title="Stability Investor Pro", layout="wide")

PF_FILE = "stability_portfolio.csv"

def load_pf():
    if os.path.exists(PF_FILE):
        try: return pd.read_csv(PF_FILE).to_dict('records')
        except: return []
    return []

def save_pf(data):
    pd.DataFrame(data).to_csv(PF_FILE, index=False)

if 'pf_data' not in st.session_state:
    st.session_state.pf_data = load_pf()

# --- 2. SIDEBAR (INVOER) ---
with st.sidebar:
    st.header("⚙️ Instellingen")
    with st.form("add_stock", clear_on_submit=True):
        t_in = st.text_input("Ticker").upper().strip()
        b_in = st.number_input("Inleg ($)", min_value=0.0, step=10.0)
        p_in = st.number_input("Aankoopprijs ($)", min_value=0.01, step=0.1)
        if st.form_submit_button("➕ Voeg toe"):
            if t_in:
                st.session_state.pf_data.append({"Ticker": t_in, "Inleg": b_in, "Prijs": p_in})
                save_pf(st.session_state.pf_data)
                st.rerun()

    if st.button("🗑️ Wis Portfolio Data"):
        st.session_state.pf_data = []
        if os.path.exists(PF_FILE): os.remove(PF_FILE)
        st.rerun()

# --- 3. DATA ENGINE (BACK-END) ---
markt_list = ['KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','MMM','T','VZ','WMT','LOW','TGT','ABT','MCD','MSFT','AAPL','IBM','HD','COST','LLY','PFE','MRK','UNH','BMY','SBUX','CAT','DE','NEE','PM','MO','BLK','V','MA','AVGO','TXN','JPM','SCHW']
mijn_list = [p['Ticker'] for p in st.session_state.pf_data]
alle_tickers = list(set(markt_list + mijn_list))

@st.cache_data(ttl=3600)
def fetch_stock_data(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="2y")
        if h.empty: return None
        return {"h": h, "info": tk.info, "price": h['Close'].iloc[-1]}
    except: return None

# Verzamel alle data
pf_results, market_results = [], []
progress_bar = st.progress(0)

for i, ticker in enumerate(alle_tickers):
    data = fetch_stock_data(ticker)
    if data:
        p, h, inf = data['price'], data['h'], data['info']
        rsi = ta.rsi(h['Close'], length=14).iloc[-1] if len(h) > 14 else 50
        ma200 = h['Close'].tail(200).mean() if len(h) >= 200 else p
        
        # Status Logica
        status = "STABIEL" if p > ma200 else "WACHTEN"
        if p > ma200 and rsi < 42: status = "KOOP"
        if p > ma200 and rsi > 75: status = "DUUR"

        # Portfolio Verwerking
        for p_item in st.session_state.pf_data:
            if p_item['Ticker'] == ticker:
                waarde = (p_item['Inleg'] / p_item['Prijs']) * p
                pf_results.append({
                    "Ticker": ticker, "Inleg": p_item['Inleg'], "Waarde": waarde,
                    "Winst": waarde - p_item['Inleg'], "RSI": rsi, "Status": status
                })

        # Markt Scanner Verwerking
        if ticker in markt_list:
            market_results.append({
                "Ticker": ticker, "Sector": inf.get('sector', 'N/B'), 
                "Dividend": (inf.get('dividendYield', 0) or 0) * 100,
                "Payout": (inf.get('payoutRatio', 0) or 0) * 100,
                "Status": status, "RSI": rsi
            })
    progress_bar.progress((i + 1) / len(alle_tickers))

# --- 4. FRONT-END (TABS) ---
st.title("🏦 Stability Investor Dashboard")

tab1, tab2, tab3 = st.tabs(["📊 Mijn Portfolio", "🔍 Markt Scanner", "🛡️ Strategie Info"])

with tab1:
    if pf_results:
        df_pf = pd.DataFrame(pf_results)
        c1, c2 = st.columns(2)
        c1.metric("Totaal Investering", f"$ {df_pf['Inleg'].sum():.2f}")
        c2.metric("Netto Resultaat", f"$ {df_pf['Winst'].sum():.2f}", delta=f"{df_pf['Winst'].sum():.2f}")
        
        st.dataframe(df_pf, use_container_width=True, hide_index=True, column_config={
            "Inleg": st.column_config.NumberColumn(format="$ %.2f"),
            "Waarde": st.column_config.NumberColumn(format="$ %.2f"),
            "Winst": st.column_config.NumberColumn(format="$ %.2f"),
            "RSI": st.column_config.ProgressColumn(min_value=0, max_value=100)
        })
    else:
        st.info("Je portfolio is nog leeg. Voeg tickers toe in de zijbalk.")

with tab2:
    if market_results:
        df_m = pd.DataFrame(market_results).sort_values("Dividend", ascending=False)
        st.dataframe(df_m, use_container_width=True, hide_index=True, column_config={
            "Dividend": st.column_config.NumberColumn(format="%.2f%%"),
            "Payout": st.column_config.NumberColumn(format="%.1f%%"),
            "RSI": st.column_config.ProgressColumn(min_value=0, max_value=100)
        })

with tab3:
    st.subheader("Hoe werkt dit systeem?")
    st.write("""
    - **STABIEL:** Koers ligt boven het 200-daags gemiddelde. Gezonde trend.
    - **KOOP:** Stabiele trend, maar de RSI is laag (onder 42). Een goede dip om bij te kopen.
    - **DUUR:** RSI is boven de 75. Mogelijk tijd om winst te nemen.
    - **WACHTEN:** Koers ligt onder het 200-daags gemiddelde. De lange termijn trend is negatief.
    """)

time.sleep(900)
st.rerun()
