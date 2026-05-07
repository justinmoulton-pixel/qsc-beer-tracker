import streamlit as st
import pandas as pd
import yagmail
from extra_streamlit_components import CookieManager
from st_supabase_connection import SupabaseConnection

def check_is_standalone():
    """Checks if the app is running in 'standalone' (installed) mode."""
    return st.query_params.get("standalone") == "true"

def check_login():
    # CookieManager must be initialized early to handle the component handshake
    cookie_manager = CookieManager()
    
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"

    # 2. Establish Supabase Connection
    conn = st.connection("supabase", type=SupabaseConnection)

    # The component needs a moment to initialize; if cookies are None, we wait
    cookies = cookie_manager.get_all()
    
    # If the component hasn't reported back yet, stop execution and let it retry
 if cookies is None:
        # We show a clean spinner instead of an AttributeError
        with st.spinner("Authenticating..."):
            st.stop()
        
    # 3. Handling Authentication (Token vs Cookie)
    query_params = st.query_params.to_dict()
    url_token = query_params.get("token")
    
    # Retrieve token from browser cookies if available
    saved_token = cookie_manager.get(cookie="qsc_beer_token")
    
    # Priority: URL Token (new login) > Cookie Token (returning user)
    active_token = url_token or saved_token
    
    if active_token and not st.session_state.logged_in:
        res = conn.table("users").select("*").eq("token", active_token).execute()
        
        if res.data:
            # User verified!
            st.session_state.user_info = res.data[0]
            st.session_state.logged_in = True
            
            # Save the token to the device cookie (expires in 90 days) 
            # This is what makes "Add to Home Screen" work without the URL param
            if not saved_token or saved_token != active_token:
                cookie_manager.set("qsc_beer_token", active_token, expires_at=90)
            
            # Maintain URL state for initial installation if needed
            if url_token:
                st.query_params["token"] = url_token
                st.query_params["standalone"] = "true"
                st.rerun()
        else:
            # If the token in the cookie/URL is invalid, don't error out permanently
            # Just let them fall through to the login screen
            if url_token:
                st.error("Invalid or expired access link.")

    # 4. Check Login Status
    if st.session_state.logged_in:
        # App Installation Tip (Standalone check)
        if not check_is_standalone():
            with st.expander("📱 App Installation Tip"):
                st.write("To launch this like a native app, tap **Share** (iOS) or **Menu** (Android) and select **'Add to Home Screen'**.")
                if st.button("Hide this tip"):
                    st.query_params["standalone"] = "true"
                    st.rerun()
        return st.session_state.user_info # Success: Proceed to app.py
        
    # 5. Login Fallback (If not logged in and no valid token/cookie)
    st.title("🍺 QSC Beer Tracker Login")
    email_input = st.text_input("Enter your email to receive your access link").strip().lower()
    
    if st.button("Send Access Link"):
        if email_input:
            # Query Supabase for the email
            res = conn.table("users").select("*").eq("email", email_input).execute()
            
            if res.data:
                user_record = res.data[0]
                token = user_record.get('token')
                
                # Live URL
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
            
    st.stop() # Stop execution here so app.py content doesn't show behind login
