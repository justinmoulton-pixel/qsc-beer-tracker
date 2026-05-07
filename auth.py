import streamlit as st
import pandas as pd
import yagmail
import random
import time
from datetime import datetime, timedelta
from extra_streamlit_components import CookieManager
from st_supabase_connection import SupabaseConnection

def check_login():
    cookie_manager = CookieManager()
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    conn = st.connection("supabase", type=SupabaseConnection)

    # 1. Cookie Handshake
    cookies = cookie_manager.get_all()
    if cookies is None:
        # If cookies aren't ready, we just wait briefly
        st.stop()

    # 2. Sticky Cookie Logic (The most important part for PWA)
    saved_code = cookies.get("qsc_beer_token")
    if saved_code and not st.session_state.logged_in:
        res = conn.table("users").select("*").eq("token", str(saved_code)).execute()
        if res.data:
            st.session_state.user_info = res.data[0]
            st.session_state.logged_in = True
            return st.session_state.user_info

    # 3. UI Rendering
    if not st.session_state.logged_in:
        st.title("🍺 QSC Beer Tracker")

        # Instead of a hard gate, we use an info box that users can see 
        # This helps them install it without blocking your dev work
        with st.expander("📱 How to install as an App", expanded=True):
            st.info("To stay logged in, add this to your home screen!")
            st.markdown("1. **iPhone:** Tap Share -> 'Add to Home Screen'\n2. **Android:** Tap Menu -> 'Install App'")

        # --- LOGIN FORM ---
        st.write("---")
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
                        # Ensure 6-digit token
                        if not code or len(str(code)) != 6:
                            code = str(random.randint(100000, 999999))
                            conn.table("users").update({"token": code}).eq("email", email_input).execute()

                        try:
                            # Using your Gmail App Password
                            yag = yagmail.SMTP("justin.moulton@gmail.com", "ocsr ngmx wzla uwau")
                            yag.send(to=email_input, subject="Beer Tracker Code", contents=f"Your code is: {code}")
                            st.success("Verification code sent! Check your inbox.")
                            st.session_state.show_code_input = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Email failed: {e}")
                    else:
                        st.error("Email not found in league roster.")
        else:
            code_in = st.text_input("6-Digit Code")
            if st.button("Log In"):
                res = conn.table("users").select("*").eq("email", email_input).eq("token", code_in).execute()
                if res.data:
                    st.session_state.user_info = res.data[0]
                    st.session_state.logged_in = True
                    
                    # Set the 90-day cookie
                    try:
                        expire_at = datetime.now() + timedelta(days=90)
                        cookie_manager.set("qsc_beer_token", str(code_in), expires_at=expire_at)
                        # Brief pause to let cookie write
                        time.sleep(0.2) 
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
