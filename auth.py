import streamlit as st
import pandas as pd
import yagmail
import random
import time
from datetime import datetime, timedelta
from extra_streamlit_components import CookieManager
from st_supabase_connection import SupabaseConnection

def check_login():
    # 1. Immediate Session Check (Zero Latency)
    if st.session_state.get("logged_in"):
        return st.session_state.user_info

    cookie_manager = CookieManager()
    conn = st.connection("supabase", type=SupabaseConnection)

    # 2. Silent Cookie Handshake
    # We do NOT render anything here. No titles, no spinners.
    cookies = cookie_manager.get_all()
    
    if cookies is None:
        # App stays blank for a split second while browser handles the request
        st.stop()

    # 3. Check for Saved Token
    saved_code = cookies.get("qsc_beer_token")
    if saved_code:
        res = conn.table("users").select("*").eq("token", str(saved_code)).execute()
        if res.data:
            st.session_state.user_info = res.data[0]
            st.session_state.logged_in = True
            return st.session_state.user_info

    # 4. Only if both checks fail, show the Login UI
    st.title("🍺 QSC Beer Tracker")

    with st.expander("📱 How to install as an App", expanded=True):
        st.info("To stay logged in, add this to your home screen!")
        st.markdown("1. **iPhone:** Tap Share -> 'Add to Home Screen'\n2. **Android:** Tap Menu -> 'Install App'")

    st.write("---")
    
    if not st.session_state.get("show_code_input"):
        email_input = st.text_input("Enter your email").strip().lower()
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
                        yag.send(to=email_input, subject="Beer Tracker Code", contents=f"Your code is: {code}")
                        st.success("Verification code sent!")
                        st.session_state.user_email = email_input
                        st.session_state.show_code_input = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Email failed: {e}")
                else:
                    st.error("Email not found in league roster.")
    
    else:
        code_in = st.text_input("Enter 6-Digit Code", max_chars=6)
        if st.button("Log In"):
            if not code_in.isdigit():
                st.error("Please enter numbers only.")
            else:
                email_to_verify = st.session_state.get('user_email')
                res = conn.table("users").select("*").eq("email", email_to_verify).eq("token", code_in).execute()
                
                if res.data:
                    st.session_state.user_info = res.data[0]
                    st.session_state.logged_in = True
                    try:
                        expire_at = datetime.now() + timedelta(days=90)
                        cookie_manager.set("qsc_beer_token", str(code_in), expires_at=expire_at)
                        time.sleep(0.2) 
                    except:
                        pass
                    st.rerun()
                else:
                    st.error("Invalid code.")
        
        if st.button("Restart Login"):
            st.session_state.show_code_input = False
            st.rerun()

    st.stop()
