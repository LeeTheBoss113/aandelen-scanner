import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time
import os

st.set_page_config(page_title="Stability Investor", layout="wide")

# Bestandsbeheer voor portfolio
PF_FILE = "stability_portfolio.csv"
def load_pf():
    return pd.read_csv(PF_FILE).to_dict('records') if os.path.exists(PF_FILE) else []
def save_pf(data):
    pd.DataFrame(data).to_csv(PF_FILE, index=False)

if 'pf_data' not in st.session_state:
    st.session_state.pf_data = load_pf()

# --- SIDEBAR: PORTFOLIO ---
st.sidebar.header("🏦 Lange Termijn Portfolio")
with st.sidebar.form("invul_form", clear_on_submit=True):
    t_in = st.text_input("Ticker").upper()
    b_in = st.number_input("Totaal Ingelegd ($)", min_value=0.0)
    p_in = st.number_input("Gem. Aankoopprijs ($)", min_value=0.0)
    submit = st.form_submit_button("Voeg toe aan Posities")

if submit and t_in:
    st.session_state.pf_data.append({"Ticker": t_in, "Inleg": b_in, "Prijs": p_in})
    save_pf(st.session_state.pf_data)
    st.sidebar.success(f"{t_in} opgeslagen")

# --- MAIN APP ---
st.title("📈 Dividend Stability & Quality Scanner")
st.markdown("*Focus op de lange termijn: Sterke trends en houdbare dividenden.*")

# De 'Dividend Aristocrats' & 'Kings' selectie
tickers = [
    'KO', 'PEP', 'JNJ', 'O', 'PG', 'ABBV', 'CVX', 'XOM', 'MMM', 'T',
    'VZ', 'WMT', 'LOW', 'TGT', 'ABT', 'MCD', 'MSFT', 'AAPL', 'IBM',
    'HD', 'COST', 'LLY', 'PFE', 'MRK', 'UNH', 'BMY', 'SBUX', 'CAT', 'DE',
    'NEE', 'PM', 'MO', 'BLK', 'V', 'MA', 'AVGO', 'TXN', 'JPM', 'SCHW'
]

@st.cache_data(ttl=3600)
def get_stability_data(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="2y") # Meer historie voor stabiliteit
        if h.empty: return None
        i = tk.info
        return {
            "h": h, 
            "div": (i.get('dividendYield', 0) or 0) * 100,
            "payout": (i.get('payoutRatio', 0) or 0) * 100, # Belangrijk voor stabiliteit!
            "sector": i.get('sector', 'N/B'),
            "price": h['Close'].iloc[-1]
        }
    except: return None

scanner_res, pf_res = [], []
balk = st.progress(0)
alle_tickers = list(set(tickers + [p['Ticker'] for p in st.session_state.pf_data]))

for n, s in enumerate(alle_tickers):
    data = get_stability_data(s)
    if data:
        p, h = data['price'], data['h']
        # Indicatoren voor lange termijn
        ma200 = h['Close'].tail(200).mean() # De 'Golden Line'
        ma50 = h['Close'].tail(50).mean()
        rsi = ta.rsi(h['Close'], length=14).iloc[-1]
        
        # Stabiliteit Checks
        is_bullish = p > ma200 and ma50 > ma200
        payout_safe = data['payout'] < 75 # Dividend is veilig als payout < 75%
        
        # Lange Termijn Advies Logica
        if is_bullish and rsi < 40: adv = "💎 STERKE KOOP"
        elif is_bullish and rsi > 75: adv = "⚠️ OVERVERHIT"
        elif is_bullish: adv = "✅ STABIEL"
        else: adv = "⏳ WACHTEN"

        # Portfolio Verwerking
        for entry in st.session_state.pf_data:
            if entry['Ticker'] == s:
                waarde = (entry['Inleg'] / entry['Prijs']) * p
                pf_res.append({
                    "Ticker": s, "Inleg": entry['Inleg'], "Waarde": round(waarde, 2),
                    "Resultaat": round(waarde - entry['Inleg'], 2), 
                    "%": round(((waarde - entry['Inleg'])/entry['Inleg'])*100, 1),
                    "Status": adv
                })

        if s in tickers:
            scanner_res.append({
                "Ticker": s, "Sector": data['sector'], "Status": adv,
                "Div %": round(data['div'], 2), "Payout %": round(data['payout'], 1),
                "Boven MA200": "Ja" if p > ma200 else "Nee", "RSI": round(rsi, 1)
            })
    balk.progress((n + 1) / len(alle_tickers))

# --- DASHBOARD ---
if pf_res:
    st.subheader("🏦 Mijn Lange Termijn Posities")
    st.dataframe(pd.DataFrame(pf_res), use_container_width=True, hide_index=True)

st.divider()
st.subheader("🔍 Stabiliteits Scanner (Top Kwaliteit)")
if scanner_res:
    df_sc = pd.DataFrame(scanner_res).sort_values("Div %", ascending=False)
    
    def color_payout(val):
        return 'color: #dc3545' if val > 80 else 'color: #28a745'
    
    st.dataframe(df_sc.style.applymap(color_payout, subset=['Payout %']), use_container_width=True, hide_index=True)

time.sleep(900)
st.rerun()
