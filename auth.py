import streamlit as st
import pandas as pd
import yagmail
from st_supabase_connection import SupabaseConnection

def check_is_standalone():
    """Checks if the app is running in 'standalone' (installed) mode."""
    return st.query_params.get("standalone") == "true"

def check_login():
    # 1. Initialize Session States
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"

    # 2. Establish Supabase Connection
    conn = st.connection("supabase", type=SupabaseConnection)

    # 3. Handle incoming Token from URL
    # We use .to_dict() to ensure we have a stable look at the params
    query_params = st.query_params.to_dict()
    url_token = query_params.get("token")
    
    if url_token and not st.session_state.logged_in:
        res = conn.table("users").select("*").eq("token", url_token).execute()
        
        if res.data:
            # User verified!
            st.session_state.user_info = res.data[0]
            st.session_state.logged_in = True
            
            # Instead of a blind rerun, we explicitly keep the token in the params
            # This forces the browser to keep the full URL string visible
            st.query_params["token"] = url_token
            st.query_params["standalone"] = "true"
            
            st.rerun()
        else:
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
        
    # 5. Login Fallback (If not logged in and no valid token)
    st.title("🍺 QSC Beer Tracker Login")
    email_input = st.text_input("Enter your email to receive your access link").strip().lower()
    
    if st.button("Send Access Link"):
        if email_input:
            # Query Supabase for the email
            res = conn.table("users").select("*").eq("email", email_input).execute()
            
            if res.data:
                user_record = res.data[0]
                token = user_record.get('token')
                
                # UPDATE THIS URL after you deploy to Streamlit Cloud
                base_url = "https://qsc-beer-tracker.streamlit.app/" 
                # For local testing, you can use: base_url = "http://localhost:8501"
                
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
