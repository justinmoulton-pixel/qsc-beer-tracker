import streamlit as st
import pandas as pd
import yagmail
import random
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
        st.stop()

    # 2. Server-Side Environment Check
    # We pull the User-Agent header to see if they are on mobile
    user_agent = st.context.headers.get("User-Agent", "").lower()
    is_mobile = any(x in user_agent for x in ["iphone", "android", "mobile"])

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

        with st.expander("🛠️ Admin Tools"):
            # This is your manual "I am on my PC" toggle
            is_dev_bypass = st.toggle("PC Development Mode", value=False)
            if st.button("Clear Session"):
                st.session_state.clear()
                st.rerun()

        # LOGIC: If it's not mobile and not the dev bypass, show installation info
        if not is_mobile and not is_dev_bypass:
            st.info("### 📱 Installation Required")
            st.write("This app is designed to be used from your home screen.")
            st.markdown("""
            **How to install:**
            1. Open this link on your phone.
            2. Tap **Share** (iOS) or **Menu** (Android).
            3. Select **'Add to Home Screen'**.
            """)
            st.stop() # This stops the script here so the email box won't show

        # --- LOGIN FORM (Only reached if Mobile or Bypass is True) ---
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
