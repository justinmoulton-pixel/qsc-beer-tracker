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

    # 1. Wait for Cookie Manager
    cookies = cookie_manager.get_all()
    if cookies is None:
        st.stop()

    # 2. Inject CSS for Standalone Detection
    # This CSS hides the "instruction" div and shows the "login" div 
    # ONLY when display-mode is standalone.
    st.markdown("""
        <style>
        #instruction-section { display: block; }
        #login-section { display: none; }

        @media (display-mode: standalone), (display-mode: fullscreen) {
            #instruction-section { display: none !important; }
            #login-section { display: block !important; }
        }
        /* iOS Specific Check */
        @supports (-webkit-touch-callout: none) {
            @media (display-mode: standalone) {
                #instruction-section { display: none !important; }
                #login-section { display: block !important; }
            }
        }
        </style>
    """, unsafe_allow_html=True)

    # 3. Sticky Cookie Check
    saved_code = cookies.get("qsc_beer_token")
    if saved_code and not st.session_state.logged_in:
        res = conn.table("users").select("*").eq("token", str(saved_code)).execute()
        if res.data:
            st.session_state.user_info = res.data[0]
            st.session_state.logged_in = True
            return st.session_state.user_info

    # 4. UI Logic
    if not st.session_state.logged_in:
        st.title("🍺 QSC Beer Tracker")

        # --- THE PC BYPASS (For your development) ---
        with st.expander("🛠️ Admin Tools"):
            override = st.toggle("PC Test Mode (Show Login)")
            if st.button("Clear Session"):
                st.session_state.clear()
                st.rerun()

        # If you are on PC testing, we skip the fancy CSS toggle
        if override:
            st.success("Admin Bypass Active")
        
        # --- WRAPPER DIVS ---
        # The CSS above controls which of these two 'divs' is visible
        
        # 1. The Instruction Section (Visible in Browser)
        if not override:
            st.markdown('<div id="instruction-section">', unsafe_allow_html=True)
            st.info("### 📱 Installation Required")
            st.write("To log in, add this app to your home screen.")
            st.markdown("1. Tap **Share** or **Menu**\n2. Select **'Add to Home Screen'**")
            st.markdown('</div>', unsafe_allow_html=True)

        # 2. The Login Section (Visible in Standalone/Home Screen)
        # We wrap the login form in a div that the CSS will 'display: block'
        st.markdown('<div id="login-section">', unsafe_allow_html=True)
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
        
        st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.logged_in:
        return st.session_state.user_info
    st.stop()
