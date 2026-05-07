import streamlit as st
import pandas as pd
import yagmail
import random
import time
from datetime import datetime, timedelta
from extra_streamlit_components import CookieManager
from st_supabase_connection import SupabaseConnection
import streamlit.components.v1 as components

def detect_browser_details():
    """
    Dumps all relevant browser attributes to find a reliable standalone signature.
    """
    js_code = """
    <script>
    function getDetails() {
        const details = {
            isiOSStandalone: window.navigator.standalone === true,
            isDisplayStandalone: window.matchMedia('(display-mode: standalone)').matches,
            isFullScreen: window.matchMedia('(display-mode: fullscreen)').matches,
            menubarVisible: window.menubar.visible,
            userAgent: navigator.userAgent,
            screenWidth: window.screen.width,
            screenHeight: window.screen.height,
            isMobile: /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)
        };
        
        // Final logic: True standalone apps usually have menubar hidden 
        // OR the specific OS standalone flags set.
        const standaloneScore = (details.isiOSStandalone || details.isDisplayStandalone) && !details.menubarVisible;

        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: { status: standaloneScore, raw: details }
        }, '*');
    }
    getDetails();
    setTimeout(getDetails, 500);
    </script>
    """
    return components.html(js_code, height=0, width=0)

def check_login():
    cookie_manager = CookieManager()
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    conn = st.connection("supabase", type=SupabaseConnection)

    # 1. Cookie Handshake
    cookies = cookie_manager.get_all()
    if cookies is None:
        with st.spinner("Connecting to Swift Data Solutions..."):
            st.stop()

    # 2. Advanced Detection
    browser_data = detect_browser_details()
    
    if browser_data is None:
        if "handshake_done" not in st.session_state:
            time.sleep(0.5)
            st.session_state.handshake_done = True
            st.rerun()
    
    # Safely parse the return object
    is_standalone = False
    raw_details = {}
    if browser_data:
        is_standalone = browser_data.get("status", False)
        raw_details = browser_data.get("raw", {})

    # 3. Check for existing Cookie
    saved_code = cookies.get("qsc_beer_code")
    if saved_code and not st.session_state.logged_in:
        res = conn.table("users").select("*").eq("token", str(saved_code)).execute()
        if res.data:
            st.session_state.user_info = res.data[0]
            st.session_state.logged_in = True
            return st.session_state.user_info

    # 4. UI Logic
    if not st.session_state.logged_in:
        st.title("🍺 QSC Beer Tracker")
        
        # --- THE DBA INSPECTION PANEL ---
        with st.expander("🛠️ Browser Fingerprint (Debug Info)"):
            st.write("**Reported Standalone:**", is_standalone)
            st.json(raw_details) # This tells us exactly what the browser sees
            override = st.toggle("Force Login Form (PC Testing)")
            if st.button("Hard Reset Session"):
                st.session_state.clear()
                st.rerun()
        
        show_login = is_standalone or override

        if not show_login:
            st.info("### 📱 Installation Required")
            st.write("To use this app, please add it to your home screen first.")
            st.markdown("1. Tap **Share** or **Menu**\n2. Select **'Add to Home Screen'**")
            st.stop()

        # --- LOGIN FORM ---
        st.success("✅ App Mode Active")
        email_input = st.text_input("Enter your email").strip().lower()
        
        if "show_code_input" not in st.session_state:
            st.session_state.show_code_input = False

        if not st.session_state.show_code_input:
            if st.button("Verify Email"):
                if email_input:
                    res = conn.table("users").select("*").eq("email", email_input).execute()
                    if res.data:
                        user = res.data[0]
                        code = user.get('token')
                        if not code or len(str(code)) != 6:
                            code = str(random.randint(100000, 999999))
                            conn.table("users").update({"token": code}).eq("email", email_input).execute()

                        try:
                            yag = yagmail.SMTP("justin.moulton@gmail.com", "ocsr ngmx wzla uwau")
                            yag.send(to=email_input, subject="Beer Tracker Code", contents=f"Your code: {code}")
                            st.success("Code sent!")
                            st.session_state.show_code_input = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Email failed: {e}")
                    else:
                        st.error("Email not found.")
        else:
            code_in = st.text_input("6-Digit Code")
            if st.button("Confirm"):
                res = conn.table("users").select("*").eq("email", email_input).eq("token", code_in).execute()
                if res.data:
                    st.session_state.user_info = res.data[0]
                    st.session_state.logged_in = True
                    
                    # FIX: Explicitly cast to datetime to satisfy .isoformat() requirement
                    # Use a fixed variable name to ensure no scope issues
                    exp_date = datetime.now() + timedelta(days=90)
                    cookie_manager.set("qsc_beer_code", str(code_in), expires_at=exp_date)
                    
                    st.rerun()
                else:
                    st.error("Invalid code.")
            
            if st.button("Back"):
                st.session_state.show_code_input = False
                st.rerun()

    if st.session_state.logged_in:
        return st.session_state.user_info
    st.stop()
