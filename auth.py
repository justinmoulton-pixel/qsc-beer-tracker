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
    Detailed detection that returns a string describing the mode.
    """
    js_code = """
    <script>
    function check() {
        const isiOS = window.navigator.standalone === true;
        const isChrome = window.matchMedia('(display-mode: standalone)').matches;
        const isEdge = window.matchMedia('(display-mode: fullscreen)').matches;
        
        const status = (isiOS || isChrome || isEdge);
        
        // We send an object with details for debugging
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: {
                is_standalone: status,
                details: `iOS: ${isiOS}, Chrome: ${isChrome}, Edge: ${isEdge}`,
                agent: navigator.userAgent
            }
        }, '*');
    }
    check();
    setInterval(check, 1000);
    </script>
    """
    res = components.html(js_code, height=0, width=0)
    
    if res is not None:
        st.session_state.is_standalone = res.get("is_standalone", False)
        st.session_state.debug_details = res.get("details", "No details")
        st.session_state.user_agent = res.get("agent", "Unknown")
    elif "is_standalone" not in st.session_state:
        time.sleep(0.5)
        st.rerun()

def check_login():
    cookie_manager = CookieManager()
    detect_standalone()
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    conn = st.connection("supabase", type=SupabaseConnection)

    # Cookie Handshake
    cookies = cookie_manager.get_all()
    if cookies is None:
        with st.spinner("Connecting to Secure Vault..."):
            st.stop()

    # --- DEBUG CONSOLE (Temporary) ---
    # This will help us see exactly what the browser is telling Python
    with st.expander("🛠️ DBA Debug Console"):
        st.write(f"**Standalone Detected:** {st.session_state.get('is_standalone')}")
        st.write(f"**Detection Logic:** {st.session_state.get('debug_details')}")
        st.write(f"**Cookies Found:** {list(cookies.keys())}")
        if st.button("Clear Session State"):
            st.session_state.clear()
            st.rerun()

    # Check for "Sticky" Cookie
    saved_code = cookies.get("qsc_beer_code")
    if saved_code and not st.session_state.logged_in:
        res = conn.table("users").select("*").eq("token", saved_code).execute()
        if res.data:
            st.session_state.user_info = res.data[0]
            st.session_state.logged_in = True
            return st.session_state.user_info

    if not st.session_state.logged_in:
        st.title("🍺 QSC Beer Tracker")
        
        # Logic Gate
        if not st.session_state.get("is_standalone", False):
            st.info("### 📱 Installation Required")
            st.write("To use this app, you must add it to your home screen.")
            st.markdown("1. Tap **Share** or **Menu**\n2. Select **'Add to Home Screen'**")
            
            # Use this toggle to get past the wall while we fix the JS
            if st.toggle("Force Login Form (Testing Only)"):
                pass
            else:
                st.stop()

        # --- LOGIN FORM ---
        st.success("🏠 App Mode Active")
        email_input = st.text_input("Email").strip().lower()
        
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
                            yag.send(to=email_input, subject="Your Code", contents=f"Code: {code}")
                            st.success("Check your email!")
                            st.session_state.show_code_input = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Mail error: {e}")
                    else:
                        st.error("Email not found.")
        else:
            code_in = st.text_input("6-Digit Code")
            if st.button("Confirm"):
                res = conn.table("users").select("*").eq("email", email_input).eq("token", code_in).execute()
                if res.data:
                    st.session_state.user_info = res.data[0]
                    st.session_state.logged_in = True
                    expiry = datetime.now() + timedelta(days=90)
                    cookie_manager.set("qsc_beer_code", code_in, expires_at=expiry)
                    st.rerun()
            if st.button("Back"):
                st.session_state.show_code_input = False
                st.rerun()

    if st.session_state.logged_in:
        return st.session_state.user_info
    st.stop()
