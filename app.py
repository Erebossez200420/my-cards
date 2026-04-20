import streamlit as st
import pandas as pd
import gspread
import requests
import base64
from google.oauth2.service_account import Credentials

# --- CONFIG & SECRETS ---
IMGBB_API_KEY = "4988b58d7f17cd1e55f0dfca0d13ecb6"
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTJncpOFgpWjWoU0kXjPoPeqj3pvrppiy0MeBNHIP2tv7pGQREloJB4CCw0UNONN4R64W6BBJS61VTO/pub?output=csv"
SHEET_NAME_URL = "https://docs.google.com/spreadsheets/d/1oiHsqmiqd5b159EAuIZ2DcyhjoYCpXDYftQnsVq6RRA/edit"

def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

def upload_to_imgbb(file):
    try:
        url = "https://api.imgbb.com/1/upload"
        payload = {"key": IMGBB_API_KEY, "image": base64.b64encode(file.read()).decode('utf-8')}
        res = requests.post(url, payload)
        return res.json()['data']['url']
    except: return None

# --- UI DESIGN SYSTEM v10 (IPHONE NATIVE FEEL) ---
st.set_page_config(page_title="ULTRA VAULT", layout="wide", page_icon="📟")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;800&display=swap');
    
    /* Clean Base */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #0a0a0c; font-family: 'Plus Jakarta Sans', sans-serif; }
    
    /* Remove unnecessary lines from Streamlit */
    hr { border: none !important; margin: 10px 0 !important; }
    .stSelectbox div[data-baseweb="select"] { border: none !important; background: #16161a !important; border-radius: 12px !important; }
    .stTextInput input { border: none !important; background: #16161a !important; border-radius: 12px !important; color: white !important; }

    /* Premium Metric Style */
    [data-testid="stMetric"] {
        background: #16161a; border-radius: 20px; padding: 20px; border: none !important;
    }
    [data-testid="stMetricValue"] { color: #00ffcc !important; font-weight: 800 !important; }
    [data-testid="stMetricLabel"] { color: #8e8e93 !important; font-size: 13px !important; }

    /* iPhone Modern Card */
    .card-box {
        background: #16161a;
        border-radius: 24px;
        padding: 16px;
        margin-bottom: 15px;
        box-shadow: 0 4px 20px rgba(0,0,0,0.3);
    }
    .card-title { color: #ffffff; font-size: 14px; font-weight: 700; height: 38px; overflow: hidden; margin-top: 10px; }
    .card-price { color: #00ffcc; font-size: 22px; font-weight: 800; font-family: monospace; }
    
    /* Custom High Contrast Buttons */
    .stButton button {
        background: #00ffcc !important; color: #000000 !important;
        border-radius: 16px !important; height: 3.8rem !important;
        font-weight: 800 !important; border: none !important; width: 100% !important;
    }
    
    /* Floating Action style for New Asset */
    .add-btn button { background: #ffffff !important; color: #000000 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINE ---
@st.cache_data(ttl=5)
def load_data():
    try:
        raw = pd.read_csv(SHEET_URL)
        for col in ['Quantity', 'Buy_Price', 'Grade_Fee', 'Market_Price', 'Sell_Price']:
            if col in raw.columns:
                raw[col] = pd.to_numeric(raw[col].astype(str).str.replace(',', '').str.replace('$', ''), errors='coerce').fillna(0)
        raw['gsheet_row'] = raw.index + 2
        raw['Cost_Total'] = raw['Buy_Price'] + raw['Grade_Fee']
        raw['Current_Val'] = raw.apply(lambda x: x['Sell_Price'] if x['Status'] == 'Sold' else x['Market_Price'], axis=1)
        raw['Profit'] = (raw['Current_Val'] - raw['Cost_Total']) * raw['Quantity']
        raw['ROI'] = (raw['Profit'] / (raw['Cost_Total'] * raw['Quantity']).replace(0, 0.01)) * 100
        return raw
    except: return pd.DataFrame()

df = load_data()

# --- HEADER & STATS ---
st.markdown("<h2 style='text-align: center; margin-top: -20px;'>📟 VAULT TERMINAL</h2>", unsafe_allow_html=True)

if not df.empty:
    m1, m2, m3 = st.columns(3)
    active_df = df[df['Status'] != 'Sold']
    m1.metric("VAULT", f"${(active_df['Cost_Total'] * active_df['Quantity']).sum():,.0f}")
    m2.metric("PROFIT", f"${df['Profit'].sum():,.0f}", delta=f"{df['Profit'].sum():+.0f}")
    m3.metric("ROI", f"{df['ROI'].mean():+.1f}%")

    st.divider()

    # --- SINGLE VIEW ARCHITECTURE ---
    tab_view, tab_add = st.tabs(["🖼️ PORTFOLIO", "➕ ADD NEW"])

    with tab_view:
        # Mini Toolbar
        t1, t2 = st.columns([0.6, 0.4])
        query = t1.text_input("🔍 Search", placeholder="Find card...")
        sort_opt = t2.selectbox("Sort", ["Latest", "ROI %", "Price"])

        # Display Logic
        view_df = df.copy()
        if query:
            view_df = view_df[view_df['Card_Name'].str.contains(query, case=False, na=False)]
        
        if sort_opt == "ROI %": view_df = view_df.sort_values('ROI', ascending=False)
        elif sort_opt == "Price": view_df = view_df.sort_values('Current_Val', ascending=False)
        else: view_df = view_df.sort_index(ascending=False)

        # Portfolio Grid
        grid = st.columns(2)
        for i in range(len(view_df)):
            row = view_df.iloc[i]
            with grid[i % 2]:
                st.markdown(f'''
                    <div class="card-box">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="color:{'#00ffcc' if row['Status'] != 'Sold' else '#ff4444'}; font-size:10px; font-weight:800;">● {row['Status'].upper()}</span>
                            <span style="color:#ffffff; font-size:12px; font-weight:800;">{row['ROI']:+.1f}%</span>
                        </div>
                        <div class="card-title">{row['Card_Name']}</div>
                ''', unsafe_allow_html=True)
                
                st.image(row['Image_URL'] if pd.notna(row['Image_URL']) else "https://via.placeholder.com/300/16161a/333?text=NO+IMAGE", use_container_width=True)
                
                st.markdown(f'''
                        <div style="margin-top:10px; text-align:center;">
                            <div class="card-price">${row['Current_Val']:,.2f}</div>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)
                
                # THE MAGIC BUTTON: Edit inside the card
                if st.button(f"EDIT DATA", key=f"edit_{row['gsheet_row']}"):
                    st.session_state.edit_mode = row['gsheet_row']

        # --- MODAL-STYLE EDIT OVERLAY ---
        if 'edit_mode' in st.session_state:
            target_row = df[df['gsheet_row'] == st.session_state.edit_mode].iloc[0]
            st.markdown(f"### ⚙️ Managing: {target_row['Card_Name']}")
            
            with st.form("quick_edit"):
                c1, c2 = st.columns(2)
                with c1:
                    u_mkt = st.number_input("Market Value ($)", value=float(target_row['Market_Price']))
                    u_qty = st.number_input("Quantity", value=int(target_row['Quantity']))
                    u_sta = st.selectbox("Status", ["Active", "Sold"], index=0 if target_row['Status'] != 'Sold' else 1)
                with c2:
                    u_sel = st.number_input("Sold For ($)", value=float(target_row['Sell_Price']))
                    u_fee = st.number_input("Grade Fee ($)", value=float(target_row['Grade_Fee']))
                    u_grd = st.text_input("Grade Score", value=str(target_row['Grade_Score']))
                
                u_img = st.file_uploader("Update Photo", type=['jpg', 'png'])
                
                eb1, eb2 = st.columns(2)
                if eb1.form_submit_button("💾 SAVE CHANGES"):
                    client = get_gspread_client()
                    sh = client.open_by_url(SHEET_NAME_URL).sheet1
                    r = int(target_row['gsheet_row'])
                    sh.update_cell(r, 8, u_mkt); sh.update_cell(r, 11, u_sel); sh.update_cell(r, 12, u_sta)
                    sh.update_cell(r, 5, u_qty); sh.update_cell(r, 9, u_grd); sh.update_cell(r, 7, u_fee)
                    if u_img:
                        url = upload_to_imgbb(u_img)
                        if url: sh.update_cell(r, 10, url)
                    del st.session_state.edit_mode
                    st.cache_data.clear(); st.rerun()
                
                if eb2.form_submit_button("❌ CANCEL"):
                    del st.session_state.edit_mode
                    st.rerun()

    with tab_add:
        with st.form("add_new_iphone"):
            st.subheader("➕ Register Asset")
            a_name = st.text_input("Card Name")
            a_set = st.text_input("Set Name")
            ac1, ac2 = st.columns(2)
            with ac1:
                a_buy = st.number_input("Buy ($)")
                a_mkt = st.number_input("Market ($)")
            with ac2:
                a_qty = st.number_input("Qty", value=1)
                a_fee = st.number_input("Fee ($)")
            
            a_grd = st.text_input("Grade Score")
            a_id = st.text_input("Serial ID")
            a_file = st.file_uploader("Take Photo", type=['jpg', 'png', 'jpeg'])
            
            if st.form_submit_button("🚀 DEPLOY TO VAULT"):
                if a_name and a_file:
                    url = upload_to_imgbb(a_file)
                    if url:
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        sh.append_row([a_id, "Card", a_name, a_set, int(a_qty), a_buy, a_fee, a_mkt, a_grd, url, 0, "Active"])
                        st.cache_data.clear(); st.rerun()
                else: st.warning("Name & Photo required.")

else:
    st.info("VAULT DISCONNECTED. CHECK SHEETS.")
