import streamlit as st
import pandas as pd
import base64
from datetime import datetime
from st_supabase_connection import SupabaseConnection
from auth import check_login

# 1. Page Config & Professional Styling
st.set_page_config(
    page_title="QSC Beer Tracker", 
    page_icon="static/QSC_Beer.png"
)

def inject_pwa_meta():
    # Since enableStaticServing is true, this path maps directly to your static folder
    icon_path = "app/static/QSC_Beer.png" 
    
    st.markdown(f"""
        <head>
            <link rel="apple-touch-icon" sizes="180x180" href="{icon_path}">
            <link rel="icon" type="image/png" sizes="192x192" href="{icon_path}">
            <meta name="apple-mobile-web-app-title" content="QSC Beer">
            <meta name="mobile-web-app-capable" content="yes">
        </head>
    """, unsafe_allow_html=True)
inject_pwa_meta()

# Base64 Function
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()
    
try:
    logo_base64 = get_base64("QSC_logo.png")
except Exception as e:
    logo_base64 = ""
    
# Custom CSS for the QSC Green/Gold Theme
st.markdown(f"""
 <style>
     /* Hides the top toolbar entirely */
    header {{
        visibility: hidden;
        display: none !important;
     }}
        
    /* Removes any empty top spacing left behind by the hidden header */
    .stApp {{
        margin-top: -60px;
    }}
    /* 1. Reset App Background */
    .stApp {{
        background-color: #f4f4f2;
    }}

    /* 2. Position the Logo at the Top and make it Faint */
    [data-testid="stAppViewContainer"]::before {{
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        
        /* Image Data */
        background-image: url("data:image/png;base64,{logo_base64}");
        background-repeat: no-repeat;
        background-position: top center;
        background-size: 50%; /* Adjust percentage to change logo size */
        
        /* FAINTNESS: 0.1 is very faint, 0.3 is clearly visible */
        opacity: 0.1; 
        
        z-index: 0;
        pointer-events: none; /* Allows you to click buttons 'through' the image */
    }}

    /* 3. Ensure content sits on top of the background logo */
    [data-testid="stVerticalBlock"] {{
        position: relative;
        z-index: 1;
    }}

    /* 4. Top Header Bar */
    header[data-testid="stHeader"] {{
        background-color: #1e4d2b !important; /* QSC Dark Green */
        z-index: 2;
    }}

    /* 5. Standardize Headings */
    h1 {{
        text-align: center !important;
        color: #1e4d2b;
        padding-top: 20px;
    }}

    /* 6. Sidebar Styling */
    [data-testid="stSidebar"] {{
        background-color: #1e4d2b !important;
    }}

    /* 7. Popover / Hamburger Menu */
    div[data-testid="stPopover"] > button {{
        background-color: #fdb927 !important; /* QSC Gold */
        color: #1e4d2b !important;
        border: 2px solid #1e4d2b !important;
        width: 60px;
        height: 45px;
        font-size: 24px;
        font-weight: bold;
    }}

    /* 8. Action Buttons */
    div.stButton > button {{
        background-color: #1e4d2b;
        color: white;
        border-radius: 8px;
        border: 2px solid #fdb927;
        font-weight: bold;
    }}
    
    div.stButton > button:hover {{
        background-color: #fdb927;
        color: #1e4d2b;
    }}

    /* 9. Table Styling */
    table {{
        background-color: white;
        border-radius: 10px;
        box-shadow: 0px 2px 5px rgba(0,0,0,0.1);
    }}

    /* 10. Mobile Responsiveness */
    @media (max-width: 600px) {{
        h1 {{
            font-size: 1.5rem !important;
            white-space: nowrap !important;
        }}
        [data-testid="stAppViewContainer"]::before {{
            background-size: 80%; /* Larger logo on mobile screens */
        }}
    }}
 </style>
""", unsafe_allow_html=True)

if "current_page" not in st.session_state:
    st.session_state.current_page = "Dashboard"
    
# 2. Authentication
check_login()

# 3. Database Functions (Supabase)
conn = st.connection("supabase", type=SupabaseConnection)

def write_to_db(table, columns, values):
    # Supabase expects a dictionary for inserts
    data = dict(zip([c.lower() for c in columns], values))
    conn.table(table.lower()).insert(data).execute()
    
    # Clear cache and refresh
    st.cache_data.clear()
    st.rerun()

