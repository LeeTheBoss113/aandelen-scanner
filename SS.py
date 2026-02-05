import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time

st.set_page_config(page_title="Dividend Pro", layout="wide")

# --- 1. JOUW PORTFOLIO INVULLEN ---
# Formaat: 'TICKER': [Totaal Bedrag Geïnvesteerd, Gemiddelde Aankoopprijs]
MIJN_PORTFOLIO = {
    'IBM': [185.00, 288.11],   # Ik heb voor $500 gekocht tegen een prijs van 58.50
    'DHR': [180.00, 220.58], # Ik heb voor $250 gekocht tegen een prijs van 180.20
    'T': [135.00, 27.11]     # Ik heb voor $1000 gekocht tegen een prijs van 52.00
}

# --- REKENMODEL IN DE LOOP ---
# (Dit deel zit al in de code verwerkt, maar zo werkt de som nu:)
# Aantal = Totaal Bedrag / Aankoopprijs
# Actuele Waarde = Aantal * Huidige Prijs

st.title("🛡️ Lange(re) Termijn Dividend Trader")

nu = time.strftime('%H:%M:%S')
st.sidebar.write("Laatste update:", nu)

tickers = [
    'KO', 'PEP', 'JNJ', 'O', 'PG', 'ABBV', 'CVX', 'XOM', 'MMM', 'T',
    'VZ', 'WMT', 'LOW', 'TGT', 'ABT', 'MCD', 'ADBE', 'MSFT', 'AAPL', 'IBM',
    'HD', 'COST', 'LLY', 'PFE', 'MRK', 'DHR', 'UNH', 'BMY', 'AMGN', 'SBUX',
    'CAT', 'DE', 'HON', 'UPS', 'FDX', 'NEE', 'SO', 'D', 'DUK', 'PM',
    'MO', 'SCHW', 'BLK', 'SPGI', 'V', 'MA', 'AVGO', 'TXN', 'NVDA', 'JPM'
]

@st.cache_data(ttl=3600)
def get_stock_info(s):
    try:
        t = yf.Ticker(s)
        h = t.history(period="1y")
        if h.empty: return None
        i = t.info
        return {
            "h": h,
            "d": (i.get('dividendYield', 0) or 0) * 100,
            "s": i.get('sector', 'Onbekend'),
            "e": i.get('exchange', 'Beurs'),
            "t": i.get('targetMeanPrice', None),
            "p": h['Close'].iloc[-1]
        }
    except:
        return None

res = []
port_res = []
bar = st.progress(0)

for i, s in enumerate(tickers):
    data = get_stock_info(s)
    if data:
        df, price = data['h'], data['p']
        rsi = ta.rsi(df['Close'], length=14).iloc[-1]
        m1y, m6m = df['Close'].mean(), df['Close'].tail(126).mean()
        
        t1y = "✅" if price > m1y else "❌"
        t6m = "✅" if price > m6m else "❌"
        
        # Portfolio check
        if s in MIJN_PORTFOLIO:
            aantal, aankoop = MIJN_PORTFOLIO[s]
            waarde = aantal * price
            winst = waarde - (aantal * aankoop)
            winst_perc = (winst / (aantal * aankoop)) * 100
            port_res.append({
                "Ticker": s, "Aantal": aantal, "Aankoop": aankoop,
                "Huidig": round(price, 2), "Winst/Verlies": round(winst, 2),
                "Rendement%": round(winst_perc, 1)
            })

        # Advies Logica
        target = data['t']
        upside = round(((target - price) / price) * 100, 1) if target and target > 0 else 0
        if t1y == "✅" and t6m == "✅" and rsi < 45: adv = "🌟 KOOP"
        elif t1y == "✅" and rsi > 70: adv = "💰 WINST"
        elif t1y == "✅": adv = "🟢 HOLD"
        else: adv = "🔴 NEE"

        res.append({
            "Ticker": s, "Beurs": data['e'], "Sector": data['s'],
            "Status": adv, "Prijs": round(price, 2), "Target": target,
            "Upside%": upside, "Div%": round(data['d'], 2), "RSI": round(rsi, 1)
        })
    bar.progress((i + 1) / len(tickers))

# --- DASHBOARD WEERGAVE ---

# 1. Portfolio Sectie
if port_res:
    st.subheader("📈 Mijn Portfolio Status")
    pdf = pd.DataFrame(port_res)
    total_winst = pdf['Winst/Verlies'].sum()
    st.metric("Totaal Winst/Verlies", f"$ {total_winst:.2f}", delta=f"{total_winst:.2f}")
    st.table(pdf) # Simpele tabel voor overzichtelijkheid

st.divider()

# 2. Scanner Sectie
st.subheader("🔍 Markt Scanner")
if res:
    final_df = pd.DataFrame(res).sort_values("Div%", ascending=False)
    st.dataframe(
        final_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Upside%": st.column_config.ProgressColumn("Upside", format="%d%%", min_value=-20, max_value=50),
            "Prijs": st.column_config.NumberColumn(format="$ %.2f"),
            "Target": st.column_config.NumberColumn(format="$ %.2f")
        }
    )

time.sleep(900)
st.rerun()



