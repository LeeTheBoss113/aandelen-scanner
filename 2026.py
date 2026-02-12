import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
from datetime import datetime

# --- CONFIG ---
AIRTABLE_TOKEN = "patCdgzOgVDPNlGCw.3008de99d994972e122dc62031b3f5aa5f2647cfa75c5ac67215dc72eba2ce07"
BASE_ID = "appgvzDsvbvKi7e45"
PORTFOLIO_TABLE = "Portfolio"
LOG_TABLE = "Logboek"

HEADERS = {"Authorization": f"Bearer {AIRTABLE_TOKEN}", "Content-Type": "application/json"}

st.set_page_config(layout="wide", page_title="Trader Dashboard 2026", initial_sidebar_state="expanded")

# --- DATA FUNCTIES ---
def get_airtable_data(table_name):
    try:
        url = f"https://api.airtable.com/v0/{BASE_ID}/{table_name}"
        r = requests.get(url, headers=HEADERS, timeout=10)
        if r.status_code == 200:
            records = r.json().get('records', [])
            rows = []
            for rec in records:
                row = rec['fields']
                row['airtable_id'] = rec['id']
                rows.append(row)
            return pd.DataFrame(rows)
        return pd.DataFrame()
    except:
        return pd.DataFrame()

def sell_position(row, current_price):
    try:
        # 1. Berekeningen
        aantal = row['Inleg'] / row['Koers'] if row['Koers'] > 0 else 0
        verkoopwaarde = aantal * current_price
        winst_eur = verkoopwaarde - row['Inleg']
        rendement = (winst_eur / row['Inleg'] * 100) if row['Inleg'] > 0 else 0
        
        # 2. Data voorbereiden (alles expliciet naar juiste type omzetten)
        log_payload = {
            "fields": {
                "Ticker": str(row['Ticker']).upper(),
                "Inleg": float(row['Inleg']),
                "Verkoopwaarde": round(float(verkoopwaarde), 2),
                "Winst_Euro": round(float(winst_eur), 2),
                "Rendement_Perc": round(float(rendement), 2),
                "Type": str(row.get('Type', 'Growth')),
                "Datum": datetime.now().isoformat()
            }
        }
        
        # 3. Schrijven naar Logboek
        log_url = f"https://api.airtable.com/v0/{BASE_ID}/{LOG_TABLE}"
        res = requests.post(log_url, headers=HEADERS, json=log_payload)
        
        if res.status_code == 200:
            # 4. Alleen bij succes verwijderen uit Portfolio
            del_url = f"https://api.airtable.com/v0/{BASE_ID}/{PORTFOLIO_TABLE}/{row['airtable_id']}"
            del_res = requests.delete(del_url, headers=HEADERS)
            if del_res.status_code == 200:
                return True
            else:
                st.error(f"Logboek gelukt, maar kon niet verwijderen uit Portfolio: {del_res.text}")
        else:
            # DIT LAAT ZIEN WAT ER MIS IS MET JE KOLOMMEN
            st.error(f"Airtable Logboek fout: {res.status_code} - {res.text}")
            return False
            
    except Exception as e:
        st.error(f"Fout in verkoop-logica: {e}")
        return False
# --- UI START ---
st.title("🏹 Trading Center 2026")

df_p = get_airtable_data(PORTFOLIO_TABLE)
df_l = get_airtable_data(LOG_TABLE)

# TABS VOOR DE TWEE STRATEGIEËN
tab_growth, tab_div, tab_log = st.tabs(["🚀 Daytrade / Growth", "💎 Dividend Portfolio", "📜 Historisch Logboek"])

def render_portfolio_section(data, strategy_name):
    if data.empty:
        st.info(f"Geen actieve {strategy_name} posities.")
        return

    subset = data[data['Type'] == strategy_name] if 'Type' in data.columns else pd.DataFrame()
    
    if subset.empty:
        st.info(f"Geen actieve {strategy_name} posities.")
        return

    # Metrics berekenen
    total_inleg = 0
    total_waarde = 0
    
    for _, row in subset.iterrows():
        ticker = str(row['Ticker']).upper()
        try:
            t = yf.Ticker(ticker)
            cur_price = t.history(period="1d")['Close'].iloc[-1]
            aantal = row['Inleg'] / row['Koers']
            waarde = aantal * cur_price
            winst = waarde - row['Inleg']
            perc = (winst / row['Inleg'] * 100)
            
            total_inleg += row['Inleg']
            total_waarde += waarde

            with st.expander(f"{ticker} | Winst: €{winst:.2f} ({perc:.2f}%)", expanded=True):
                c1, c2, c3, c4 = st.columns([2, 2, 2, 1])
                c1.metric("Inleg", f"€{row['Inleg']:.2f}")
                c2.metric("Huidige Waarde", f"€{waarde:.2f}")
                c3.metric("Huidige Koers", f"€{cur_price:.2f}")
                if c4.button("⚡ Verkoop", key=f"sell_{strategy_name}_{row['airtable_id']}"):
                    if sell_position(row, cur_price):
                        st.success("Verkocht!")
                        time.sleep(0.5)
                        st.rerun()
        except:
            st.error(f"Kon data voor {ticker} niet laden.")

    st.sidebar.markdown(f"### 📊 Totalen {strategy_name}")
    st.sidebar.write(f"Inleg: €{total_inleg:.2f}")
    st.sidebar.write(f"Winst: €{total_waarde - total_inleg:.2f}")

with tab_growth:
    st.header("Snelgroeiende & Daytrade Posities")
    render_portfolio_section(df_p, "Growth")

with tab_div:
    st.header("Lange Termijn Dividend")
    render_portfolio_section(df_p, "Dividend")

with tab_log:
    st.header("📜 Gerealiseerde Resultaten")
    if not df_l.empty:
        strat_filter = st.selectbox("Filter op type", ["Alles", "Growth", "Dividend"])
        log_display = df_l.copy()
        
        if strat_filter != "Alles":
            # Alleen filteren als de kolom 'Type' bestaat
            if 'Type' in log_display.columns:
                log_display = log_display[log_display['Type'] == strat_filter]
        
        cols = ['Ticker', 'Inleg', 'Verkoopwaarde', 'Winst_Euro', 'Rendement_Perc', 'Type', 'Datum']
        existing_cols = [c for c in cols if c in log_display.columns]
        
        # VEILIG SORTEREN: Check of 'Datum' in de kolommen zit
        if 'Datum' in log_display.columns:
            log_display = log_display.sort_values(by='Datum', ascending=False)
        
        if not log_display.empty:
            st.dataframe(log_display[existing_cols], use_container_width=True, hide_index=True)
        else:
            st.info(f"Geen resultaten gevonden voor {strat_filter}.")
    else:
        st.info("Logboek is nog leeg. Verkoop een aandeel om de historie te starten.")

# --- SIDEBAR TOEVOEGEN ---
with st.sidebar:
    st.header("➕ Nieuwe Aankoop")
    with st.form("add_form"):
        t = st.text_input("Ticker").upper()
        i = st.number_input("Inleg (€)", 100)
        k = st.number_input("Koers", 0.01)
        s = st.selectbox("Type", ["Growth", "Dividend"])
        if st.form_submit_button("Toevoegen"):
            requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{PORTFOLIO_TABLE}", headers=HEADERS, 
                          json={"fields": {"Ticker": t, "Inleg": i, "Koers": k, "Type": s}})

            st.rerun()

