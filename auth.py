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

    # 2. Sticky Cookie Logic
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

        if "show_code_input" not in st.session_state:
            st.session_state.show_code_input = False

        # Phase 1: Email Entry
        if not st.session_state.show_code_input:
            st.markdown("""
                <style>
                    /* 1. Target the Email Input Wrapper */
                    .st-key-email_addr div[data-baseweb="input"] {
                        border: 3px solid #1E90FF !important;
                        border-radius: 8px !important;
                    }
                </style>
            """, unsafe_allow_html=True)
            email_input = st.text_input("Enter your email", key="email_addr").strip().lower()
            if st.button("Verify Email"):
                if email_input:
                    res = conn.table("users").select("*").eq("email", email_input).execute()
                    if res.data:
                        user = res.data[0]
                        code = user.get('token')
                        # Ensure 6-digit token exists
                        if not code or len(str(code)) != 6:
                            code = str(random.randint(100000, 999999))
                            conn.table("users").update({"token": code}).eq("email", email_input).execute()

                        try:
                            # Send email
                            email_body = f"""
                            Your code is: <b>{code}</b>
                            
                            <br><br>
                            ---
                            <br>
                            <b>Icon for your app:</b><br>
                            <a href="https://raw.githubusercontent.com/justinmoulton-pixel/qsc-beer-tracker/main/static/QSC_Beer.png">Click here to download the QSC Beer Icon</a>
                            """
                            yag = yagmail.SMTP("justin.moulton@gmail.com", "ocsr ngmx wzla uwau")
                            yag.send(to=email_input, subject="Beer Tracker Code", contents=email_body)
                            st.success("Verification code sent! Check your inbox.")
                            st.session_state.user_email = email_input # Store email for verification
                            st.session_state.show_code_input = True
                            st.rerun()
                        except Exception as e:
                            st.error(f"Email failed: {e}")
                    else:
                        st.error("Email not found in league roster.")
        
        # Phase 2: 6-Digit Numeric Code Entry
        else:
            # We use text_input but validate it's numeric to keep the UI clean
            st.markdown("""
                <style>
                    /* 2. Target the 6-Digit Code Input Wrapper */
                    .st-key-access_code div[data-baseweb="input"] {
                        border: 3px solid #1E90FF !important;
                        border-radius: 8px !important;
                    }
                </style>
            """, unsafe_allow_html=True)
            code_in = st.text_input("Enter 6-Digit Code", max_chars=6, key="access_code", help="Numbers only")
            
            if st.button("Log In"):
                # Check if input is numeric and the correct code
                if not code_in.isdigit():
                    st.error("Please enter numbers only.")
                else:
                    email_to_verify = st.session_state.get('user_email')
                    res = conn.table("users").select("*").eq("email", email_to_verify).eq("token", code_in).execute()
                    
                    if res.data:
                        st.session_state.user_info = res.data[0]
                        st.session_state.logged_in = True
                        
                        # Set the 90-day cookie
                        try:
                            expire_at = datetime.now() + timedelta(days=90)
                            cookie_manager.set("qsc_beer_token", str(code_in), expires_at=expire_at)
                            time.sleep(0.2) 
                        except:
                            pass
                        st.rerun()
                    else:
                        st.error("Invalid code. Please check your email and try again.")
            
            # Replaced "Back" button with a simple reset link to keep UI clean
            #if st.button("Restart Login"):
            #    st.session_state.show_code_input = False
            #    st.rerun()

    if st.session_state.logged_in:
        return st.session_state.user_info
    st.stop()
