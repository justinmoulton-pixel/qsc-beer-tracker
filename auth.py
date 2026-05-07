import streamlit as st
import pandas as pd
import yagmail
import random
from datetime import datetime, timedelta
from extra_streamlit_components import CookieManager
from st_supabase_connection import SupabaseConnection

def check_is_standalone():
    return st.query_params.get("standalone") == "true"

def check_login():
    # 1. Initialize Components
    cookie_manager = CookieManager()
    
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
        # Check if this code belongs to a user
        res = conn.table("users").select("*").eq("token", saved_code).execute()
        if res.data:
            st.session_state.user_info = res.data[0]
            st.session_state.logged_in = True
            return st.session_state.user_info

    # 4. The Login/Verification Flow
    if not st.session_state.logged_in:
        st.title("🍺 QSC Beer Tracker")
        
        # Instructions for first-time users
        if not check_is_standalone():
            st.warning("👉 **First Step:** Tap 'Share' (iOS) or 'Menu' (Android) and 'Add to Home Screen'. Open the app from your home screen to log in!")

        email_input = st.text_input("Enter your email").strip().lower()
        
        # State tracking for the two-step verification
        if "show_code_input" not in st.session_state:
            st.session_state.show_code_input = False

        if not st.session_state.show_code_input:
            if st.button("Verify Email"):
                if email_input:
                    res = conn.table("users").select("*").eq("email", email_input).execute()
                    if res.data:
                        user = res.data[0]
                        existing_code = user.get('token')
                        
                        # Generate code if it doesn't exist or is too long (old tokens)
                        if not existing_code or len(str(existing_code)) > 6:
                            new_code = str(random.randint(100000, 999999))
                            conn.table("users").update({"token": new_code}).eq("email", email_input).execute()
                            final_code = new_code
                        else:
                            final_code = existing_code

                        # Send the Email
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
            # Step 2: Enter the 6-digit code
            code_input = st.text_input("Enter 6-Digit Code", placeholder="123456")
            if st.button("Confirm Code"):
                res = conn.table("users").select("*").eq("email", email_input).eq("token", code_input).execute()
                
                if res.data:
                    st.session_state.user_info = res.data[0]
                    st.session_state.logged_in = True
                    
                    # SAVE THE COOKIE inside the Home Screen Sandbox
                    expiry = datetime.now() + timedelta(days=90)
                    cookie_manager.set("qsc_beer_code", code_input, expires_at=expiry)
                    
                    st.success("Success! Redirecting...")
                    st.rerun()
                else:
                    st.error("Invalid code. Please try again.")
            
            if st.button("Back"):
                st.session_state.show_code_input = False
                st.rerun()

    if st.session_state.logged_in:
        return st.session_state.user_info

    st.stop()
