import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="Scanner 2026")

API_URL = "https://script.google.com/macros/s/AKfycbyFLn_y2SiI8GNgAC8W6YajFHm8QS-i8dlATnL2QOTpS30BthsPCRqyj23sxjg5RmEe/exec"

# --- DATA OPHALEN ---
def get_data():
    try:
        r = requests.get(f"{API_URL}?t={int(time.time())}", timeout=10).json()
        
        def clean(raw_data, fallback_cols):
            if not raw_data or len(raw_data) <= 1:
                return pd.DataFrame(columns=fallback_cols)
            
            df = pd.DataFrame(raw_data[1:])
            # Zorg dat we altijd 4 kolommen hebben (Ticker, Inleg, Koers, Type)
            while len(df.columns) < 4:
                df[len(df.columns)] = ""
                
            df = df.iloc[:, :4]
            df.columns = fallback_cols
            
            # Types opschonen: verwijder spaties en zet alles naar hoofdletters voor de vergelijking
            df['Type'] = df['Type'].astype(str).str.strip().upper()
            df['Ticker'] = df['Ticker'].astype(str).str.strip().upper()
            
            for col in ['Inleg', 'Koers']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            return df[df['Ticker'] != ""]

        return clean(r.get('active', []), ["Ticker", "Inleg", "Koers", "Type"]), \
               clean(r.get('log', []), ["Datum", "Ticker", "Inleg", "Winst", "Type"])
    except:
        return pd.DataFrame(columns=["Ticker", "Inleg", "Koers", "Type"]), pd.DataFrame()

# --- DATA LADEN ---
df_active, df_log = get_data()

st.title("🚀 Dual-Strategy Dashboard")

# FILTERING (Extra robuust)
growth_active = df_active[df_active['Type'] == "GROWTH"]
div_active = df_active[df_active['Type'] == "DIVIDEND"]

tab1, tab2, tab3 = st.tabs(["📈 Growth Strategy", "💎 Dividend Strategy", "📜 Logboek"])

def render_portfolio(df, p_type_label, p_type_value):
    st.subheader(f"Actieve {p_type_label} posities")
    
    # Haal koersen op voor de tabel
    if not df.empty:
        tickers = df['Ticker'].tolist()
        # Voeg watchlist toe aan data ophalen
        watchlist = ['NVDA','TSLA','AAPL','MSFT'] if p_type_value == "Growth" else ['KO','PEP','O','JNJ']
        all_t = list(set(tickers + watchlist))
        
        # Simpele koers ophaal actie
        market_data = {}
        for t in all_t:
            try:
                # Alleen ophalen als we het aandeel echt in bezit hebben voor de winstberekening
                if t in tickers:
                    tk = yf.Ticker(t)
                    price = tk.history(period="1d")['Close'].iloc[-1]
                    market_data[t] = price
            except: continue

        # Bereken winst
        pf_display = []
        for _, r in df.iterrows():
            nu_koers = market_data.get(r['Ticker'], 0)
            winst = ((r['Inleg'] / r['Koers']) * nu_koers) - r['Inleg'] if r['Koers'] > 0 and nu_koers > 0 else 0
            pf_display.append({
                "Ticker": r['Ticker'], "Inleg": r['Inleg'], "Aankoop": r['Koers'], 
                "Nu": round(nu_koers, 2), "Winst": round(winst, 2)
            })
        
        st.dataframe(pd.DataFrame(pf_display), use_container_width=True, hide_index=True)
        
        # Verkoop knop
        sel = st.selectbox("Sluit positie:", [""] + tickers, key=f"sel_{p_type_value}")
        if st.button("Verkoop & Log", key=f"btn_{p_type_value}"):
            if sel:
                row = [p for p in pf_display if p['Ticker'] == sel][0]
                requests.post(API_URL, data=json.dumps({
                    "method": "delete", "ticker": sel, "inleg": row['Inleg'], "winst": row['Winst'], "type": p_type_value
                }))
                st.rerun()
    else:
        st.info(f"Geen actieve {p_type_label} aandelen in Google Sheets.")

    # Toevoeg formulier
    with st.expander(f"➕ Voeg {p_type_label} toe"):
        with st.form(f"add_{p_type_value}"):
            t_in = st.text_input("Ticker").upper()
            i_in = st.number_input("Inleg (€)", 100)
            k_in = st.number_input("Koers", 0.0)
            if st.form_submit_button("Opslaan"):
                if t_in and k_in > 0:
                    requests.post(API_URL, data=json.dumps({
                        "ticker": t_in, "inleg": i_in, "koers": k_in, "type": p_type_value
                    }))
                    st.rerun()

with tab1:
    render_portfolio(growth_active, "Growth", "Growth")

with tab2:
    render_portfolio(div_active, "Dividend", "Dividend")

with tab3:
    st.subheader("Gesloten Trades")
    st.dataframe(df_log, use_container_width=True, hide_index=True)

# --- DEBUG CHECK (Alleen zichtbaar als Dividend leeg blijft) ---
if div_active.empty and not df_active.empty:
    with st.sidebar:
        st.write("### 🛠 Debug Hulp")
        st.write("Gevonden types in Sheet:")

        st.write(df_active['Type'].unique())

