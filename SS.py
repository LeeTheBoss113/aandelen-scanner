# --- KOLOM 1: SCANNER ---
with c1:
    st.header("🔍 Scanner")
    watch_input = st.text_input("Watchlist (tickers met komma):", "ASML.AS, KO, PG, JNJ, O, ABBV, SHEL.AS, MO", key="w1")
    
    if watch_input:
        tickers = [t.strip().upper() for t in watch_input.split(",") if t.strip()]
        
        with st.spinner('Data ophalen...'):
            results = []
            for t in tickers:
                data = scan_aandeel(t)
                if data:
                    results.append(data)
            
            if results:
                df_all = pd.DataFrame(results).sort_values(by="Score", ascending=False)
                st.dataframe(df_all[['Ticker', 'RSI', 'Div %', 'Score']].style.background_gradient(cmap='RdYlGn', subset=['Score']), use_container_width=True)
            else:
                st.error("Geen data gevonden. Check of de tickers correct zijn (bijv. ASML.AS).")
    else:
        st.warning("Vul tickers in om te scannen.")

# --- KOLOM 2: SIGNALEER-CENTRUM ---
with c2:
    st.header("⚡ Signalen")
    
    # Gebruik de results van kolom 1
    if 'results' in locals() and results:
        buys = [r for r in results if r['Score'] >= 85]
        if buys:
            for b in buys:
                st.success(f"**KOOP: {b['Ticker']}** (Score: {b['Score']})")
                if b['Score'] >= 90:
                    if stuur_alert_mail(b['Ticker'], b['Score'], b['RSI'], "KOOP"):
                        st.toast(f"Mail verzonden voor {b['Ticker']}!")
        else:
            st.info("Geen koop-signalen.")
    
    st.divider()

    st.subheader("🔥 Sell")
    port_input = st.text_input("Mijn Bezit:", "KO, ASML.AS", key="p_in")
    
    if port_input:
        p_tickers = [t.strip().upper() for t in port_input.split(",") if t.strip()]
        with st.spinner('Portfolio scannen...'):
            p_res = []
            for pt in p_tickers:
                p_data = scan_aandeel(pt)
                if p_data:
                    p_res.append(p_data)
            
            if p_res:
                sells = [r for r in p_res if r['RSI'] >= 70]
                if sells:
                    for s in sells:
                        st.warning(f"**VERKOOP: {s['Ticker']}** (RSI: {s['RSI']})")
                        if s['RSI'] >= 75:
                            if stuur_alert_mail(s['Ticker'], "N.V.T.", s['RSI'], "VERKOOP"):
                                st.toast(f"Verkoop-alert verzonden!")
                else:
                    st.write("Geen verkoop nodig.")
