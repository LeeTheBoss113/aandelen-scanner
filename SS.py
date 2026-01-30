# --- KOLOM 2: ACTIE-CENTRUM MET LIVE MAIL ALERTS ---
with c2:
    st.header("⚡ Signalen")
    
    # 1. BUY ALERTS + MAIL
    st.subheader("💎 Buy")
    buys = [r for r in results if r['Score'] >= 85]
    if buys:
        for b in buys: 
            st.success(f"**{b['Ticker']}** (Score: {b['Score']})")
            # Trigger mail bij zeer hoge score
            if b['Score'] >= 90:
                verstuurd = stuur_alert_mail(b['Ticker'], b['Score'], b['RSI'], type="KOOP")
                if verstuurd: st.caption(f"📧 Koop-alert verzonden voor {b['Ticker']}")
    else: 
        st.info("Geen koopkansen")

    st.divider()

    # 2. SELL ALERTS + MAIL
    st.subheader("🔥 Sell")
    port_input = st.text_input("Mijn Bezit:", "KO, ASML.AS", key="p_in")
    p_tickers = [t.strip().upper() for t in port_input.split(",")]
    p_res = [scan_aandeel(t) for t in p_tickers if scan_aandeel(t)]
    
    if p_res:
        sells = [r for r in p_res if r['RSI'] >= 70]
        if sells:
            for s in sells: 
                st.warning(f"**{s['Ticker']}** (RSI: {s['RSI']})")
                # Trigger mail bij oververhitting
                if s['RSI'] >= 75:
                    verstuurd = stuur_alert_mail(s['Ticker'], "N.V.T.", s['RSI'], type="VERKOOP")
                    if verstuurd: st.caption(f"📧 Verkoop-alert verzonden voor {s['Ticker']}")
        else: 
            st.write("Geen verkoop nodig")
