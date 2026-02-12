import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import json
import time

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="Pure Strategy Scanner 2026")
API_URL = "https://script.google.com/macros/s/AKfycbz-4mkyZJISTvixd3JsNHIj9ja3N9824MEHIBsoIZgd_tkx2fM6Yc5ota6kW4WjRKO_/exec"

# --- DATA LADEN ---
def get_clean_data():
    try:
        r = requests.get(f"{API_URL}?t={int(time.time())}").json()
        active_raw = r.get('active', [])
        log_raw = r.get('log', [])
        
        # Maak DataFrames en dwing kolommen af
        df_a = pd.DataFrame(active_raw[1:], columns=["Ticker", "Inleg", "Koers", "Type"]) if len(active_raw) > 1 else pd.DataFrame(columns=["Ticker", "Inleg", "Koers", "Type"])
        df_l = pd.DataFrame(log_raw[1:], columns=["Datum", "Ticker", "Inleg", "Winst", "Type"]) if len(log_raw) > 1 else pd.DataFrame(columns=["Datum", "Ticker", "Inleg", "Winst", "Type"])
        
        # Getallen forceren
        for df in [df_a, df_l]:
            for col in ['Inleg', 'Koers', 'Winst']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df_a, df_l
    except:
        return pd.DataFrame(columns=["Ticker", "Inleg", "Koers", "Type"]), pd.DataFrame()

# --- INTERFACE ---
st.title("⚡ Strategy Dashboard Pro")
df_active, df_log = get_clean_data()

# Splits data in de app (zuivere methode)
growth_active = df_active[df_active['Type'] == 'Growth']
div_active = df_active[df_active['Type'] == 'Dividend']

t1, t2 = st.tabs(["🚀 Growth", "🛡️ Dividend"])

def show_portfolio(df, p_type):
    st.subheader(f"Actieve {p_type} Posities")
    if not df.empty:
        st.dataframe(df, use_container_width=True, hide_index=True)
        # Verkoop knop logica hier...
    else:
        st.info("Geen posities.")

    with st.expander(f"➕ Nieuwe {p_type} toevoegen"):
        with st.form(f"add_{p_type}"):
            tick = st.text_input("Ticker").upper()
            inl = st.number_input("Inleg", 100)
            krs = st.number_input("Koers", 0.0)
            if st.form_submit_button("Opslaan"):
                requests.post(API_URL, data=json.dumps({"ticker":tick, "inleg":inl, "koers":krs, "type":p_type}))
                st.rerun()

with t1: show_portfolio(growth_active, "Growth")
with t2: show_portfolio(div_active, "Dividend")