@st.cache_data(ttl=60)
def load_data():
    # Fetch all data from Supabase tables
    users_res = conn.table("users").select("*").execute()
    beer_res = conn.table("beertransactions").select("*").execute()
    money_res = conn.table("moneytransactions").select("*").execute()
    
# 1. Load Users (with safety)
    users = pd.DataFrame(users_res.data)
    if users.empty:
        users = pd.DataFrame(columns=['email', 'name', 'role'])
    else:
        users.columns = [c.lower() for c in users.columns]

    # 2. Load Beer (with safety)
    beer_df = pd.DataFrame(beer_res.data)
    if beer_df.empty:
        # Define the exact columns your app logic needs
        beer_df = pd.DataFrame(columns=['timestamp', 'email', 'action', 'reason', 'quantity', 'note'])
    else:
        beer_df.columns = [c.lower() for c in beer_df.columns]

    # 3. Load Money (with safety)
    money_df = pd.DataFrame(money_res.data)
    if money_df.empty:
        # Define the exact columns your app logic needs
        money_df = pd.DataFrame(columns=['timestamp', 'email', 'action', 'amount', 'reason'])
    else:
        money_df.columns = [c.lower() for c in money_df.columns]
    
    return users, beer_df, money_df

# Load core data
users, beer_df, money_df = load_data()
user_info = st.session_state.user_info
# Note: 'role' and 'name' might also be lowercase in your users table
role = user_info.get('role', user_info.get('Role', 'User'))

# 5. Navigation Menu (Auto-Closing)
menu_col, spacer = st.columns([1, 2])
with menu_col:
    with st.popover("☰", key=f"nav_popover_{st.session_state.current_page}"):
        menu_options = ["Dashboard", "Leaderboard", "Beer Summary", "Money Summary"]
        if role == 'Admin':
            menu_options.extend(["Admin Panel", "Admin Summary"])
        
        for option in menu_options:
            if st.button(option, use_container_width=True, key=f"nav_btn_{option}"):
                st.session_state.current_page = option
                st.rerun()

# Define active page
page = st.session_state.current_page

# 6. Global Calculation Logic (Lowercased keys)
total_drank_out = beer_df[(beer_df['reason'] == 'Drank') & (beer_df['action'] == 'OUT')]['quantity'].sum()
total_drank_corr = beer_df[(beer_df['reason'] == 'Drank Correction') & (beer_df['action'] == 'IN')]['quantity'].sum()
net_drank_all = total_drank_out - total_drank_corr

total_don_in = beer_df[(beer_df['reason'] == 'Donation') & (beer_df['action'] == 'IN')]['quantity'].sum()
total_don_corr = beer_df[(beer_df['reason'] == 'Donation Correction') & (beer_df['action'] == 'OUT')]['quantity'].sum()
net_donated_all = total_don_in - total_don_corr

# 7. PAGE LOGIC
if page == "Dashboard":
    st.title(f"Welcome, {user_info.get('name', user_info.get('Name'))}")
    
    if st.session_state.get('show_success'):
        st.toast("Beer Taken, Cheers! 🍻", icon="✅")
        st.session_state.show_success = False

    if st.button("🍺 Beer Taken", use_container_width=True):
        st.session_state.show_success = True
        write_to_db(
            "beertransactions", 
            ['timestamp', 'email', 'action', 'reason', 'quantity', 'note'], 
            [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), user_info.get('email', user_info.get('Email')), 'OUT', 'Drank', 1, 'Beer Taken']
        )
    
    u_beer = beer_df[beer_df['email'] == user_info.get('email', user_info.get('Email'))]
    u_money = money_df[money_df['email'] == user_info.get('email', user_info.get('Email'))]
    
    drank = (u_beer[(u_beer['action'] == 'OUT') & (u_beer['reason'] == 'Drank')]['quantity'].sum() - 
             u_beer[(u_beer['action'] == 'IN') & (u_beer['reason'] == 'Drank Correction')]['quantity'].sum())
    
    donated = (u_beer[(u_beer['action'] == 'IN') & (u_beer['reason'] == 'Donation')]['quantity'].sum() - 
               u_beer[(u_beer['action'] == 'OUT') & (u_beer['reason'] == 'Donation Correction')]['quantity'].sum())
    
    paid = u_money[u_money['reason'] == 'Payment']['amount'].sum() - u_money[u_money['reason'] == 'Refund']['amount'].sum()
    
    st.markdown(f"""
    <table style="width:100%; border:none; border-collapse:collapse;">
        <tr><td style="padding:10px;"><b>Beer Drank</b></td><td style="text-align:right; padding:10px;">{int(drank)}</td></tr>
        <tr><td style="padding:10px;"><b>Beer Donated</b></td><td style="text-align:right; padding:10px;">{int(donated)}</td></tr>
        <tr><td style="padding:10px;"><b>Beer Cost</b></td><td style="text-align:right; padding:10px;">${drank * 3:.2f}</td></tr>
        <tr><td style="padding:10px;"><b>Money Paid</b></td><td style="text-align:right; padding:10px;">${paid:.2f}</td></tr>
        <tr><td style="padding:10px; border-top: 1px solid #ddd;"><b>Balance</b></td><td style="text-align:right; padding:10px; border-top: 1px solid #ddd;"><b>${paid - (drank * 3):.2f}</b></td></tr>
    </table>
    """, unsafe_allow_html=True)
    
