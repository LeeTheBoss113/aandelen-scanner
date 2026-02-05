import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import time
import os

# --- 1. SETUP ---
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

# --- 2. SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Beheer")
    with st.form("add_stock", clear_on_submit=True):
        t_in = st.text_input("Ticker").upper().strip()
        i_in = st.number_input("Inleg ($)", min_value=0.0, step=10.0)
        p_in = st.number_input("Aankoopprijs ($)", min_value=0.01, step=0.1)
        if st.form_submit_button("➕ Toevoegen"):
            if t_in:
                st.session_state.pf_data.append({"Ticker": t_in, "Inleg": i_in, "Prijs": p_in})
                save_pf(st.session_state.pf_data)
                st.rerun()

    if st.session_state.pf_data:
        st.divider()
        st.subheader("🗑️ Verwijderen")
        for n, item in enumerate(st.session_state.pf_data):
            c1, c2 = st.columns([3, 1])
            c1.write(f"**{item['Ticker']}**")
            if c2.button("❌", key=f"del_{n}"):
                st.session_state.pf_data.pop(n)
                save_pf(st.session_state.pf_data)
                st.rerun()

# --- 3. DATA ENGINE ---
m_list = ['KO','PEP','JNJ','O','PG','ABBV','CVX','XOM','MMM','T','VZ','WMT','LOW','TGT','ABT','MCD','MSFT','AAPL','IBM','HD','COST','LLY','PFE','MRK','UNH','BMY','SBUX','CAT','DE','NEE','PM','MO','BLK','V','MA','AVGO','TXN','JPM','SCHW']
a_list = list(set(m_list + [x['Ticker'] for x in st.session_state.pf_data]))

@st.cache_data(ttl=3600)
def get_stock(s):
    try:
        tk = yf.Ticker(s)
        h = tk.history(period="2y")
        if h.empty: return None
        return {"h": h, "i": tk.info, "p": h['Close'].iloc[-1]}
    except: return None

pf_res, sc_res = [], []
pb = st.progress(0)

for i, t in enumerate(a_list):
    d = get_stock(t)
    if d:
        p, h, inf = d['p'], d['h'], d['i']
        rsi = ta.rsi(h['Close'], length=14).iloc[-1] if len(h) > 14 else 50
        ma = h['Close'].tail(200).mean() if len(h) >= 200 else p
        
        # Status Logica
        stt = "WACHTEN"
        if p > ma:
            stt = "STABIEL"
            if rsi < 42: stt = "KOOP"
            if rsi > 75: stt = "DUUR"

        # Winstberekening voor Portfolio
        for pi in st.session_state.pf_data:
            if pi['Ticker'] == t:
                # Aantal aandelen = Inleg / Aankoopprijs
                aantal = pi['Inleg'] / pi['Prijs']
                waarde = aantal * p
                winst = waarde - pi['Inleg']
                pf_res.append({
                    "Ticker": t, "Inleg": pi['Inleg'], "Koers": p, 
                    "Waarde": waarde, "Winst": winst, "Status": stt
                })

        # Markt Scanner
        if t in m_list:
            sc_res.append({
                "Ticker": t, "Koers": p, "Sector": inf.get('sector', 'N/B'), 
                "Div": (inf.get('dividendYield', 0) or 0) * 100,
                "Pay": (inf.get('payoutRatio', 0) or 0) * 100, 
                "Status": stt, "RSI": rsi
            })
    pb.progress((i + 1) / len(a_list))

# --- 4. VIEW ---
st.title("🏦 Stability Investor Dashboard")
t1, t2 = st.tabs(["📊 Portfolio", "🔍 Scanner"])

def style_it(df):
    def _stt(v):
        if v == "KOOP": return "background-color: #d4edda; color: #155724;"
        if v == "WACHTEN": return "background-color: #f8d7da; color: #721c24;"
        return ""
    return df.style.map(_stt, subset=['Status'])

with t1:
    if pf_res:
        df_p = pd.DataFrame(pf_res)
        c1, c2, c3 = st.columns(3)
        c1.metric("Investering", f"$ {df_p['Inleg'].sum():.2f}")
        c2.metric("Waarde", f"$ {df_p['Waarde'].sum():.2f}")
        c3.metric("Winst/Verlies", f"$ {df_p['Winst'].sum():.2f}", delta=f"{df_p['Winst'].sum():.2f}")
        
        st.dataframe(style_it(df_p), use_container_width=True, hide_index=True, column_config={
            "Inleg": st.column_config.NumberColumn(format="$ %.2f"),
            "Koers": st.column_config.NumberColumn(format="$ %.2f"),
            "Waarde": st.column_config.NumberColumn(format="$ %.2f"),
            "Winst": st.column_config.NumberColumn(format="$ %.2f")
        })
    else: st.info("Portfolio is leeg.")

with t2:
    if sc_res:
        df_s = pd.DataFrame(sc_res)
        rk = {"KOOP": 1, "STABIEL": 2, "DUUR": 3, "WACHTEN": 4}
        df_s['R'] = df_s['Status'].map(rk)
        df_s = df_s.sort_values(['R', 'Div'], ascending=[True, False]).drop(columns='R')
        
        st.dataframe(style_it(df_s), use_container_width=True, hide_index=True, column_config={
            "Koers": st.column_config.NumberColumn(format="$ %.2f"),
            "Div": st.column_config.NumberColumn(format="%.2f%%"),
            "Pay": st.column_config.NumberColumn(format="%.1f%%"),
            "RSI": st.column_config.ProgressColumn(min_value=0, max_value=100)
        })

time.sleep(900)
st.rerun()
