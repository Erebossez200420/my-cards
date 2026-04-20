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

# --- UI DESIGN SYSTEM v13 (TOTAL CONTROL) ---
st.set_page_config(page_title="THE VAULT PRO", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #0d1117; font-family: 'Inter', sans-serif; }
    h1, h2, h3 { color: #ffffff !important; font-weight: 800 !important; }
    p, span, label { color: #f0f6fc !important; font-weight: 600 !important; }
    
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: #161b22 !important; color: #ffffff !important; 
        border: 1px solid #30363d !important; border-radius: 10px !important;
    }
    
    [data-testid="stMetric"] { background: #161b22; border: 1px solid #30363d; border-radius: 16px; padding: 20px; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: 800 !important; }

    .st-expander { background-color: #0d1117 !important; border: 1px solid #30363d !important; border-radius: 12px !important; margin-bottom: 10px !important; }

    /* Button Themes */
    .stButton button { border-radius: 10px !important; font-weight: 700 !important; height: 3rem; width: 100%; }
    .btn-sync button { background: #238636 !important; color: white !important; border: none; }
    .btn-update button { background: #1f6feb !important; color: white !important; border: none; }
    .btn-delete button { background: #da3633 !important; color: white !important; border: none; }
    
    .p-bar-bg { background: #30363d; height: 10px; border-radius: 5px; width: 100%; margin: 12px 0; }
    .p-bar-fill { height: 100%; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA ENGINE ---
@st.cache_data(ttl=5)
def load_data():
    try:
        raw = pd.read_csv(SHEET_URL)
        # บันทึก Row Index เริ่มต้น (Row 1 คือ Header ดังนั้น Index 0 ใน DF คือ Row 2 ใน Sheet)
        raw['gsheet_row'] = raw.index + 2
        
        for col in ['Quantity', 'Buy_Price', 'Grade_Fee', 'Market_Price', 'Sell_Price']:
            if col in raw.columns:
                raw[col] = pd.to_numeric(raw[col].astype(str).str.replace(',', '').str.replace('$', ''), errors='coerce').fillna(0)
        
        raw['Unit_Cost'] = raw['Buy_Price'] + raw['Grade_Fee']
        raw['Total_Cost'] = raw['Unit_Cost'] * raw['Quantity']
        raw['Current_Price'] = raw.apply(lambda x: x['Sell_Price'] if x['Status'] == 'Sold' else x['Market_Price'], axis=1)
        raw['Total_Value'] = raw['Current_Price'] * raw['Quantity']
        raw['Net_Profit'] = raw['Total_Value'] - raw['Total_Cost']
        raw['ROI_Pct'] = (raw['Net_Profit'] / raw['Total_Cost'].replace(0, 0.01)) * 100
        return raw
    except: return pd.DataFrame()

df = load_data()

# --- TOP NAVIGATION ---
t_col1, t_col2 = st.columns([0.7, 0.3])
with t_col1:
    st.markdown("<h1 style='margin-bottom:0;'>VAULT ELITE v13</h1>", unsafe_allow_html=True)
with t_col2:
    st.markdown('<div class="btn-sync">', unsafe_allow_html=True)
    if st.button("🔄 SYNC DATA"):
        st.cache_data.clear()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

if not df.empty:
    # Stats Overview
    m1, m2, m3 = st.columns(3)
    m1.metric("PORTFOLIO VALUE", f"${df[df['Status'] != 'Sold']['Total_Value'].sum():,.0f}")
    m2.metric("NET PROFIT", f"${df['Net_Profit'].sum():,.0f}", delta=f"{df['Net_Profit'].sum():+.0f}")
    m3.metric("ALL-TIME ROI", f"{(df['Net_Profit'].sum() / df['Total_Cost'].sum() * 100 if df['Total_Cost'].sum() > 0 else 0):+.1f}%")

    st.divider()

    # Search & Sort
    f_col1, f_col2 = st.columns([0.6, 0.4])
    with f_col1: search_q = st.text_input("🔍 Search", placeholder="Find asset...")
    with f_col2: sort_opt = st.selectbox("Order By", ["Latest", "Profit", "ROI %"])

    view_df = df.copy()
    if search_q: view_df = view_df[view_df['Card_Name'].str.contains(search_q, case=False, na=False)]
    
    if sort_opt == "Profit": view_df = view_df.sort_values('Net_Profit', ascending=False)
    elif sort_opt == "ROI %": view_df = view_df.sort_values('ROI_Pct', ascending=False)
    else: view_df = view_df.sort_index(ascending=False)

    # Asset Display
    for idx, row in view_df.iterrows():
        roi_clr = "#3fb950" if row['ROI_Pct'] >= 0 else "#f85149"
        with st.expander(f"{row['Card_Name']} ┃ {row['ROI_Pct']:+.1f}%", expanded=False):
            c_left, c_right = st.columns([0.4, 0.6])
            with c_left:
                st.image(row['Image_URL'] if pd.notna(row['Image_URL']) else "https://via.placeholder.com/300/161b22/30363d", use_container_width=True)
            with c_right:
                # Value Progress
                safe_cost = max(row['Unit_Cost'], 0.01)
                meter_w = min(max((row['Current_Price'] / safe_cost) * 50, 5), 100)
                st.markdown(f'''
                    <div style="font-size:12px; color:#8b949e;">VALUE PROGRESSION</div>
                    <div class="p-bar-bg"><div class="p-bar-fill" style="width:{meter_w}%; background:{roi_clr};"></div></div>
                ''', unsafe_allow_html=True)
                
                st.markdown(f"**Live Value:** ${row['Current_Price']:,.2f} | **P/L:** <span style='color:{roi_clr};'>${row['Net_Profit']:,.2f}</span>", unsafe_allow_html=True)
                
                # --- MANAGE POPOVER ---
                with st.popover("⚙️ MANAGE ASSET"):
                    # 1. Update Form
                    with st.form(f"update_{row['gsheet_row']}"):
                        st.markdown("#### Update Data")
                        u_mkt = st.number_input("Market ($)", value=float(row['Market_Price']))
                        u_sel = st.number_input("Sold ($)", value=float(row['Sell_Price']))
                        u_sta = st.selectbox("Status", ["Active", "Sold"], index=0 if row['Status'] != 'Sold' else 1)
                        u_qty = st.number_input("Qty", value=int(row['Quantity']))
                        u_fee = st.number_input("Fee ($)", value=float(row['Grade_Fee']))
                        u_grd = st.text_input("Grade", value=str(row['Grade_Score']))
                        u_img = st.file_uploader("New Photo", type=['jpg', 'png'])
                        
                        st.markdown('<div class="btn-update">', unsafe_allow_html=True)
                        if st.form_submit_button("💾 SAVE CHANGES"):
                            client = get_gspread_client()
                            sh = client.open_by_url(SHEET_NAME_URL).sheet1
                            r_num = int(row['gsheet_row'])
                            sh.update_cell(r_num, 8, u_mkt); sh.update_cell(r_num, 11, u_sel); sh.update_cell(r_num, 12, u_sta)
                            sh.update_cell(r_num, 5, u_qty); sh.update_cell(r_num, 9, u_grd); sh.update_cell(r_num, 7, u_fee)
                            if u_img:
                                url = upload_to_imgbb(u_img)
                                if url: sh.update_cell(r_num, 10, url)
                            st.cache_data.clear(); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.divider()
                    
                    # 2. Delete Section
                    st.markdown("#### 🗑️ Dangerous Area")
                    confirm_del = st.checkbox(f"Confirm Delete: {row['Card_Name']}", key=f"del_chk_{row['gsheet_row']}")
                    st.markdown('<div class="btn-delete">', unsafe_allow_html=True)
                    if st.button("🗑️ REMOVE FROM VAULT", key=f"del_btn_{row['gsheet_row']}", disabled=not confirm_del):
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        r_num = int(row['gsheet_row'])
                        if r_num > 1: # Protection for Header
                            sh.delete_rows(r_num)
                            st.success(f"Row {r_num} removed successfully.")
                            st.cache_data.clear(); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # ADD NEW
    st.divider()
    with st.expander("➕ REGISTER NEW ASSET", expanded=False):
        with st.form("add_v13", clear_on_submit=True):
            a_name = st.text_input("Asset Name")
            a_set = st.text_input("Set Name")
            c1, c2 = st.columns(2)
            with c1:
                a_buy = st.number_input("Buy ($)")
                a_mkt = st.number_input("Market ($)")
            with c2:
                a_qty = st.number_input("Quantity", value=1)
                a_fee = st.number_input("Fee ($)")
            a_grd = st.text_input("Grade")
            a_id = st.text_input("Serial ID")
            a_file = st.file_uploader("Capture Image", type=['jpg', 'png', 'jpeg'])
            
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
    st.info("System Ready. Waiting for Data...")
