import streamlit as st
import pandas as pd
import gspread
import yagmail

def check_is_standalone():
    """Checks if the app is running in 'standalone' (installed) mode."""
    # This checks a custom flag we can pass or a common browser state
    return st.query_params.get("standalone") == "true"

def check_login():
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
 
    # Initialize page state here so it's guaranteed to exist
    if 'current_page' not in st.session_state:
        st.session_state.current_page = "Dashboard"
        
    # 1. Handle incoming Token
    query_params = st.query_params
    url_token = query_params.get("token")
    
    if url_token and not st.session_state.logged_in:
        gc = gspread.service_account(filename='credentials.json')
        sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1sOq9HDN5wTdwOmnT8wnTett7X4JwWzPuUzT0mOga_3c/edit")
        users_df = pd.DataFrame(sh.worksheet("Users").get_all_records())
        
        if url_token in users_df['Token'].values:
            user_data = users_df[users_df['Token'] == url_token].iloc[0]
            st.session_state.user_info = user_data.to_dict()
            st.session_state.logged_in = True
            # Clear token from URL so it doesn't look messy
            st.query_params.clear()
            st.rerun()

    # 2. If logged in, show "Install" prompt if not in standalone mode
#    if st.session_state.logged_in:
#        if not check_is_standalone():
#            st.warning("📱 **Pro Tip:** Make this app official!")
#            st.write("To launch this like a native app, tap your browser's **Share** (iOS) or **Menu** (Android) button and select **'Add to Home Screen'**.")
#            if st.button("Got it, hide this message"):
#                st.query_params["standalone"] = "true"
#                st.rerun()
#        return # Proceed to the rest of the app


# 2. Check Login Status
    if st.session_state.logged_in:
        # Move the 'Pro Tip' to a place where it won't break the layout flow
        if not check_is_standalone():
            with st.expander("📱 App Installation Tip"):
                st.write("Tap **Share** (iOS) or **Menu** (Android) and select **'Add to Home Screen'**.")
                if st.button("Hide this tip"):
                    st.query_params["standalone"] = "true"
                    st.rerun()
        return # Success: Proceed to app.py
        
    # 3. Login Fallback
    st.title("🍺 QSC Beer Tracker Login")
    email = st.text_input("Enter your email to receive your access link")
    
    if st.button("Send Access Link"):
        gc = gspread.service_account(filename='credentials.json')
        sh = gc.open_by_url("https://docs.google.com/spreadsheets/d/1sOq9HDN5wTdwOmnT8wnTett7X4JwWzPuUzT0mOga_3c/edit")
        users_df = pd.DataFrame(sh.worksheet("Users").get_all_records())
        
        if email in users_df['Email'].values:
            token = users_df[users_df['Email'] == email].iloc[0]['Token']
            # We add &standalone=true so the app knows they've 'installed' it
            link = f"http://localhost:8501/?token={token}&standalone=true"
            yag = yagmail.SMTP("justin.moulton@gmail.com", "ocsr ngmx wzla uwau")
            yag.send(email, "Your Beer Tracker Access Link", f"Click here to access: {link}")
            st.success("Access link sent! Check your email.")
        else:
            st.error("Email not found.")
    st.stop()