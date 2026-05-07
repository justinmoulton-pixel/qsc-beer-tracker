import streamlit as st
import pandas as pd
import yagmail
import random
from datetime import datetime, timedelta
from extra_streamlit_components import CookieManager
from st_supabase_connection import SupabaseConnection
import streamlit.components.v1 as components

def detect_standalone():
    """
    Injects JS to detect if the app is in standalone mode 
    and reports it back to st.session_state.is_standalone
    """
    js_code = """
    <script>
    function checkStandalone() {
        const isInWebAppiOS = window.navigator.standalone === true;
        const isInWebAppChrome = window.matchMedia('(display-mode: standalone)').matches;
        const isStandalone = isInWebAppiOS || isInWebAppChrome;
        
        window.parent.postMessage({
            type: 'streamlit:setComponentValue',
            value: isStandalone
        }, '*');
    }
    // Run immediately and after a small delay to ensure handshake
    checkStandalone();
    setTimeout(checkStandalone, 200);
    </script>
    """
    # This creates a hidden 0px iframe to run the detection
    res = components.html(js_code, height=0, width=0)
    
    # Update session state based on JS return
    if res is not None:
        st.session_state.is_standalone = res
    elif "is_standalone" not in st.session_state:
        # Default to False until JS reports back
        st.session_state.is_standalone = False

def check_login():
    # 1. Initialize Components & Detect Mode
    cookie_manager = CookieManager()
    detect_standalone()
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    conn = st.connection("supabase", type=SupabaseConnection)

    # 2. Defensive Handshake for Cookies
    cookies = cookie_manager.get_all()
    if cookies is None:
        with st.spinner("Connecting..."):
            st.stop()

    # 3. Check for existing "Sticky" Cookie
    saved_code = cookies.get("qsc_beer_code")
    
    if saved_code and not st.session_state.logged_in:
        res = conn.table("users").select("*").eq("token", saved_code).execute()
        if res.data:
            st.session_state.user_info = res.data[0]
            st.session_state.logged_in = True
            return st.session_state.user_info

    # 4. The UI Logic
    if not st.session_state.logged_in:
        st.title("🍺 QSC Beer Tracker")
        
        # GATEKEEPER: Check if they are in the browser or the Home Screen
        if not st.session_state.is_standalone:
            # BROWSER MODE: Show instructions ONLY
            st.info("### 📱 Installation Required")
            st.write("To use the Beer Tracker, you must first add it to your home screen:")
            
            st.markdown("""
            1. **iOS (Safari):** Tap the **Share** button (box with arrow) and select **'Add to Home Screen'**.
            2. **Android (Chrome):** Tap the **Menu** (three dots) and select **'Install app'** or **'Add to Home Screen'**.
            
            **Once added, close this browser tab and open the 'Beer Tracker' app from your home screen to verify your account.**
            """)
            
            # For debugging/testing, you can add a temporary button here to bypass
            # if st.button("Developer Bypass (Browser Mode)"):
            #     st.session_state.is_standalone = True
            #     st.rerun()
            
            st.stop() # Stops execution so login form never shows in Safari/Chrome
            
        else:
            # STANDALONE MODE: Show the Verification Flow
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
                        
                        st.success("Success! Loading Dashboard...")
                        st.rerun()
                    else:
                        st.error("Invalid code. Please try again.")
                
                if st.button("Back"):
                    st.session_state.show_code_input = False
                    st.rerun()

    if st.session_state.logged_in:
        return st.session_state.user_info

    st.stop()
