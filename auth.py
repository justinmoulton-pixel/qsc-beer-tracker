import streamlit as st
import pandas as pd
import yagmail
import random
import time
from datetime import datetime, timedelta
from extra_streamlit_components import CookieManager
from st_supabase_connection import SupabaseConnection
import streamlit.components.v1 as components

def get_browser_fingerprint():
    """
    Injects JS to pull browser attributes.
    """
    js_code = """
    <script>
    function sendDetails() {
        const data = {
            isiOSStandalone: window.navigator.standalone === true,
            isDisplayStandalone: window.matchMedia('(display-mode: standalone)').matches,
            userAgent: navigator.userAgent,
            windowWidth: window.innerWidth,
            windowHeight: window.innerHeight,
            isMobile: /iPhone|iPad|iPod|Android/i.test(navigator.userAgent),
            menubarVisible: window.menubar ? window.menubar.visible : "unknown"
        };
        
        // Logical detection
        const isLikelyStandalone = data.isiOSStandalone || (data.isDisplayStandalone && data.isMobile);

        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: { status: isLikelyStandalone, raw: data }
        }, '*');
    }
    sendDetails();
    // Repeating to ensure the message hits the parent
    setTimeout(sendDetails, 500);
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
        st.stop()

    # 2. Safe Component Handling
    # This is where the error was happening. We MUST check if it's None first.
    fingerprint_component = get_browser_fingerprint()
    
    is_standalone = False
    raw_debug = {}

    if fingerprint_component is not None:
        # Check if it's a dict before calling .get()
        if isinstance(fingerprint_component, dict):
            is_standalone = fingerprint_component.get("status", False)
            raw_debug = fingerprint_component.get("raw", {})
    else:
        # If it's None, we wait once and rerun to give JS time to talk back
        if "retry_count" not in st.session_state:
            st.session_state.retry_count = 0
            
        if st.session_state.retry_count < 2:
            st.session_state.retry_count += 1
            time.sleep(0.5)
            st.rerun()

    # 3. Sticky Cookie Check
    saved_code = cookies.get("qsc_beer_token")
    if saved_code and not st.session_state.logged_in:
        res = conn.table("users").select("*").eq("token", str(saved_code)).execute()
        if res.data:
            st.session_state.user_info = res.data[0]
            st.session_state.logged_in = True
            return st.session_state.user_info

    # 4. UI Rendering
    if not st.session_state.logged_in:
        st.title("🍺 QSC Beer Tracker")
        
        # --- THE FULL BROWSER DUMP ---
        with st.expander("🛠️ DBA Browser Profile Dump"):
            st.write(f"**Calculated Standalone:** {is_standalone}")
            if raw_debug:
                st.json(raw_debug)
            else:
                st.write("Waiting for browser data...")
            
            override = st.toggle("PC Test Mode (Bypass)")
            if st.button("Hard Reset Session"):
                st.session_state.clear()
                st.rerun()

        if not (is_standalone or override):
            st.info("### 📱 Installation Required")
            st.write("To log in, please add this app to your home screen first.")
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
                            yag.send(to=email_input, subject="Your Code", contents=f"Code: {code}")
                            st.success("Verification code sent!")
                            st.session_state.show_code_input = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Email error: {e}")
                    else:
                        st.error("Email not found.")
        else:
            code_in = st.text_input("Enter 6-Digit Code")
            if st.button("Confirm Code"):
                res = conn.table("users").select("*").eq("email", email_input).eq("token", code_in).execute()
                if res.data:
                    st.session_state.user_info = res.data[0]
                    st.session_state.logged_in = True
                    
                    try:
                        # Fixed date handling
                        exp = datetime.now() + timedelta(days=90)
                        cookie_manager.set("qsc_beer_token", str(code_in), expires_at=exp)
                    except:
                        pass
                    
                    st.rerun()
                else:
                    st.error("Invalid code.")
            
            if st.button("Back"):
                st.session_state.show_code_input = False
                st.rerun()

    if st.session_state.logged_in:
        return st.session_state.user_info
    st.stop()
