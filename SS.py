import streamlit as st
import yfinance as yf
import pandas as pd
import smtplib
from email.mime.text import MIMEText


def stuur_alert_mail(ticker, rsi, advies):
    # Jouw gegevens (gebruik een 'App Password' als je Gmail gebruikt!)
    afzender = "jouw-email@gmail.com"
    ontvanger = "jouw-email@gmail.com"
    wachtwoord = "abcd efgh ijkl mnop" # Dit is een App Password, niet je normale wachtwoord

    onderwerp = f"🚨 BEURS ALERT: {ticker} is {advies}!"
    bericht = f"De scanner heeft een actie gevonden voor {ticker}.\n\nRSI: {rsi:.2f}\nAdvies: {advies}\n\nCheck je Trading 212 app!"

    msg = MIMEText(bericht)
    msg['Subject'] = onderwerp
    msg['From'] = afzender
    msg['To'] = ontvanger

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(afzender, wachtwoord)
            server.sendmail(afzender, ontvanger, msg.as_string())
        return True
    except Exception as e:
        print(f"Fout bij mailen: {e}")
        return False

st.set_page_config(page_title="Ultimate Score Scanner", layout="wide")
st.title("🏆 Beste Kansen: RSI + Dividend Score")

# Je lijst met aandelen
watchlist = ["ASML.AS", "AAPL", "MSFT", "NVDA", "TSLA", "SHELL.AS", "KO", "ABBV", "PEP", "INTC"]

def scan_aandeel(ticker_symbol):
    t = yf.Ticker(ticker_symbol)
    hist = t.history(period="1y")
    
    # 1. RSI Berekening
    delta = hist['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    huidige_rsi = rsi.iloc[-1]
    
    # 2. Dividend Yield ophalen
    div_yield = t.info.get('dividendYield', 0)
    if div_yield is None: div_yield = 0
    yield_perc = div_yield * 100
    
    # 3. DE SCORE BEREKENING (Onze eigen logica)
    # Lage RSI is goed (punten = 100 - RSI)
    # Hoog dividend is goed (we tellen yield * 5 erbij op als bonus)
    score = (100 - huidige_rsi) + (yield_perc * 5)
    
    return {
        "Ticker": ticker_symbol,
        "Prijs": round(hist['Close'].iloc[-1], 2),
        "RSI": round(huidige_rsi, 1),
        "Dividend": f"{yield_perc:.2f}%",
        "Kansen-Score": round(score, 1)
    }

if st.button("Bereken Beste Kansen"):
    results = []
    progress_bar = st.progress(0)
    
    for i, s in enumerate(watchlist):
        try:
            data = scan_aandeel(s)
            results.append(data)
        except Exception as e:
            st.warning(f"Kon {s} niet laden. Check of de ticker klopt.")
        progress_bar.progress((i + 1) / len(watchlist))
    
    # CHECK: Hebben we wel data?
    if len(results) > 0:
        df = pd.DataFrame(results)
        
        # Dubbelcheck of de kolom echt bestaat voor we sorteren
        if "Kansen-Score" in df.columns:
            df_final = df.sort_values(by="Kansen-Score", ascending=False)
            st.subheader("Top Resultaten")
            st.dataframe(df_final.style.background_gradient(subset=['Kansen-Score'], cmap='YlGn'))
            
            top_ticker = df_final.iloc[0]['Ticker']
            st.success(f"🎯 Volgens de scan is **{top_ticker}** momenteel de meest interessante optie.")
        else:
            st.error("Kolom 'Kansen-Score' ontbreekt. Er gaat iets mis in de scan_aandeel functie.")
            # --- SECTIE 2: PORTFOLIO MONITOR ---
st.divider()
st.header("📈 Portfolio Monitor")
st.write("Vul hier de tickers in die je al bezit om te zien of het tijd is om te verkopen.")

# Invoerveld voor je eigen aandelen
mijn_portefeuille = st.text_input("Mijn aandelen (tickers gescheiden door komma's)", "ASML.AS, KO, AAPL")
tickers_eigen = [t.strip().upper() for t in mijn_portefeuille.split(",")]

if st.button("Check mijn Portefeuille"):
    port_results = []
    for s in tickers_eigen:
        try:
            # We gebruiken dezelfde scan_aandeel functie
            res = scan_aandeel(s)
            
            # Bepaal het advies op basis van RSI
            if res['RSI'] > 70:
                res['Advies'] = "⚠️ VERKOPEN (Winst pakken)"
                res['Kleur'] = "background-color: #ff4b4b" # Rood
            elif res['RSI'] < 35:
                res['Advies'] = "💎 BIJKOPEN (Ondergewaardeerd)"
                res['Kleur'] = "background-color: #28a745" # Groen
            else:
                res['Advies'] = "✅ VASTHOUDEN (Stabiel)"
                res['Kleur'] = ""
            
            port_results.append(res)
        except:
            st.error(f"Kon data voor {s} niet ophalen.")

    if port_results:
        df_port = pd.DataFrame(port_results)
       
from email.mime.text import MIMEText
import streamlit as st

def stuur_alert_mail(ticker, rsi, advies):
    try:
        # Haal gegevens veilig uit de Streamlit Cloud instellingen
        afzender = st.secrets["email"]["user"]
        wachtwoord = st.secrets["email"]["password"]
        ontvanger = st.secrets["email"]["receiver"]

        onderwerp = f"🚨 BEURS ALERT: {ticker} is {advies}!"
        bericht = f"Actie vereist voor {ticker}.\n\nStatus: {advies}\nRSI: {rsi:.2f}\n\nCheck je Trading 212 app!"

        msg = MIMEText(bericht)
        msg['Subject'] = onderwerp
        msg['From'] = afzender
        msg['To'] = ontvanger

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login(afzender, wachtwoord)
            server.sendmail(afzender, ontvanger, msg.as_string())
        return True
    except Exception as e:
        st.error(f"E-mail versturen mislukt: {e}")
        return False

# In je scan-loop (bij het berekenen van de resultaten):
# if data['RSI'] < 30:
#     stuur_alert_mail(s, data['RSI'], "KOOPKANS")
# elif data['RSI'] > 70:
#     stuur_alert_mail(s, data['RSI'], "VERKOOPKANS")
        
        # We printen de kolomnamen even in je app (alleen voor debuggen, mag later weg)
        # st.write("Beschikbare kolommen:", df_port.columns.tolist())

        # Selecteer alleen kolommen die daadwerkelijk bestaan om de error te voorkomen
        kolommen_om_te_tonen = ['Ticker', 'Prijs', 'RSI', 'Advies'] 
        # Check welke van deze kolommen echt in de df zitten
        bestaande_kolommen = [c for c in kolommen_om_te_tonen if c in df_port.columns]
        
        if bestaande_kolommen:
            # Gebruik de kolommen die we gevonden hebben
            st.table(df_port[bestaande_kolommen])
        else:
            st.error("De monitor kon de juiste gegevens niet vinden in de scan.")
            st.write(df_port) # Toon alles zodat je ziet wat er wél is
            



