import streamlit as st
import pandas as pd
import yfinance as yf
import pandas_ta as ta
import requests
import json
import time

# --- CONFIG ---
st.set_page_config(layout="wide", page_title="Scanner 2026")

# De link naar je nieuwe Google Script implementatie
API_URL = "https://script.google.com/macros/s/AKfycbz-4mkyZJISTvixd3JsNHIj9ja3N9824MEHIBsoIZgd_tkx2fM6Yc5ota6kW4WjRKO_/exec"

# --- DATA OPHALEN ---
def get_data():
    try:
        # We voegen een timestamp toe om caching te voorkomen
        r = requests.get(f"{API_URL}?t={int(time.time())}", timeout=10).json()
        
        def clean(raw_data, fallback_cols):
            if not raw_data or len(raw_data) <= 1:
                return pd.DataFrame(columns=fallback_cols)
            
            # We forceren de kolommen op basis van POSITIE voor maximale stabiliteit
            df = pd.DataFrame(raw_data[1:])
            
            # Als de sheet minder kolommen heeft dan verwacht, vul aan met leegte
            while len(df.columns) < len(fallback_cols):
                df[len(df.columns)] = ""
                
            df = df.iloc[:, :len(fallback_cols)]
            df.columns = fallback_cols
            
            # Zet getallen om
            for col in ['Inleg', 'Koers', 'Winst']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
            
            # Ticker opschonen
            df['Ticker'] = df['Ticker'].astype(str).str.strip().upper()
            return df[df['Ticker'] != ""]

        df_a = clean(r.get('active', []), ["Ticker", "Inleg", "Koers", "Type"])
        df_l = clean(r.get('log', []), ["Datum", "Ticker", "Inleg", "Winst", "Type"])
        return df_a, df_l
    except Exception as e:
        st.error(f"Fout bij verbinden met Google: {e}")
        return pd.DataFrame(columns=["Ticker", "Inleg", "Koers", "Type"]), pd.DataFrame()

# --- INITIALISATIE ---
df_active, df_log = get_data()

st.title("🚀 Dual-Strategy Dashboard")

# DEBUG OPTIE (Zet dit uit als alles werkt)
if st.sidebar.checkbox("Laat ruwe data zien"):
    st.write("Data uit Google Sheets:", df_active)

# Strategieën splitsen
# We maken het "case-insensitive" voor de zekerheid
growth_active = df_active[df_active['Type'].astype(str).str.upper() == "GROWTH"]
div_active = df_active[df_active['Type'].astype(str).str.upper() == "DIVIDEND"]

# Als er geen type is ingevuld, laten we die ook zien in een 'Onbekend' tabblad
misc_active = df_active[~df_active['Type'].astype(str).str.upper().isin(["GROWTH", "DIVIDEND"])]

t1, t2, t3, t4 = st.tabs(["📈 Growth", "💎 Dividend", "❓ Ongeclassificeerd", "📜 Logboek"])

def render_portfolio(df, p_type):
    if not df.empty:
        st.subheader(f"Actieve {p_type} posities")
        st.dataframe(df, use_container_width=True, hide_index=True)
        
        sel = st.selectbox("Selecteer aandeel om te sluiten:", [""] + df['Ticker'].tolist(), key=f"sel_{p_type}")
        if st.button("Sluit positie & Log winst", key=f"btn_{p_type}"):
            if sel:
                row = df[df['Ticker'] == sel].iloc[0]
                # Hier de POST call naar Google Script
                requests.post(API_URL, data=json.dumps({
                    "method": "delete",
                    "ticker": sel,
                    "inleg": row['Inleg'],
                    "winst": 0, # In de echte versie bereken je dit op basis van koers
                    "type": p_type
                }))
                st.rerun()
    else:
        st.info(f"Geen {p_type} posities gevonden.")

    with st.expander(f"➕ Nieuwe {p_type} toevoegen"):
        with st.form(f"form_{p_type}"):
            t = st.text_input("Ticker").upper()
            i = st.number_input("Inleg", 100)
            k = st.number_input("Koers", 0.0)
            if st.form_submit_button("Opslaan naar Google Sheet"):
                requests.post(API_URL, data=json.dumps({"ticker":t, "inleg":i, "koers":k, "type":p_type}))
                st.rerun()

with t1: render_portfolio(growth_active, "Growth")
with t2: render_portfolio(div_active, "Dividend")
with t3: 
    if not misc_active.empty:
        st.warning("Deze aandelen hebben geen geldig type (Growth/Dividend) in de Sheet.")
        render_portfolio(misc_active, "Onbekend")
    else:
        st.success("Alle aandelen zijn netjes ingedeeld!")
with t4:
    st.subheader("Laatste verkopen")
    st.dataframe(df_log, use_container_width=True, hide_index=True)