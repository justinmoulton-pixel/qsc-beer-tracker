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
    Surgical JS detection that returns the value directly.
    """
    js_code = """
    <script>
    function check() {
        const isiOS = window.navigator.standalone === true;
        const isChrome = window.matchMedia('(display-mode: standalone)').matches;
        // Check for common standalone modes
        const status = (isiOS || isChrome);
        
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: status
        }, '*');
    }
    check();
    // Keep checking in case of slow browser renders
    setTimeout(check, 500);
    </script>
    """
    # This returns the value from the JS postMessage
    return components.html(js_code, height=0, width=0)

def check_login():
    cookie_manager = CookieManager()
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    conn = st.connection("supabase", type=SupabaseConnection)

    # 1. Cookie Handshake
    cookies = cookie_manager.get_all()
    if cookies is None:
        with st.spinner("Connecting..."):
            st.stop()

    # 2. Standalone Detection
    # We get the value directly from the component rather than using session_state
    is_standalone_component = detect_standalone()
    
    # If it's the very first load, give it a half-second to handshake
    if is_standalone_component is None:
        time.sleep(0.5)
        st.rerun()

    # Convert the component return value to a boolean
    # If the component is still loading, it might be an empty object or None
    is_standalone = bool(is_standalone_component)

    # 3. Check for existing "Sticky" Cookie
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
        
        # DEBUG: Temporary expander to see what's happening
        with st.expander("🛠️ Connection Debug"):
            st.write(f"Standalone Mode Detected: {is_standalone}")
            if st.toggle("Override (Show Login Form)"):
                is_standalone = True

        if not is_standalone:
            st.info("### 📱 Installation Required")
            st.write("To access the tracker, please add this page to your home screen.")
            st.markdown("1. Tap **Share** (iOS) or **Menu** (Android)\n2. Select **'Add to Home Screen'**")
            st.stop()

        # --- LOGIN FORM (Only shown in Standalone) ---
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
                        if not code or len(str(code)) > 6:
                            code = str(random.randint(100000, 999999))
                            conn.table("users").update({"token": code}).eq("email", email_input).execute()

                        try:
                            yag = yagmail.SMTP("justin.moulton@gmail.com", "ocsr ngmx wzla uwau")
                            yag.send(to=email_input, subject="Your Beer Tracker Code", contents=f"Your code is: {code}")
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
                    # Set the sticky cookie
                    expiry = datetime.now() + timedelta(days=90)
                    cookie_manager.set("qsc_beer_code", code_in, expires_at=expiry)
                    st.rerun()
                else:
                    st.error("Invalid code.")
            
            if st.button("Back"):
                st.session_state.show_code_input = False
                st.rerun()

    if st.session_state.logged_in:
        return st.session_state.user_info
    st.stop()
