import streamlit as st
import pandas as pd
import yagmail
from datetime import datetime, timedelta
from extra_streamlit_components import CookieManager
from st_supabase_connection import SupabaseConnection

def check_is_standalone():
    """Checks if the app is running in 'standalone' (installed) mode."""
    return st.query_params.get("standalone") == "true"

def check_login():
    # 1. Initialize Cookie Manager & Session States
    cookie_manager = CookieManager()
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"

    # 2. Establish Supabase Connection
    conn = st.connection("supabase", type=SupabaseConnection)

    # 3. Defensive Handshake
    # Wait for the CookieManager component to wake up and report back
    cookies = cookie_manager.get_all()
    
    if cookies is None:
        # Prevents the AttributeError by stopping execution until cookies are ready
        with st.spinner("Authenticating..."):
            st.stop()
        
    # 4. Handling Authentication (Token vs Cookie)
    query_params = st.query_params.to_dict()
    url_token = query_params.get("token")
    
    # Retrieve token from browser cookies if available
    saved_token = cookies.get("qsc_beer_token")
    
    # Priority: URL Token (new login) > Cookie Token (returning user)
    active_token = url_token or saved_token
    
    if active_token and not st.session_state.logged_in:
        res = conn.table("users").select("*").eq("token", active_token).execute()
        
        if res.data:
            # User verified!
            st.session_state.user_info = res.data[0]
            st.session_state.logged_in = True
            
            # FIX: Convert 90 days to a proper datetime object for the cookie engine
            if not saved_token or saved_token != active_token:
                expiry = datetime.now() + timedelta(days=90)
                cookie_manager.set("qsc_beer_token", active_token, expires_at=expiry)
            
            # Maintain URL state for initial installation window
            if url_token:
                st.query_params["token"] = url_token
                st.query_params["standalone"] = "true"
                st.rerun()
            
            return st.session_state.user_info
        else:
            if url_token:
                st.error("Invalid or expired access link.")

    # 5. Check Login Status
    if st.session_state.logged_in:
        if not check_is_standalone():
            with st.expander("📱 App Installation Tip"):
                st.write("To launch this like a native app, tap **Share** (iOS) or **Menu** (Android) and select **'Add to Home Screen'**.")
                if st.button("Hide this tip"):
                    st.query_params["standalone"] = "true"
                    st.rerun()
        return st.session_state.user_info
        
    # 6. Login Fallback
    st.title("🍺 QSC Beer Tracker Login")
    email_input = st.text_input("Enter your email to receive your access link").strip().lower()
    
    if st.button("Send Access Link"):
        if email_input:
            res = conn.table("users").select("*").eq("email", email_input).execute()
            
            if res.data:
                user_record = res.data[0]
                token = user_record.get('token')
                base_url = "https://qsc-beer-tracker.streamlit.app" 
                link = f"{base_url}/?token={token}&standalone=true"
                
                try:
                    yag = yagmail.SMTP("justin.moulton@gmail.com", "ocsr ngmx wzla uwau")
                    yag.send(
                        to=email_input, 
                        subject="Your Beer Tracker Access Link", 
                        contents=f"Click here to access your tracker: {link}"
                    )
                    st.success("Access link sent! Check your email.")
                except Exception as e:
                    st.error(f"Failed to send email. Error: {e}")
            else:
                st.error("Email not found in the system.")
        else:
            st.warning("Please enter an email address.")
            
    st.stop()
