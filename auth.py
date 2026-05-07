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
    Improved detection with a handshake. 
    Returns True/False only when the browser responds.
    """
    js_code = """
    <script>
    function check() {
        const isInWebAppiOS = window.navigator.standalone === true;
        const isInWebAppChrome = window.matchMedia('(display-mode: standalone)').matches;
        const isStandalone = isInWebAppiOS || isInWebAppChrome;
        
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: isStandalone
        }, '*');
    }
    check();
    // Persistent check to ensure the value gets through
    setInterval(check, 500);
    </script>
    """
    # Create the component
    res = components.html(js_code, height=0, width=0)
    
    # If the JS hasn't reported yet, we wait briefly
    if res is None:
        if "is_standalone" not in st.session_state:
            # First run: pause a moment to let JS talk to Python
            time.sleep(0.5)
            st.rerun()
    else:
        st.session_state.is_standalone = res

def check_login():
    # 1. Initialize Components
    cookie_manager = CookieManager()
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    conn = st.connection("supabase", type=SupabaseConnection)

    # 2. Defensive Handshake for Cookies
    cookies = cookie_manager.get_all()
    if cookies is None:
        with st.spinner("Initializing..."):
            st.stop()

    # 3. Detect Standalone Mode
    detect_standalone()
    
    # Safety: If detect_standalone is still cycling, stop here
    if "is_standalone" not in st.session_state:
        st.stop()

    # 4. Check for existing "Sticky" Cookie
    saved_code = cookies.get("qsc_beer_code")
    if saved_code and not st.session_state.logged_in:
        res = conn.table("users").select("*").eq("token", saved_code).execute()
        if res.data:
            st.session_state.user_info = res.data[0]
            st.session_state.logged_in = True
            return st.session_state.user_info

    # 5. UI Logic
    if not st.session_state.logged_in:
        st.title("🍺 QSC Beer Tracker")
        
        if not st.session_state.is_standalone:
            # --- BROWSER MODE ---
            st.info("### 📱 Installation Required")
            st.write("To log in, you must add this app to your home screen first.")
            
            # Use columns for a cleaner look on mobile
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**iPhone (Safari)**\n1. Tap 'Share'\n2. 'Add to Home Screen'")
            with col2:
                st.markdown("**Android (Chrome)**\n1. Tap 'Menu' (⋮)\n2. 'Install app'")
            
            # Temporary Bypass for the Admin (You)
            if st.toggle("Admin Bypass (Show login anyway)"):
                pass 
            else:
                st.stop()
        
        # --- STANDALONE MODE (LOGIN FORM) ---
        st.success("✅ Home Screen Mode Detected")
        email_input = st.text_input("Enter your email").strip().lower()
        
        if "show_code_input" not in st.session_state:
            st.session_state.show_code_input = False

        if not st.session_state.show_code_input:
            if st.button("Verify Email"):
                if email_input:
                    res = conn.table("users").select("*").eq("email", email_input).execute()
                    if res.data:
                        user = res.data[0]
                        existing_code = user.get('token')
                        
                        if not existing_code or len(str(existing_code)) > 6:
                            new_code = str(random.randint(100000, 999999))
                            conn.table("users").update({"token": new_code}).eq("email", email_input).execute()
                            final_code = new_code
                        else:
                            final_code = existing_code

                        try:
                            yag = yagmail.SMTP("justin.moulton@gmail.com", "ocsr ngmx wzla uwau")
                            yag.send(
                                to=email_input,
                                subject="Your Beer Tracker Access Code",
                                contents=f"Your 6-digit access code is: {final_code}"
                            )
                            st.success(f"Verification code sent to {email_input}!")
                            st.session_state.show_code_input = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error sending email: {e}")
                    else:
                        st.error("Email not found in league records.")
        
        else:
            code_input = st.text_input("Enter 6-Digit Code", placeholder="123456")
            if st.button("Confirm Code"):
                res = conn.table("users").select("*").eq("email", email_input).eq("token", code_input).execute()
                
                if res.data:
                    st.session_state.user_info = res.data[0]
                    st.session_state.logged_in = True
                    expiry = datetime.now() + timedelta(days=90)
                    cookie_manager.set("qsc_beer_code", code_input, expires_at=expiry)
                    st.rerun()
                else:
                    st.error("Invalid code.")
            
            if st.button("Back"):
                st.session_state.show_code_input = False
                st.rerun()

    if st.session_state.logged_in:
        return st.session_state.user_info

    st.stop()
