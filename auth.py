import streamlit as st
import pandas as pd
import yagmail
import random
import time
from datetime import datetime, timedelta
from extra_streamlit_components import CookieManager
from st_supabase_connection import SupabaseConnection
import streamlit.components.v1 as components

def detect_standalone():
    """
    Enhanced JS detection. Returns True only if the browser UI is hidden 
    AND it is a mobile device.
    """
    js_code = """
    <script>
    function check() {
        const isiOS = window.navigator.standalone === true;
        const isStandaloneMode = window.matchMedia('(display-mode: standalone)').matches;
        // Strict mobile check
        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        
        // Final Status: Must be in standalone mode AND on a mobile device
        const status = isiOS || (isStandaloneMode && isMobile);
        
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: status
        }, '*');
    }
    check();
    setTimeout(check, 500);
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

    # 2. Standalone Detection
    is_standalone_component = detect_standalone()
    
    if is_standalone_component is None:
        if "handshake_done" not in st.session_state:
            time.sleep(0.5)
            st.session_state.handshake_done = True
            st.rerun()
    
    is_standalone = bool(is_standalone_component)

    # 3. Check for existing Cookie
    saved_code = cookies.get("qsc_beer_code")
    if saved_code and not st.session_state.logged_in:
        res = conn.table("users").select("*").eq("token", saved_code).execute()
        if res.data:
            st.session_state.user_info = res.data[0]
            st.session_state.logged_in = True
            return st.session_state.user_info

    # 4. UI Logic
    if not st.session_state.logged_in:
        st.title("🍺 QSC Beer Tracker")
        
        # Connection Debug Expander
        with st.expander("🛠️ Connection Debug"):
            st.write(f"Standalone Mode Detected: **{is_standalone}**")
            override = st.toggle("Force Login Form (PC Testing)")
            if st.button("Reset Session"):
                st.session_state.clear()
                st.rerun()
        
        show_login = is_standalone or override

        if not show_login:
            st.info("### 📱 Installation Required")
            st.write("To use this app, please add it to your home screen first.")
            st.markdown("""
            **How to install:**
            1. Tap the **Share** (iOS) or **Menu** (Android) button.
            2. Select **'Add to Home Screen'**.
            3. Open the app from the icon on your home screen.
            """)
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
                        # Check if token is 6 digits; if not, reset it
                        if not code or len(str(code)) != 6:
                            code = str(random.randint(100000, 999999))
                            conn.table("users").update({"token": code}).eq("email", email_input).execute()

                        try:
                            # Using your stored Gmail credentials
                            yag = yagmail.SMTP("justin.moulton@gmail.com", "ocsr ngmx wzla uwau")
                            yag.send(
                                to=email_input, 
                                subject="Beer Tracker Code", 
                                contents=f"Your 6-digit access code is: {code}"
                            )
                            st.success("Code sent! Check your email.")
                            st.session_state.show_code_input = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Email failed: {e}")
                    else:
                        st.error("Email not found.")
        else:
            code_in = st.text_input("Enter 6-Digit Code")
            if st.button("Confirm and Log In"):
                res = conn.table("users").select("*").eq("email", email_input).eq("token", code_in).execute()
                if res.data:
                    st.session_state.user_info = res.data[0]
                    st.session_state.logged_in = True
                    
                    # FIX: Correctly format the datetime for the cookie manager
                    # This prevents the .isoformat() AttributeError
                    expiry_date = datetime.now() + timedelta(days=90)
                    cookie_manager.set("qsc_beer_code", str(code_in), expires_at=expiry_date)
                    
                    st.rerun()
                else:
                    st.error("Invalid code.")
            
            if st.button("Back"):
                st.session_state.show_code_input = False
                st.rerun()

    if st.session_state.logged_in:
        return st.session_state.user_info
    st.stop()