elif page == "Leaderboard":
    st.title("🏆 Leaderboard")
    drank_transactions = beer_df[beer_df['reason'] == 'Drank']
    out_drank = drank_transactions[drank_transactions['action'] == 'OUT'].groupby('email')['quantity'].sum()
    in_corr = beer_df[(beer_df['reason'] == 'Drank Correction') & (beer_df['action'] == 'IN')].groupby('email')['quantity'].sum()
    totals = pd.concat([out_drank, in_corr], axis=1).fillna(0)
    totals.columns = ['out', 'in']
    totals['net'] = totals['out'] - totals['in']
    
    # Matching lowercase email/name from users table
    lb = users[['email', 'name']].merge(totals['net'].reset_index(), on='email', how='left').fillna(0)
    lb = lb.rename(columns={'name': 'Player', 'net': 'Beer Drank'})
    lb['Beer Drank'] = lb['Beer Drank'].astype(int)
    lb = lb[lb['Player'] != 'System'].sort_values(by='Beer Drank', ascending=False).reset_index(drop=True)
    lb.insert(0, 'Rank', range(1, len(lb) + 1))
    st.table(lb[['Rank', 'Player', 'Beer Drank']])

elif page == "Beer Summary":
    st.title("🍺 Beer Summary")
    league = int(beer_df[beer_df['reason'] == 'League Donation']['quantity'].sum())
    bought = int(beer_df[beer_df['reason'] == 'Bought']['quantity'].sum())
    shrink = int(beer_df[beer_df['reason'] == 'Shrinkage']['quantity'].sum())
    d_in = beer_df[(beer_df['reason'] == 'Donation') & (beer_df['action'] == 'IN')]['quantity'].sum()
    d_corr = beer_df[(beer_df['reason'] == 'Donation Correction') & (beer_df['action'] == 'OUT')]['quantity'].sum()
    net_donated = d_in - d_corr
    drk_out = beer_df[(beer_df['reason'] == 'Drank') & (beer_df['action'] == 'OUT')]['quantity'].sum()
    drk_corr = beer_df[(beer_df['reason'] == 'Drank Correction') & (beer_df['action'] == 'IN')]['quantity'].sum()
    net_drank = drk_out - drk_corr
    total_in = league + net_donated + bought
    on_hand = total_in - net_drank - shrink

    st.markdown(f"""<table style="width:100%; border:none; border-collapse:collapse;">
        <tr><td style="padding:10px;"><b>League Donations</b></td><td style="text-align:right; padding:10px;">{league}</td></tr>
        <tr><td style="padding:10px;"><b>Player Donations</b></td><td style="text-align:right; padding:10px;">{int(net_donated)}</td></tr>
        <tr><td style="padding:10px;"><b>Bought</b></td><td style="text-align:right; padding:10px;">{bought}</td></tr>
        <tr><td style="padding:10px;"><b>Total Beer In</b></td><td style="text-align:right; padding:10px;">{int(total_in)}</td></tr>
        <tr><td style="padding:10px;"><b>Net Drank</b></td><td style="text-align:right; padding:10px;">{int(net_drank)}</td></tr>
        <tr><td style="padding:10px;"><b>Shrinkage</b></td><td style="text-align:right; padding:10px;">{shrink}</td></tr>
        <tr><td style="padding:10px; border-top: 1px solid #ddd;"><b>On Hand</b></td><td style="text-align:right; padding:10px; border-top: 1px solid #ddd;"><b>{int(on_hand)}</b></td></tr>
    </table>""", unsafe_allow_html=True)

