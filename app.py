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

# --- UI SETTINGS ---
st.set_page_config(page_title="PRO VAULT | BOSS TANG", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #050505; color: #00f2ff; }
    .card-frame { 
        border: 1px solid #1a1a1a; padding: 12px; border-radius: 15px; 
        background: #0a0a0a; text-align: center; margin-bottom: 15px; 
    }
    .status-badge { font-size: 10px; font-weight: bold; padding: 2px 8px; border-radius: 10px; text-transform: uppercase; }
    .active-badge { border: 1px solid #00ff88; color: #00ff88; }
    .sold-badge { border: 1px solid #ff4444; color: #ff4444; }
    .stButton button { border-radius: 20px; background-color: #00f2ff11; border: 1px solid #00f2ff; color: #00f2ff; width: 100%; }
    [data-testid="stMetricValue"] { color: #00f2ff !important; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

# --- 1. DATA LOADING ---
@st.cache_data(ttl=5)
def load_data():
    try:
        raw_df = pd.read_csv(SHEET_URL)
        for col in ['Quantity', 'Buy_Price', 'Grade_Fee', 'Market_Price', 'Sell_Price']:
            if col in raw_df.columns:
                raw_df[col] = pd.to_numeric(raw_df[col].astype(str).str.replace(',', '').str.replace('$', ''), errors='coerce').fillna(0)
        
        raw_df['Unit_Cost'] = raw_df['Buy_Price'] + raw_df['Grade_Fee']
        raw_df['Current_Value'] = raw_df.apply(lambda x: x['Sell_Price'] if x['Status'] == 'Sold' else x['Market_Price'], axis=1)
        raw_df['Total_Profit'] = (raw_df['Current_Value'] - raw_df['Unit_Cost']) * raw_df['Quantity']
        
        cost_for_roi = (raw_df['Unit_Cost'] * raw_df['Quantity']).replace(0, 0.01)
        raw_df['ROI'] = (raw_df['Total_Profit'] / cost_for_roi) * 100
        return raw_df
    except: return pd.DataFrame()

df = load_data()

# --- HEADER ---
c_h1, c_h2 = st.columns([0.7, 0.3])
with c_h1:
    st.title("📈 PRO-VAULT 7.6")
    st.caption("STABLE VERSION // BUG FIXED")
with c_h2:
    privacy_mode = st.toggle("🔒 Privacy", value=False)
    if st.button("🔄 REFRESH"):
        st.cache_data.clear()
        st.rerun()

if not df.empty:
    def f_v(v): return "********" if privacy_mode else f"${v:,.2f}"
    
    # Global Metrics
    m1, m2, m3 = st.columns(3)
    active_mask = df['Status'] != 'Sold'
    m1.metric("VAULT HOLDINGS", f_v((df[active_mask]['Unit_Cost'] * df[active_mask]['Quantity']).sum()))
    m2.metric("TOTAL P/L", f_v(df['Total_Profit'].sum()))
    m3.metric("WIN RATE", f"{(len(df[df['Total_Profit'] > 0]) / len(df) * 100):.1f}%")

    st.divider()

    t_view, t_edit, t_add = st.tabs(["🖼️ ARCHIVE", "⚙️ MGMT", "➕ NEW"])

    with t_view:
        f1, f2, f3 = st.columns([0.4, 0.3, 0.3])
        search = f1.text_input("🔍 Search", placeholder="Name, Set...")
        status_f = f2.selectbox("Status", ["All", "Active", "Sold"])
        sort_f = f3.selectbox("Sort", ["Newest", "Price (High)", "ROI (High)"])

        # --- RE-FIXED FILTERING LOGIC ---
        view_df = df.copy()
        
        if search:
            view_df = view_df[view_df['Card_Name'].str.contains(search, case=False, na=False) | 
                             view_df['Set_Name'].str.contains(search, case=False, na=False)]
        
        if status_f == "Active": view_df = view_df[view_df['Status'] != 'Sold']
        elif status_f == "Sold": view_df = view_df[view_df['Status'] == 'Sold']

        if sort_f == "Price (High)": view_df = view_df.sort_values('Current_Value', ascending=False)
        elif sort_f == "ROI (High)": view_df = view_df.sort_values('ROI', ascending=False)
        else: view_df = view_df.sort_index(ascending=False) # สั่งจัดเรียงจาก Index โดยตรง

        # Render Grid
        grid_cols = st.columns(2)
        # ใช้ reset_index เพื่อให้การนับลำดับใน UI ไม่รวน แต่ยังเก็บ index เดิมไว้ใน 'index' column
        for i, (orig_idx, row) in enumerate(view_df.iterrows()):
            with grid_cols[i % 2]:
                is_sold = row['Status'] == 'Sold'
                profit_color = "#00ff88" if row['Total_Profit'] >= 0 else "#ff4444"
                
                st.markdown(f'''
                    <div class="card-frame">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
                            <span class="status-badge {"sold-badge" if is_sold else "active-badge"}">{"SOLD" if is_sold else "ACTIVE"}</span>
                            <span style="color:{profit_color}; font-weight:bold; font-size:12px;">{row['ROI']:+.1f}%</span>
                        </div>
                        <div style="font-weight:bold; margin-bottom:10px;">{row['Card_Name']}</div>
                    </div>
                ''', unsafe_allow_html=True)
                
                img_url = row.get('Image_URL', "")
                st.image(img_url if (pd.notna(img_url) and str(img_url).startswith('http')) else "https://via.placeholder.com/300/111/00f2ff?text=NO+IMAGE", use_container_width=True)
                
                st.markdown(f"""
                    <div style="text-align:center;">
                        <div style="color:{profit_color}; font-size:20px; font-weight:bold;">{f_v(row['Current_Value'])}</div>
                        <div style="color:#666; font-size:10px;">P/L: {f_v(row['Total_Profit'])} | {row['Grade_Score']}</div>
                    </div>
                """, unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    with t_edit:
        st.subheader("🛠️ ASSET MANAGER")
        target = st.selectbox("Select Card", df['Card_Name'].tolist())
        real_idx = df[df['Card_Name'] == target].index[0]
        
        st.info(f"💡 **Break-even:** {f_v(df.at[real_idx, 'Unit_Cost'])}")
        
        with st.form("edit_form_v76"):
            e1, e2 = st.columns(2)
            with e1:
                u_mkt = st.number_input("Market Price ($)", value=float(df.at[real_idx, 'Market_Price']))
                u_sel = st.number_input("Sell Price ($)", value=float(df.at[real_idx, 'Sell_Price']))
                u_status = st.selectbox("Status", ["Active", "Sold"], index=0 if df.at[real_idx, 'Status'] != 'Sold' else 1)
            with e2:
                u_qty = st.number_input("Qty", value=int(df.at[real_idx, 'Quantity']))
                u_grade = st.text_input("Grade", value=str(df.at[real_idx, 'Grade_Score']))
                u_fee = st.number_input("Fee ($)", value=float(df.at[real_idx, 'Grade_Fee']))
            
            u_img = st.file_uploader("Update Photo", type=['jpg', 'png'])
            
            if st.form_submit_button("💾 SYNC TO CLOUD"):
                client = get_gspread_client()
                sh = client.open_by_url(SHEET_NAME_URL).sheet1
                r = int(real_idx) + 2
                sh.update_cell(r, 8, u_mkt); sh.update_cell(r, 11, u_sel); sh.update_cell(r, 12, u_status)
                sh.update_cell(r, 5, u_qty); sh.update_cell(r, 9, u_grade); sh.update_cell(r, 7, u_fee)
                if u_img:
                    url = upload_to_imgbb(u_img)
                    if url: sh.update_cell(r, 10, url)
                st.cache_data.clear(); st.rerun()

    with t_add:
        st.subheader("➕ ADD ASSET")
        with st.form("add_form_v76", clear_on_submit=True):
            a_name = st.text_input("Name")
            a_cat = st.selectbox("Type", ["One Piece", "Pokemon", "F1", "Others"])
            a_set = st.text_input("Set")
            a_buy = st.number_input("Buy ($)")
            a_fee = st.number_input("Fee ($)")
            a_mkt = st.number_input("Market ($)")
            a_qty = st.number_input("Qty", value=1)
            a_grd = st.text_input("Grade")
            a_id = st.text_input("Serial")
            a_file = st.file_uploader("Photo", type=['jpg', 'png', 'jpeg'])
            
            if st.form_submit_button("🚀 RECORD"):
                if a_name and a_file:
                    url = upload_to_imgbb(a_file)
                    if url:
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        sh.append_row([a_id, a_cat, a_name, a_set, int(a_qty), a_buy, a_fee, a_mkt, a_grd, url, 0, "Active"])
                        st.cache_data.clear(); st.rerun()
                else: st.warning("Name and Photo required")
