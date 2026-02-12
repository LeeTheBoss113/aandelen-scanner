import streamlit as st
import pandas as pd
import yfinance as yf
import requests
import time
from datetime import datetime

# --- CONFIG ---
# Vul hier je eigen gegevens in
AIRTABLE_TOKEN = "patCdgzOgVDPNlGCw.3008de99d994972e122dc62031b3f5aa5f2647cfa75c5ac67215dc72eba2ce07"
BASE_ID = "appgvzDsvbvKi7e45"
PORTFOLIO_TABLE = "Portfolio"
LOG_TABLE = "Logboek"

HEADERS = {
    "Authorization": f"Bearer {AIRTABLE_TOKEN}",
    "Content-Type": "application/json"
}

st.set_page_config(layout="wide", page_title="Professional Portfolio Manager 2026")

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
        else:
            st.error(f"Fout bij ophalen {table_name}: {r.text}")
            return pd.DataFrame()
    except Exception as e:
        st.error(f"Verbindingsfout: {e}")
        return pd.DataFrame()

def sell_position(row, current_price):
    # 1. Berekeningen
    aantal = row['Inleg'] / row['Koers'] if row['Koers'] > 0 else 0
    verkoopwaarde = aantal * current_price
    winst_eur = verkoopwaarde - row['Inleg']
    rendement = (winst_eur / row['Inleg'] * 100) if row['Inleg'] > 0 else 0
    
    # 2. Opslaan in Logboek
    log_url = f"https://api.airtable.com/v0/{BASE_ID}/{LOG_TABLE}"
    log_payload = {
        "fields": {
            "Ticker": str(row['Ticker']).upper(),
            "Inleg": float(row['Inleg']),
            "Verkoopwarde": round(float(verkoopwaarde), 2), # Let op: check spelling in Airtable!
            "Winst_Euro": round(float(winst_eur), 2),
            "Rendement_Perc": round(float(rendement), 2),
            "Datum": datetime.now().isoformat()
        }
    }
    res_log = requests.post(log_url, headers=HEADERS, json=log_payload)
    
    if res_log.status_code == 200:
        # 3. Alleen verwijderen uit Portfolio als Logboek is gelukt
        del_url = f"https://api.airtable.com/v0/{BASE_ID}/{PORTFOLIO_TABLE}/{row['airtable_id']}"
        requests.delete(del_url, headers=HEADERS)
        return True
    return False

# --- UI HEADER ---
st.title("💼 Portfolio Manager & Strategisch Logboek")
st.write(f"Vandaag: {datetime.now().strftime('%d-%m-%Y')}")

# --- PORTFOLIO SECTIE ---
df_p = get_airtable_data(PORTFOLIO_TABLE)

if not df_p.empty:
    # Verwijder rijen zonder Ticker of Inleg om crashes te voorkomen
    df_p = df_p.dropna(subset=['Ticker', 'Inleg', 'Koers'])
    
    st.subheader("📊 Actieve Posities")
    
    total_inleg = 0
    total_waarde = 0

    for _, row in df_p.iterrows():
        ticker_str = str(row['Ticker']).strip().upper()
        if not ticker_str: continue

        try:
            # Haal koers op
            t = yf.Ticker(ticker_str)
            hist = t.history(period="1d")
            if hist.empty:
                st.warning(f"Geen data voor {ticker_str}")
                continue
                
            cur_price = hist['Close'].iloc[-1]
            aantal = row['Inleg'] / row['Koers']
            waarde = aantal * cur_price
            winst = waarde - row['Inleg']
            perc = (winst / row['Inleg'] * 100)
            
            total_inleg += row['Inleg']
            total_waarde += waarde

            # Visuele weergave per aandeel
            with st.container():
                c1, c2, c3, c4, c5 = st.columns([1, 1, 1, 1, 1])
                c1.markdown(f"### {ticker_str}")
                c2.metric("Inleg", f"€{row['Inleg']:.2f}")
                
                # Kleur van winst bepalen
                color = "green" if winst >= 0 else "red"
                c3.markdown(f"**Winst/Verlies**\n\n<span style='color:{color}'>€{winst:.2f} ({perc:.2f}%)</span>", unsafe_allow_html=True)
                
                c4.metric("Huidige Koers", f"€{cur_price:.2f}")
                
                # Unieke knop met Ticker + Airtable ID
                if c5.button("Verkopen 💰", key=f"btn_{ticker_str}_{row['airtable_id']}"):
                    if sell_position(row, cur_price):
                        st.success(f"{ticker_str} succesvol verkocht!")
                        time.sleep(1)
                        st.rerun()
                st.divider()
        except Exception as e:
            st.error(f"Fout bij {ticker_str}: {e}")

    # Dashboard Metrics
    st.sidebar.markdown("---")
    st.sidebar.subheader("Totaal Overzicht")
    st.sidebar.metric("Totale Inleg", f"€{total_inleg:.2f}")
    st.sidebar.metric("Huidige Waarde", f"€{total_waarde:.2f}")
    st.sidebar.metric("Netto Resultaat", f"€{total_waarde - total_inleg:.2f}")

else:
    st.info("Je portfolio is momenteel leeg.")

# --- LOGBOEK SECTIE ---
st.divider()
st.subheader("📜 Gerealiseerde Resultaten (Logboek)")
df_l = get_airtable_data(LOG_TABLE)

# Controleer of de tabel niet leeg is EN of de cruciale kolommen bestaan
required_columns = ['Ticker', 'Inleg', 'Verkoopwaarde', 'Winst_Euro', 'Rendement_Perc', 'Datum']

if not df_l.empty and all(col in df_l.columns for col in required_columns):
    # Tabel netjes tonen
    df_l_clean = df_l[required_columns].copy()
    df_l_clean = df_l_clean.sort_values(by='Datum', ascending=False)
    st.dataframe(df_l_clean, use_container_width=True, hide_index=True)
    
    totaal_winst = df_l_clean['Winst_Euro'].sum()
    st.success(f"Totaal verdiend met gesloten trades: **€{totaal_winst:.2f}**")
else:
    st.info("Het logboek is nog leeg. Zodra je een aandeel verkoopt, verschijnt hier de historie.")

# --- TOEVOEGEN FORMULIER ---
with st.sidebar:
    st.header("➕ Nieuwe Aankoop")
    with st.form("add_form", clear_on_submit=True):
        new_t = st.text_input("Ticker (bv. ASML.AS)").upper()
        new_i = st.number_input("Inleg (€)", min_value=1.0)
        new_k = st.number_input("Aankoopkoers", min_value=0.01)
        new_s = st.selectbox("Strategie", ["Growth", "Dividend"])
        
        if st.form_submit_button("Toevoegen aan Portfolio"):
            if new_t:
                payload = {"fields": {"Ticker": new_t, "Inleg": new_i, "Koers": new_k, "Type": new_s}}
                res = requests.post(f"https://api.airtable.com/v0/{BASE_ID}/{PORTFOLIO_TABLE}", headers=HEADERS, json=payload)
                if res.status_code == 200:
                    st.success("Toegevoegd!")
                    time.sleep(1)
                    st.rerun()
                else:

                    st.error("Fout bij opslaan.")
