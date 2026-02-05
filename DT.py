import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time
import os

st.set_page_config(page_title="Active Trader", layout="wide")

# --- BESTANDSLOGICA ---
PORTFOLIO_FILE = "my_portfolio.csv"

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        return pd.read_csv(PORTFOLIO_FILE).to_dict('records')
    return []

def save_portfolio(data):
    pd.DataFrame(data).to_csv(PORTFOLIO_FILE, index=False)

# Initialiseer sessie
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_portfolio()

# --- SIDEBAR: PORTFOLIO BEHEER ---
st.sidebar.header("📥 Portfolio Beheer")
with st.sidebar.form("add_form", clear_on_submit=True):
    new_ticker = st.text_input("Ticker (bijv. AAPL)").upper()
    new_inleg = st.number_input("Ingelegd bedrag ($)", min_value=0.0, step=10.0)
    new_prijs = st.number_input("Aankoopprijs ($)", min_value=0.0, step=0.1)
    submit = st.form_submit_button("Voeg toe aan Portfolio")

if submit and new_ticker:
    # Voeg toe aan lijst
    st.session_state.portfolio.append({
        "Ticker": new_ticker,
        "Inleg": new_inleg,
        "Aankoop": new_prijs
    })
    save_portfolio(st.session_state.portfolio)
    st.sidebar.success(f"{new_ticker} opgeslagen!")

if st.sidebar.button("🗑️ Wis hele Portfolio"):
    st.session_state.portfolio = []
    if os.path.exists(PORTFOLIO_FILE):
        os.remove(PORTFOLIO_FILE)
    st.rerun()

# --- MAIN APP ---
st.title("🛡️ Active Dividend Swing Trader")

tickers = [
    'KO', 'PEP', 'JNJ', 'O', 'PG', 'ABBV', 'CVX', 'XOM', 'MMM', 'T',
    'VZ', 'WMT', 'LOW', 'TGT', 'ABT', 'MCD', 'ADBE', 'MSFT', 'AAPL', 'IBM',
    'HD', 'COST', 'LLY', 'PFE', 'MRK', 'DHR', 'UNH', 'BMY', 'AMGN', 'SBUX',
    'CAT', 'DE', 'HON', 'UPS', 'FDX', 'NEE', 'SO', 'D', 'DUK', 'PM',
    'MO', 'SCHW', 'BLK', 'SPGI', 'V', 'MA', 'AVGO', 'TXN', 'NVDA', 'JPM'
]

@st.cache_data(ttl=3600)
def get_data(s):
    try:
        t = yf.Ticker(s)
        h = t.history(period="1y")
        if h.empty: return None
        inf = t.info
        return {
            "h": h, "d": (inf.get('dividendYield', 0) or 0) * 100,
            "s": inf.get('sector', 'N/B'), "e": inf.get('exchange', 'Beurs'),
            "t": inf.get('targetMeanPrice', None), "p": h['Close'].iloc[-1]
        }
    except: return None

res, port_res = [], []
bar = st.progress(0)

# Verwerk alle tickers voor de scanner
all_symbols = list(set(tickers + [p['Ticker'] for p in st.session_state.portfolio]))

for i, s in enumerate(all_symbols):
    data = get_data(s)
    if data:
        price = data['p']
        df = data['h']
        rsi = ta.rsi(df['Close'], length=14).iloc[-1]
        
        # Check of dit aandeel in ons portfolio zit
        for p in st.session_state.portfolio:
            if p['Ticker'] == s:
                aantal = p['Inleg'] / p['Aankoop']
                waarde = aantal * price
                winst = waarde - p['Inleg']
                port_res.append({
                    "Ticker": s, "Inleg": p['Inleg'], "Waarde": round(waarde, 2),
                    "Resultaat": round(winst, 2), "%": round((winst/p['Inleg'])*100, 1),
                    "RSI": round(rsi, 1)
                })

        # Scanner logica (alleen voor de hoofdlijst)
        if s in tickers:
            m1y = df['Close'].mean()
            m6m = df['Close'].tail(126).mean()
            t1y, t6m = ("✅" if price > m1y else "❌"), ("✅" if price > m6m else "❌")
            target = data['t']
            upside = round(((target-price)/price)*100, 1) if target and target > 0 else 0
            
            if t1y == "✅" and t6m == "✅" and rsi < 45: adv = "🌟 KOOP DIP"
            elif t1y == "✅" and rsi > 70: adv = "💰 WINST PAKKEN"
            elif t1y == "✅": adv = "🟢 HOLD"
            else: adv = "🔴 VERMIJDEN"

            res.append({
                "Ticker": s, "Status": adv, "Prijs": round(price, 2), 
                "Upside%": upside, "Div%": round(data['d'], 2), "RSI": round(rsi, 1)
            })
    bar.progress((i + 1) / len(all_symbols))

# --- DASHBOARD WEERGAVE ---
if port_res:
    st.subheader("📊 Mijn Open Posities")
    pdf = pd.DataFrame(port_res)
    tot_res = sum([x['Resultaat'] for x in port_res])
    st.metric("Totaal Resultaat", f"$ {tot_res:.2f}", delta=f"{tot_res:.2f}")
    st.dataframe(pdf, use_container_width=True, hide_index=True)

st.divider()
st.subheader("🔍 Markt Kansen")
if res:
    df_f = pd.DataFrame(res).sort_values("Div%", ascending=False)
    st.dataframe(df_f, use_container_width=True, hide_index=True)

time.sleep(900)
st.rerun()
