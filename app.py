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

# --- UI STEALTH DESIGN ---
st.set_page_config(page_title="VAULT 7.9 | BOSS TANG", layout="wide", page_icon="📟")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #0b0c10; color: #E0E0E0; }
    
    /* Text Readability Enhancement */
    h1, h2, h3 { color: #00f2ff !important; }
    p, span, label { color: #ffffff !important; font-weight: 500; }
    [data-testid="stMetricValue"] { color: #00f2ff !important; font-family: 'Courier New', monospace; }
    [data-testid="stMetricLabel"] { color: #aaaaaa !important; }

    /* Premium Card Look */
    .card-frame { 
        border: 1px solid #1f2833; padding: 16px; border-radius: 20px; 
        background: #11141a; box-shadow: 0 8px 20px rgba(0,0,0,0.4);
        text-align: center; margin-bottom: 20px; 
    }
    
    .status-badge { font-size: 10px; font-weight: 800; padding: 4px 12px; border-radius: 50px; }
    .active-badge { border: 1px solid #00ff88; color: #00ff88 !important; }
    .sold-badge { border: 1px solid #ff4444; color: #ff4444 !important; }
    
    /* Button & Form */
    .stButton button { 
        border-radius: 15px; background: #45a29e; color: #0b0c10 !important; 
        font-weight: 700; height: 3.5em; width: 100%; border: none;
    }
    .stTabs [aria-selected="true"] { background-color: #45a29e !important; color: #0b0c10 !important; border-radius: 10px 10px 0 0; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA PROCESSING ---
@st.cache_data(ttl=5)
def load_data():
    try:
        raw = pd.read_csv(SHEET_URL)
        # Ensure correct row indexing for GSpread (starting at 2)
        raw['gsheet_row'] = raw.index + 2
        
        for col in ['Quantity', 'Buy_Price', 'Grade_Fee', 'Market_Price', 'Sell_Price']:
            if col in raw.columns:
                raw[col] = pd.to_numeric(raw[col].astype(str).str.replace(',', '').str.replace('$', ''), errors='coerce').fillna(0)
        
        raw['Unit_Cost'] = raw['Buy_Price'] + raw_df['Grade_Fee'] if 'Grade_Fee' in raw else raw['Buy_Price']
        raw['Current_Val'] = raw.apply(lambda x: x['Sell_Price'] if x['Status'] == 'Sold' else x['Market_Price'], axis=1)
        raw['Profit'] = (raw['Current_Val'] - raw['Unit_Cost']) * raw['Quantity']
        raw['ROI'] = (raw['Profit'] / (raw['Unit_Cost'] * raw['Quantity']).replace(0, 0.01)) * 100
        return raw
    except: return pd.DataFrame()

df = load_data()

# --- HEADER ---
c1, c2 = st.columns([0.7, 0.3])
with c1:
    st.title("📟 MASTER VAULT v7.9")
    st.caption("ULTRA-STABLE ENGINE // ELITE INTERFACE")
with c2:
    privacy = st.toggle("🔒 Privacy", value=False)
    if st.button("🔄 REFRESH"):
        st.cache_data.clear()
        st.rerun()

if not df.empty:
    def fmt(v): return "********" if privacy else f"${v:,.2f}"
    
    # Summary Metrics
    m1, m2, m3 = st.columns(3)
    active_df = df[df['Status'] != 'Sold']
    m1.metric("VAULT HOLDING", fmt((active_df['Unit_Cost'] * active_df['Quantity']).sum()))
    m2.metric("TOTAL PROFIT", fmt(df['Profit'].sum()), delta=None if privacy else f"{df['Profit'].sum():+.2f}")
    m3.metric("ROI", f"{df['ROI'].mean():+.1f}%")

    st.divider()

    t_port, t_mgmt, t_add = st.tabs(["🖼️ PORTFOLIO", "⚙️ CONTROL", "➕ ADD"])

    with t_port:
        f1, f2, f3 = st.columns([0.4, 0.3, 0.3])
        q = f1.text_input("🔍 Search", placeholder="Name...")
        s_filter = f2.selectbox("Status", ["All Assets", "Active", "Sold"])
        o_filter = f3.selectbox("Order", ["Newest", "Value (High)", "ROI (High)"])

        # STABLE FILTERING ENGINE
        view_df = df.copy()
        if q:
            view_df = view_df[view_df['Card_Name'].str.contains(q, case=False, na=False) | 
                             view_df['Set_Name'].str.contains(q, case=False, na=False)]
        
        if s_filter == "Active": view_df = view_df[view_df['Status'] != 'Sold']
        elif s_filter == "Sold": view_df = view_df[view_df['Status'] == 'Sold']

        if o_filter == "Value (High)": view_df = view_df.sort_values('Current_Val', ascending=False)
        elif o_filter == "ROI (High)": view_df = view_df.sort_values('ROI', ascending=False)
        else: view_df = view_df.sort_values('gsheet_row', ascending=False)

        # RENDER GRID (Bulletproof Method)
        grid = st.columns(2)
        items = view_df.to_dict('records') # แปลงเป็น List of Dict เพื่อเลี่ยงปัญหา Index ของ DataFrame
        
        for i, item in enumerate(items):
            with grid[i % 2]:
                is_sold = item['Status'] == 'Sold'
                p_clr = "#00ff88" if item['Profit'] >= 0 else "#ff4444"
                
                st.markdown(f'''
                    <div class="card-frame">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 12px;">
                            <span class="status-badge {"sold-badge" if is_sold else "active-badge"}">{"SOLD" if is_sold else "ACTIVE"}</span>
                            <span style="color:{p_clr}; font-weight:bold;">{item['ROI']:+.1f}%</span>
                        </div>
                        <div style="font-weight:700; font-size:15px; color:#ffffff; height:45px; overflow:hidden;">{item['Card_Name']}</div>
                ''', unsafe_allow_html=True)
                
                st.image(item['Image_URL'] if pd.notna(item['Image_URL']) else "https://via.placeholder.com/300/111/00f2ff?text=NO+IMAGE", use_container_width=True)
                
                st.markdown(f'''
                        <div style="margin-top:12px;">
                            <div style="color:{p_clr}; font-size:22px; font-weight:800;">{fmt(item['Current_Val'])}</div>
                            <div style="color:#888; font-size:11px; margin-top:4px;">{item['Grade_Score']} | P/L: {fmt(item['Profit'])}</div>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)

    with t_mgmt:
        target = st.selectbox("🎯 Select Card to Edit", df['Card_Name'].tolist())
        target_row = df[df['Card_Name'] == target].iloc[0]
        
        st.success(f"💎 Break-even Price: **{fmt(target_row['Unit_Cost'])}**")
        
        with st.form("edit_form_final"):
            e1, e2 = st.columns(2)
            with e1:
                u_mkt = st.number_input("Market ($)", value=float(target_row['Market_Price']))
                u_sel = st.number_input("Sell ($)", value=float(target_row['Sell_Price']))
                u_sta = st.selectbox("Status", ["Active", "Sold"], index=0 if target_row['Status'] != 'Sold' else 1)
            with e2:
                u_qty = st.number_input("Qty", value=int(target_row['Quantity']))
                u_grd = st.text_input("Grade", value=str(target_row['Grade_Score']))
                u_fee = st.number_input("Fee ($)", value=float(target_row['Grade_Fee']))
            
            u_img = st.file_uploader("Update Image", type=['jpg', 'png'])
            
            if st.form_submit_button("💾 SAVE CHANGES"):
                client = get_gspread_client()
                sh = client.open_by_url(SHEET_NAME_URL).sheet1
                r = int(target_row['gsheet_row'])
                sh.update_cell(r, 8, u_mkt); sh.update_cell(r, 11, u_sel); sh.update_cell(r, 12, u_sta)
                sh.update_cell(r, 5, u_qty); sh.update_cell(r, 9, u_grd); sh.update_cell(r, 7, u_fee)
                if u_img:
                    url = upload_to_imgbb(u_img)
                    if url: sh.update_cell(r, 10, url)
                st.cache_data.clear(); st.rerun()

    with t_add:
        with st.form("add_form_final", clear_on_submit=True):
            st.markdown("### ➕ Register Asset")
            a_name = st.text_input("Card Name")
            a_cat = st.selectbox("Type", ["One Piece", "Pokemon", "F1", "Others"])
            a_set = st.text_input("Set Name")
            a_buy = st.number_input("Buy ($)")
            a_fee = st.number_input("Fee ($)")
            a_mkt = st.number_input("Market ($)")
            a_qty = st.number_input("Qty", value=1)
            a_grd = st.text_input("Grade Score")
            a_id = st.text_input("Serial")
            a_file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])
            
            if st.form_submit_button("🚀 DEPLOY"):
                if a_name and a_file:
                    url = upload_to_imgbb(a_file)
                    if url:
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        sh.append_row([a_id, a_cat, a_name, a_set, int(a_qty), a_buy, a_fee, a_mkt, a_grd, url, 0, "Active"])
                        st.cache_data.clear(); st.rerun()
                else: st.warning("Name & Photo required")
else:
    st.info("No data available.")
