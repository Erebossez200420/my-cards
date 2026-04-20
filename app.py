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

# --- UI SETTINGS (PRO MODE) ---
st.set_page_config(page_title="PRO VAULT | BOSS TANG", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #050505; color: #00f2ff; }
    .card-frame { 
        border: 1px solid #1a1a1a; padding: 12px; border-radius: 15px; 
        background: #0a0a0a; text-align: center; margin-bottom: 15px; 
    }
    .roi-badge { font-size: 12px; font-weight: bold; border-radius: 5px; padding: 2px 6px; }
    .stButton button { border-radius: 20px; background-color: #00f2ff11; border: 1px solid #00f2ff; color: #00f2ff; width: 100%; }
    [data-testid="stMetricValue"] { color: #00f2ff !important; font-family: monospace; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
c_h1, c_h2 = st.columns([0.7, 0.3])
with c_h1:
    st.title("📈 PRO-VAULT v7.3")
    st.caption("ANALYTICS & ASSET TRACKING // STATUS: ACTIVE")
with c_h2:
    privacy_mode = st.toggle("🔒 Privacy", value=False)
    if st.button("🔄 Sync"):
        st.cache_data.clear()
        st.rerun()

# --- 1. DATA LOADING ---
@st.cache_data(ttl=10)
def load_data():
    try:
        data = pd.read_csv(SHEET_URL)
        num_cols = ['Quantity', 'Buy_Price', 'Grade_Fee', 'Market_Price', 'Sell_Price']
        for col in num_cols:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col].astype(str).str.replace(',', '').str.replace('$', ''), errors='coerce').fillna(0)
        return data
    except: return pd.DataFrame()

df = load_data()

if not df.empty:
    # --- Advanced Analytics ---
    df['Unit_Cost'] = df['Buy_Price'] + df['Grade_Fee']
    df['Current_Value'] = df.apply(lambda x: x['Sell_Price'] if x['Status'] == 'Sold' else x['Market_Price'], axis=1)
    df['Net_Profit'] = (df['Current_Value'] - df['Unit_Cost']) * df['Quantity']
    df['ROI'] = (df['Net_Profit'] / (df['Unit_Cost'] * df['Quantity'].replace(0, 1))) * 100

    # Summary Metrics
    def f_v(v): return "********" if privacy_mode else f"${v:,.2f}"
    
    m1, m2, m3, m4 = st.columns(4)
    active_df = df[df['Status'] != 'Sold']
    sold_df = df[df['Status'] == 'Sold']
    
    m1.metric("VAULT VALUE", f_v(active_df['Unit_Cost'].sum() * active_df['Quantity'].sum()))
    m2.metric("HOLDING P/L", f_v(active_df['Net_Profit'].sum()), delta=f"{active_df['Net_Profit'].sum():,.2f}")
    m3.metric("REALIZED PROFIT", f_v(sold_df['Net_Profit'].sum()))
    total_roi = (df['Net_Profit'].sum() / (df['Unit_Cost'] * df['Quantity']).sum()) * 100
    m4.metric("TOTAL ROI", f"{total_roi:.1f}%")

    st.divider()

    # --- 2. TABS ---
    t_archive, t_edit, t_add = st.tabs(["🖼️ PORTFOLIO", "⚙️ MANAGEMENT", "➕ NEW ASSET"])

    with t_archive:
        # --- Search & Sort Controls ---
        c1, c2, c3 = st.columns([0.4, 0.3, 0.3])
        search_q = c1.text_input("🔍 Search Name/Set...", placeholder="Kimi, OP-05, etc.")
        sort_by = c2.selectbox("Sort By", ["Newest", "Price (High-Low)", "ROI (High-Low)"])
        view_f = c3.selectbox("Status", ["All Assets", "In Vault", "Sold"])

        # Filtering Logic
        display_df = df.copy()
        if search_q:
            display_df = display_df[display_df['Card_Name'].str.contains(search_q, case=False) | display_df['Set_Name'].str.contains(search_q, case=False)]
        if view_f == "In Vault": display_df = display_df[display_df['Status'] != 'Sold']
        elif view_f == "Sold": display_df = display_df[display_df['Status'] == 'Sold']
        
        # Sorting Logic
        if sort_by == "Price (High-Low)": display_df = display_df.sort_values('Current_Value', ascending=False)
        elif sort_by == "ROI (High-Low)": display_df = display_df.sort_values('ROI', ascending=False)
        else: display_df = display_df.iloc[::-1] # Newest First

        # Gallery
        cols = st.columns(2)
        for idx, row in display_df.reset_index().iterrows():
            with cols[idx % 2]:
                is_sold = row['Status'] == 'Sold'
                roi_color = "#00ff88" if row['ROI'] >= 0 else "#ff4444"
                
                st.markdown('<div class="card-frame">', unsafe_allow_html=True)
                st.write(f"**{row['Card_Name']}**")
                
                img = row.get('Image_URL', "")
                st.image(img if (pd.notna(img) and str(img).startswith('http')) else "https://via.placeholder.com/300/111/00f2ff?text=NO+IMAGE", use_container_width=True)
                
                # Tags & ROI
                st.markdown(f'<span style="color:{roi_color}; border: 1px solid {roi_color};" class="roi-badge">{row["ROI"]:+.1f}%</span>', unsafe_allow_html=True)
                st.caption(f"{row['Grade_Score']} | QTY: {int(row['Quantity'])}")
                
                price_val = row['Sell_Price'] if is_sold else row['Market_Price']
                st.markdown(f"<div style='color:{roi_color}; font-size:18px; font-weight:bold;'>{f_v(price_val)}</div>", unsafe_allow_html=True)
                st.markdown(f'<div style="color:#666; font-size:10px;">{"SOLD" if is_sold else "MARKET PRICE"}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    with t_edit:
        # Management tab (Same as v7.2 with Break-even tip)
        target = st.selectbox("Select Asset to Update", df['Card_Name'].tolist())
        idx_r = df[df['Card_Name'] == target].index[0]
        
        # Break-even calculation
        be_price = df.at[idx_r, 'Unit_Cost']
        st.info(f"💡 Break-even Price: **${be_price:,.2f}** (Sell above this to make profit)")
        
        with st.form("edit_pro"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                m_mkt = st.number_input("Market Price ($)", value=float(df.at[idx_r, 'Market_Price']))
                m_sel = st.number_input("Sell Price ($)", value=float(df.at[idx_r, 'Sell_Price']))
                m_sta = st.selectbox("Status", ["Active", "Sold"], index=0 if df.at[idx_r, 'Status'] != 'Sold' else 1)
            with col_e2:
                m_qty = st.number_input("Qty", value=int(df.at[idx_r, 'Quantity']))
                m_grd = st.text_input("Grade", value=str(df.at[idx_r, 'Grade_Score']))
                m_fee = st.number_input("Grade Fee ($)", value=float(df.at[idx_r, 'Grade_Fee']))
            
            m_pic = st.file_uploader("Update Image", type=['jpg','png'])
            if st.form_submit_button("Update Asset"):
                client = get_gspread_client()
                sh = client.open_by_url(SHEET_NAME_URL).sheet1
                r = idx_r + 2
                sh.update_cell(r, 8, m_mkt); sh.update_cell(r, 11, m_sel); sh.update_cell(r, 12, m_sta)
                sh.update_cell(r, 5, m_qty); sh.update_cell(r, 9, m_grd); sh.update_cell(r, 7, m_fee)
                if m_pic:
                    url = upload_to_imgbb(m_pic)
                    if url: sh.update_cell(r, 10, url)
                st.cache_data.clear(); st.rerun()

    with t_add:
        # (Add New form remains same as v7.2)
        with st.form("add_pro"):
            st.write("### ➕ Record New Investment")
            an_name = st.text_input("Asset Name")
            an_buy = st.number_input("Buy Price ($)")
            an_fee = st.number_input("Grade Fee ($)")
            an_file = st.file_uploader("Photo", type=['jpg','png','jpeg'])
            if st.form_submit_button("Save Asset"):
                if an_file and an_name:
                    url = upload_to_imgbb(an_file)
                    if url:
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        sh.append_row(["", "Misc", an_name, "", 1, an_buy, an_fee, an_buy, "RAW", url, 0, "Active"])
                        st.cache_data.clear(); st.rerun()
else:
    st.info("System Ready.")