elif page == "Money Summary":
    st.title("💰 Money Summary")
    total_owed = net_drank_all * 3
    paid = money_df[money_df['reason'] == 'Payment']['amount'].sum() - money_df[money_df['reason'] == 'Refund']['amount'].sum()
    expense_total = money_df[(money_df['reason'] == 'Expense') & (money_df['action'] == 'OUT')]['amount'].sum()
    expense_refunds = money_df[(money_df['reason'] == 'Expense') & (money_df['action'] == 'IN')]['amount'].sum()
    expenses = expense_total - expense_refunds
    st.markdown(f"""<table style="width:100%; border:none; border-collapse:collapse;">
        <tr><td style="padding:10px;"><b>Total Owed</b></td><td style="text-align:right; padding:10px;">${total_owed:.2f}</td></tr>
        <tr><td style="padding:10px;"><b>Paid</b></td><td style="text-align:right; padding:10px;">${paid:.2f}</td></tr>
        <tr><td style="padding:10px;"><b>Balance</b></td><td style="text-align:right; padding:10px;">${paid - total_owed:.2f}</td></tr>
        <tr><td style="padding:10px;"><b>Expenses</b></td><td style="text-align:right; padding:10px;">${expenses:.2f}</td></tr>
        <tr><td style="padding:10px; border-top: 1px solid #ddd;"><b>Kitty</b></td><td style="text-align:right; padding:10px; border-top: 1px solid #ddd;"><b>${paid - expenses:.2f}</b></td></tr>
    </table>""", unsafe_allow_html=True)

elif page == "Admin Summary":
    st.title("📊 Admin Summary")
    summary_list = []
    t_don, t_drk, t_cst, t_pd, t_bal = 0, 0, 0.0, 0.0, 0.0
    for _, user in users.iterrows():
        u_beer = beer_df[beer_df['email'] == user['email']]
        u_money = money_df[money_df['email'] == user['email']]
        drank = (u_beer[(u_beer['action'] == 'OUT') & (u_beer['reason'] == 'Drank')]['quantity'].sum() - u_beer[(u_beer['action'] == 'IN') & (u_beer['reason'] == 'Drank Correction')]['quantity'].sum())
        donated = (u_beer[(u_beer['action'] == 'IN') & (u_beer['reason'] == 'Donation')]['quantity'].sum() - u_beer[(u_beer['action'] == 'OUT') & (u_beer['reason'] == 'Donation Correction')]['quantity'].sum())
        paid = u_money[u_money['reason'] == 'Payment']['amount'].sum() - u_money[u_money['reason'] == 'Refund']['amount'].sum()
        bal = paid - (drank * 3)
        summary_list.append({"Name": user['name'], "Beer Donated": int(donated), "Beer Drank": int(drank), "Beer Cost": drank * 3, "Money Paid": paid, "Balance": bal})
        t_don += int(donated); t_drk += int(drank); t_cst += (drank * 3); t_pd += paid; t_bal += bal
    df = pd.DataFrame(summary_list)
    t_row = pd.DataFrame({"Name": ["**TOTAL**"], "Beer Donated": [f"**{t_don}**"], "Beer Drank": [f"**{t_drk}**"], "Beer Cost": [f"**${t_cst:.2f}**"], "Money Paid": [f"**${t_pd:.2f}**"], "Balance": [f"**${t_bal:.2f}**"]})
    df['Beer Cost'] = df['Beer Cost'].apply(lambda x: f"${x:.2f}"); df['Money Paid'] = df['Money Paid'].apply(lambda x: f"${x:.2f}"); df['Balance'] = df['Balance'].apply(lambda x: f"${x:.2f}")
    st.table(pd.concat([df, t_row], ignore_index=True))

