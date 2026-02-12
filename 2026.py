import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
from datetime import datetime

# --- CONFIG ---
AIRTABLE_TOKEN = "patCdgzOgVDPNlGCw.3008de99d994972e122dc62031b3f5aa5f2647cfa75c5ac67215dc72eba2ce07"
BASE_ID = "appgvzDsvbvKi7e45"
TABLE_NAME = "Portfolio"
LOG_TABLE = "Logboek"

HEADERS = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}

st.set_page_config(layout="wide", page_title="Portfolio & Exit Strategy")

# --- DATA FUNCTIES ---
def get_airtable_data(table_name):
    url = f"https://api.airtable.com/v0/{BASE_ID}/{table_name}"
    r = requests.get(url, headers=HEADERS).json()
    records = r.get('records', [])
    rows = []
    for r in records:
        row = r['fields']
        row['airtable_id'] = r['id']
        rows.append(row)
    return pd.DataFrame(rows)

def sell_position(row, current_price):
    # 1. Berekeningen
    aantal = row['Inleg'] / row['Koers']
    verkoopwaarde = aantal * current_price
    winst_eur = verkoopwaarde - row['Inleg']
    rendement = (winst_eur / row['Inleg'] * 100) if row['Inleg'] > 0 else 0
    
    # 2. Opslaan in Logboek
    log_url = f"https://api.airtable.com/v0/{BASE_ID}/{LOG_TABLE}"
    log_payload = {
        "fields": {
            "Ticker": row['Ticker'],
            "Inleg": row['Inleg'],
            "Verkoopwaarde": round(verkoopwaarde, 2),
            "Winst_Euro": round(winst_eur, 2),
            "Rendement_Perc": round(rendement, 2),
            "Datum": datetime.now().isoformat()
        }
    }
    requests.post(log_url, headers=HEADERS, json=log_payload)
    
    # 3. Verwijderen uit Portfolio
    del_url = f"https://api.airtable.com/v0/{BASE_ID}/{PORTFOLIO_TABLE}/{row['airtable_id']}"
    requests.delete(del_url, headers=HEADERS)

# --- UI ---
st.title("💼 Portfolio Manager & Logboek")

df_p = get_airtable_data(PORTFOLIO_TABLE)

# --- PORTFOLIO SECTIE ---
if not df_p.empty:
    st.subheader("Actieve Posities")
    display_list = []
    for _, row in df_p.iterrows():
        t = yf.Ticker(row['Ticker'])
        cur_price = t.history(period="1d")['Close'].iloc[-1]
        
        aantal = row['Inleg'] / row['Koers']
        huidige_waarde = aantal * cur_price
        winst = huidige_waarde - row['Inleg']
        
        col1, col2, col3, col4, col5 = st.columns([1,1,1,1,1])
        col1.write(f"**{row['Ticker']}**")
        col2.write(f"Inleg: €{row['Inleg']:.2f}")
        col3.write(f"Winst: €{winst:.2f}")
        
        # De Verkoop Knop
        if col5.button("Verkopen 💰", key=f"sell_{row['Ticker']}"):
            sell_position(row, cur_price)
            st.success(f"{row['Ticker']} verkocht voor €{cur_price:.2f}!")
            time.sleep(1)
            st.rerun()
        st.divider()

# --- LOGBOEK SECTIE ---
st.subheader("📜 Gerealiseerde Winsten (Logboek)")
df_l = get_airtable_data(LOG_TABLE)
if not df_l.empty:
    st.dataframe(df_l[['Ticker', 'Winst_Euro', 'Rendement_Perc', 'Datum']], use_container_width=True)
    st.metric("Totaal Gerealiseerd", f"€{df_l['Winst_Euro'].sum():.2f}")