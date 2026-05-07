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
    Simpler JS detection to avoid API Exceptions. 
    Returns the raw value from the component.
    """
    js_code = """
    <script>
    function sendStatus() {
        const isiOS = window.navigator.standalone === true;
        const isPWA = window.matchMedia('(display-mode: standalone)').matches;
        const isMobile = /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);
        
        // Return a simple boolean
        const status = isiOS || (isPWA && isMobile);
        
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: status
        }, '*');
    }
    sendStatus();
    setTimeout(sendStatus, 300);
    </script>
    """
    return components.html(js_code, height=0, width=0)

def check_login():
    cookie_manager = CookieManager()
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    conn = st.connection("supabase", type=SupabaseConnection)

    # 1. Wait for Cookie Manager to be ready
    cookies = cookie_manager.get_all()
    if cookies is None:
        st.spinner("Initializing...")
        st.stop()

    # 2. Standalone Detection (Safe Handling)
    is_standalone_val = detect_standalone()
    
    # Give the JS component a moment to report back on first load
    if is_standalone_val is None:
        if "init_wait" not in st.session_state:
            time.sleep(0.5)
            st.session_state.init_wait = True
            st.rerun()
    
    is_standalone = bool(is_standalone_val)

    # 3. Check for existing "Sticky" Cookie
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
        
        # Debugging expander
        with st.expander("🛠️ Connection Debug"):
            st.write(f"Standalone Mode: **{is_standalone}**")
            override = st.toggle("PC Test Mode (Bypass)")
            if st.button("Clear Session"):
                st.session_state.clear()
                st.rerun()

        if not (is_standalone or override):
            st.info("### 📱 Installation Required")
            st.write("Please add this app to your home screen to log in.")
            st.markdown("1. Tap **Share** (iOS) or **Menu** (Android)\n2. Select **'Add to Home Screen'**")
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
                            st.success("Check your email!")
                            st.session_state.show_code_input = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Email error: {e}")
                    else:
                        st.error("Email not found.")
        else:
            code_in = st.text_input("6-Digit Code")
            if st.button("Confirm and Log In"):
                res = conn.table("users").select("*").eq("email", email_input).eq("token", code_in).execute()
                if res.data:
                    st.session_state.user_info = res.data[0]
                    st.session_state.logged_in = True
                    
                    # FINAL FIX: Use a clear datetime object for expiry
                    # This prevents the AttributeError: isoformat
                    try:
                        expire_at = datetime.now() + timedelta(days=90)
                        cookie_manager.set("qsc_beer_code", str(code_in), expires_at=expire_at)
                    except:
                        pass # Fallback if cookie fails so login still works
                    
                    st.rerun()
                else:
                    st.error("Invalid code.")
            
            if st.button("Back"):
                st.session_state.show_code_input = False
                st.rerun()

    if st.session_state.logged_in:
        return st.session_state.user_info
    st.stop()