elif page == "Admin Panel":
    st.title("🛠️ Admin Tasks")
    tab1, tab2, tab3 = st.tabs(["Player Adjustments", "Add/Remove Beer", "Expenses"])
    
    with tab1:
        selected_user_name = st.selectbox("Select User to Adjust",options=sorted(users['name'].unique()),filter_mode=None)
        selected_user = users[users['name'] == selected_user_name].iloc[0]
        u_beer = beer_df[beer_df['email'] == selected_user['email']]
        u_money = money_df[money_df['email'] == selected_user['email']]
        drank = (u_beer[(u_beer['action'] == 'OUT') & (u_beer['reason'] == 'Drank')]['quantity'].sum() - u_beer[(u_beer['action'] == 'IN') & (u_beer['reason'] == 'Drank Correction')]['quantity'].sum())
        donated = (u_beer[(u_beer['action'] == 'IN') & (u_beer['reason'] == 'Donation')]['quantity'].sum() - u_beer[(u_beer['action'] == 'OUT') & (u_beer['reason'] == 'Donation Correction')]['quantity'].sum())
        paid = u_money[u_money['reason'] == 'Payment']['amount'].sum() - u_money[u_money['reason'] == 'Refund']['amount'].sum()
        
        st.markdown(f"""<table style="width:100%; border:none; border-collapse:collapse;">
            <tr><td style="padding:10px;"><b>Beer Drank</b></td><td style="text-align:right; padding:10px;">{int(drank)}</td></tr>
            <tr><td style="padding:10px;"><b>Beer Donated</b></td><td style="text-align:right; padding:10px;">{int(donated)}</td></tr>
            <tr><td style="padding:10px;"><b>Beer Cost</b></td><td style="text-align:right; padding:10px;">${drank * 3:.2f}</td></tr>
            <tr><td style="padding:10px;"><b>Money Paid</b></td><td style="text-align:right; padding:10px;">${paid:.2f}</td></tr>
            <tr><td style="padding:10px; border-top: 1px solid #ddd;"><b>Balance</b></td><td style="text-align:right; padding:10px; border-top: 1px solid #ddd;"><b>${paid - (drank * 3):.2f}</b></td></tr>
        </table>""", unsafe_allow_html=True)
        
        st.divider()
        col1, col2 = st.columns(2)
        if col1.button("Beer Taken"): write_to_db("beertransactions", ['timestamp', 'email', 'action', 'reason', 'quantity', 'note'], [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), selected_user['email'], 'OUT', 'Drank', 1, 'Admin Adjust'])
        if col1.button("Refund Beer Taken"): write_to_db("beertransactions", ['timestamp', 'email', 'action', 'reason', 'quantity', 'note'], [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), selected_user['email'], 'IN', 'Drank Correction', 1, 'Admin Adjust'])
        
        d_qty = col2.number_input("Quantity", min_value=1, value=3, key="adj_qty")
        if col2.button("Beer Donated"): write_to_db("beertransactions", ['timestamp', 'email', 'action', 'reason', 'quantity', 'note'], [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), selected_user['email'], 'IN', 'Donation', d_qty, 'Admin'])
        if col2.button("Refund Beer Donated"): write_to_db("beertransactions", ['timestamp', 'email', 'action', 'reason', 'quantity', 'note'], [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), selected_user['email'], 'OUT', 'Donation Correction', d_qty, 'Admin'])
        
        st.divider()
        amt = st.number_input("Amount ($)", min_value=0.0, key="adj_amt")
        if st.button("Enter Payment"): write_to_db("moneytransactions", ['timestamp', 'email', 'action', 'amount', 'reason'], [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), selected_user['email'], 'IN', amt, 'Payment'])
        if st.button("Enter Refund"): write_to_db("moneytransactions", ['timestamp', 'email', 'action', 'amount', 'reason'], [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), selected_user['email'], 'OUT', amt, 'Refund'])
    
    with tab2:
        league = int(beer_df[beer_df['reason'] == 'League Donation']['quantity'].sum())
        bought = int(beer_df[beer_df['reason'] == 'Bought']['quantity'].sum())
        shrink = int(beer_df[beer_df['reason'] == 'Shrinkage']['quantity'].sum())
        net_drank_sys = (beer_df[(beer_df['reason'] == 'Drank') & (beer_df['action'] == 'OUT')]['quantity'].sum() - beer_df[(beer_df['reason'] == 'Drank Correction') & (beer_df['action'] == 'IN')]['quantity'].sum())
        net_donated_sys = (beer_df[(beer_df['reason'] == 'Donation') & (beer_df['action'] == 'IN')]['quantity'].sum() - beer_df[(beer_df['reason'] == 'Donation Correction') & (beer_df['action'] == 'OUT')]['quantity'].sum())
        total_in_sys = league + net_donated_sys + bought
        
        st.markdown(f"""<table style="width:100%; border:none; border-collapse:collapse;">
            <tr><td style="padding:10px;"><b>League</b></td><td style="text-align:right; padding:10px;">{league}</td></tr>
            <tr><td style="padding:10px;"><b>Player Don.</b></td><td style="text-align:right; padding:10px;">{int(net_donated_sys)}</td></tr>
            <tr><td style="padding:10px;"><b>Bought</b></td><td style="text-align:right; padding:10px;">{bought}</td></tr>
            <tr><td style="padding:10px;"><b>Total In</b></td><td style="text-align:right; padding:10px;">{int(total_in_sys)}</td></tr>
            <tr><td style="padding:10px;"><b>Net Drank</b></td><td style="text-align:right; padding:10px;">{int(net_drank_sys)}</td></tr>
            <tr><td style="padding:10px;"><b>Shrinkage</b></td><td style="text-align:right; padding:10px;">{shrink}</td></tr>
            <tr><td style="padding:10px; border-top: 1px solid #ddd;"><b>On Hand</b></td><td style="text-align:right; padding:10px; border-top: 1px solid #ddd;"><b>{int(total_in_sys - net_drank_sys - shrink)}</b></td></tr>
        </table>""", unsafe_allow_html=True)
        
        st.divider()
        qty = st.number_input("System Qty", min_value=1, step=1, key="sys_qty")
        if st.button("Add League Donation"): write_to_db("beertransactions", ['timestamp', 'email', 'reason', 'quantity'], [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'System', 'League Donation', qty])
        if st.button("Add Bought"): write_to_db("beertransactions", ['timestamp', 'email', 'reason', 'quantity'], [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'System', 'Bought', qty])
        if st.button("Remove Shrinkage"): write_to_db("beertransactions", ['timestamp', 'email', 'action', 'reason', 'quantity'], [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'System', 'OUT', 'Shrinkage', qty])
    
    with tab3:
        total_owed_sys = net_drank_all * 3
        paid_sys = money_df[money_df['reason'] == 'Payment']['amount'].sum() - money_df[money_df['reason'] == 'Refund']['amount'].sum()
        expense_total_sys = money_df[(money_df['reason'] == 'Expense') & (money_df['action'] == 'OUT')]['amount'].sum()
        expense_refunds_sys = money_df[(money_df['reason'] == 'Expense') & (money_df['action'] == 'IN')]['amount'].sum()
        expenses_sys = expense_total_sys - expense_refunds_sys
        
        st.markdown(f"""<table style="width:100%; border:none; border-collapse:collapse;">
            <tr><td style="padding:10px;"><b>Total Owed</b></td><td style="text-align:right; padding:10px;">${total_owed_sys:.2f}</td></tr>
            <tr><td style="padding:10px;"><b>Paid</b></td><td style="text-align:right; padding:10px;">${paid_sys:.2f}</td></tr>
            <tr><td style="padding:10px;"><b>Balance</b></td><td style="text-align:right; padding:10px;">${paid_sys - total_owed_sys:.2f}</td></tr>
            <tr><td style="padding:10px;"><b>Expenses</b></td><td style="text-align:right; padding:10px;">${expenses_sys:.2f}</td></tr>
            <tr><td style="padding:10px; border-top: 1px solid #ddd;"><b>Kitty</b></td><td style="text-align:right; padding:10px; border-top: 1px solid #ddd;"><b>${paid_sys - expenses_sys:.2f}</b></td></tr>
        </table>""", unsafe_allow_html=True)
        
        st.divider()
        exp = st.number_input("Expense Amount", min_value=0.0, key="exp_amt")
        if st.button("Add Expense"): write_to_db("moneytransactions", ['timestamp', 'email', 'action', 'amount', 'reason'], [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'System', 'OUT', exp, 'Expense'])
        if st.button("Refund Expense"): write_to_db("moneytransactions", ['timestamp', 'email', 'action', 'amount', 'reason'], [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'System', 'IN', exp, 'Expense'])
