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

# --- UI DESIGN SYSTEM ---
st.set_page_config(page_title="VAULT PRO v13.4", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #0d1117; font-family: 'Inter', sans-serif; color: #ffffff; }
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: #161b22 !important; color: #ffffff !important; border: 1px solid #30363d !important; border-radius: 10px !important;
    }
    [data-testid="stMetric"] { background: #161b22; border: 1px solid #30363d; border-radius: 16px; padding: 20px; }
    .st-expander { background-color: #0d1117 !important; border: 1px solid #30363d !important; border-radius: 12px !important; }
    .stButton button { border-radius: 10px !important; font-weight: 700 !important; height: 3.5rem; width: 100%; border: none !important; }
    .btn-sync button { background: #238636 !important; color: white !important; }
    .btn-update button { background: #1f6feb !important; color: white !important; }
    .btn-delete button { background: #da3633 !important; color: white !important; }
    .p-bar-bg { background: #30363d; height: 10px; border-radius: 5px; width: 100%; margin: 12px 0; }
    .p-bar-fill { height: 100%; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA ENGINE (BULLETPROOF MODE) ---
@st.cache_data(ttl=5)
def load_data():
    try:
        raw = pd.read_csv(SHEET_URL)
        # 1. ล้างชื่อ Column ให้สะอาดที่สุด (ลบอักขระพิเศษ)
        raw.columns = [str(c).strip().replace('\ufeff', '') for c in raw.columns]

        # 2. ฟังก์ชันดึงข้อมูลแบบ "ไม่มีวันพัง"
        def get_safe_col(df_in, target_name, default=""):
            # ค้นหาชื่อ Column ที่ใกล้เคียงที่สุด (Case-insensitive)
            for c in df_in.columns:
                if c.lower() == target_name.lower():
                    return df_in[c]
            return pd.Series([default] * len(df_in))

        # 3. สร้าง DataFrame ใหม่ด้วยโครงสร้างที่แน่นอน
        clean_df = pd.DataFrame()
        clean_df['gsheet_row'] = raw.index + 2
        clean_df['Card_Name'] = get_safe_col(raw, 'Card_Name', "Unknown Asset")
        clean_df['Status'] = get_safe_col(raw, 'Status', "Active")
        clean_df['Quantity'] = get_safe_col(raw, 'Quantity', 0)
        clean_df['Buy_Price'] = get_safe_col(raw, 'Buy_Price', 0)
        clean_df['Grade_Fee'] = get_safe_col(raw, 'Grade_Fee', 0)
        clean_df['Market_Price'] = get_safe_col(raw, 'Market_Price', 0)
        clean_df['Sell_Price'] = get_safe_col(raw, 'Sell_Price', 0)
        clean_df['Image_URL'] = get_safe_col(raw, 'Image_URL', "")
        clean_df['Grade_Score'] = get_safe_col(raw, 'Grade_Score', "N/A")

        # 4. Clean numeric data
        for col in ['Quantity', 'Buy_Price', 'Grade_Fee', 'Market_Price', 'Sell_Price']:
            clean_df[col] = (clean_df[col].astype(str)
                            .str.replace(r'[$, ]', '', regex=True)
                            .replace('', '0'))
            clean_df[col] = pd.to_numeric(clean_df[col], errors='coerce').fillna(0)
        
        # 5. Business Logic
        clean_df['Unit_Cost'] = clean_df['Buy_Price'] + clean_df['Grade_Fee']
        clean_df['Total_Cost'] = clean_df['Unit_Cost'] * clean_df['Quantity']
        clean_df['Current_Val'] = clean_df.apply(lambda x: x['Sell_Price'] if str(x['Status']).strip().lower() == 'sold' else x['Market_Price'], axis=1)
        clean_df['Total_Value'] = clean_df['Current_Val'] * clean_df['Quantity']
        clean_df['Net_Profit'] = clean_df['Total_Value'] - clean_df['Total_Cost']
        clean_df['ROI_Pct'] = (clean_df['Net_Profit'] / clean_df['Total_Cost'].replace(0, 0.01)) * 100
        
        return clean_df
    except Exception as e:
        st.error(f"Data Sync Failed: {e}")
        return pd.DataFrame()

df = load_data()

# --- APP UI ---
h_col1, h_col2 = st.columns([0.7, 0.3])
with h_col1:
    st.markdown("<h1 style='margin:0;'>PRO VAULT 13.4</h1>", unsafe_allow_html=True)
with h_col2:
    st.markdown('<div class="btn-sync">', unsafe_allow_html=True)
    if st.button("🔄 REFRESH"):
        st.cache_data.clear(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

if not df.empty:
    # 100% Safe Column Access
    status_list = df['Status'].astype(str).str.strip().lower()
    active_mask = status_list != 'sold'
    
    # Dashboard
    m1, m2, m3 = st.columns(3)
    m1.metric("HOLDING VALUE", f"${df[active_mask]['Total_Value'].sum():,.2f}")
    m2.metric("NET P/L", f"${df['Net_Profit'].sum():,.2f}", delta=f"{df['Net_Profit'].sum():+.0f}")
    m3.metric("ROI (%)", f"{(df['Net_Profit'].sum() / df['Total_Cost'].sum() * 100 if df['Total_Cost'].sum() > 0 else 0):+.1f}%")

    st.divider()

    # Filters
    f1, f2 = st.columns([0.6, 0.4])
    q = f1.text_input("🔍 Search", placeholder="Find by name...")
    sort_by = f2.selectbox("Sort", ["Latest", "Highest Profit", "Best ROI %"])

    view_df = df.copy()
    if q: view_df = view_df[view_df['Card_Name'].astype(str).str.contains(q, case=False, na=False)]
    if sort_by == "Highest Profit": view_df = view_df.sort_values('Net_Profit', ascending=False)
    elif sort_by == "Best ROI %": view_df = view_df.sort_values('ROI_Pct', ascending=False)
    else: view_df = view_df.sort_index(ascending=False)

    for idx, row in view_df.iterrows():
        p_color = "#3fb950" if row['Net_Profit'] >= 0 else "#f85149"
        
        with st.expander(f"{row['Card_Name']} ┃ ${row['Current_Val']:,.0f}", expanded=False):
            lc, rc = st.columns([0.4, 0.6])
            with lc:
                st.image(row['Image_URL'] if pd.notna(row['Image_URL']) and str(row['Image_URL']).startswith('http') else "https://via.placeholder.com/300/161b22/30363d?text=NO+IMAGE", use_container_width=True)
            with rc:
                # Progress Bar
                safe_c = max(row['Unit_Cost'], 0.01)
                meter = min(max((row['Current_Val'] / safe_c) * 50, 5), 100)
                st.markdown(f'''
                    <div style="font-size:12px; color:#8b949e; margin-bottom:5px;">VALUATION</div>
                    <div class="p-bar-bg"><div class="p-bar-fill" style="width:{meter}%; background:{p_color}; shadow: 0 0 10px {p_color}44;"></div></div>
                    <p>Price: <b>${row['Current_Val']:,.2f}</b> | P/L: <span style="color:{p_color}; font-weight:800;">${row['Net_Profit']:,.2f}</span></p>
                ''', unsafe_allow_html=True)
                
                with st.popover("⚙️ ACTIONS"):
                    with st.form(f"form_{row['gsheet_row']}"):
                        u_mkt = st.number_input("Market Price", value=float(row['Market_Price']))
                        u_sel = st.number_input("Sold Price", value=float(row['Sell_Price']))
                        u_sta = st.selectbox("Status", ["Active", "Sold"], index=0 if str(row['Status']).lower() != 'sold' else 1)
                        u_qty = st.number_input("Quantity", value=int(row['Quantity']))
                        u_fee = st.number_input("Grade Fee", value=float(row['Grade_Fee']))
                        u_grd = st.text_input("Grade", value=str(row['Grade_Score']))
                        u_img = st.file_uploader("New Photo", type=['jpg', 'png'])
                        
                        st.markdown('<div class="btn-update">', unsafe_allow_html=True)
                        if st.form_submit_button("SAVE"):
                            client = get_gspread_client()
                            sh = client.open_by_url(SHEET_NAME_URL).sheet1
                            r = int(row['gsheet_row'])
                            sh.update_cell(r, 8, u_mkt); sh.update_cell(r, 11, u_sel); sh.update_cell(r, 12, u_sta)
                            sh.update_cell(r, 5, u_qty); sh.update_cell(r, 9, u_grd); sh.update_cell(r, 7, u_fee)
                            if u_img:
                                url = upload_to_imgbb(u_img)
                                if url: sh.update_cell(r, 10, url)
                            st.cache_data.clear(); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.divider()
                    conf = st.checkbox("Delete Asset?", key=f"c_{row['gsheet_row']}")
                    st.markdown('<div class="btn-delete">', unsafe_allow_html=True)
                    if st.button("DELETE", key=f"b_{row['gsheet_row']}", disabled=not conf):
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        r = int(row['gsheet_row'])
                        if r > 1:
                            sh.delete_rows(r)
                            st.cache_data.clear(); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # ADD NEW
    st.divider()
    with st.expander("➕ REGISTER NEW ASSET"):
        with st.form("add_v13_4", clear_on_submit=True):
            a_name = st.text_input("Name")
            a_set = st.text_input("Set")
            a_buy = st.number_input("Buy ($)")
            a_mkt = st.number_input("Market ($)")
            a_qty = st.number_input("Qty", value=1)
            a_fee = st.number_input("Fee ($)")
            a_grd = st.text_input("Grade")
            a_id = st.text_input("Serial ID")
            a_file = st.file_uploader("Photo", type=['jpg', 'png', 'jpeg'])
            if st.form_submit_button("DEPLOY TO VAULT"):
                if a_name and a_file:
                    url = upload_to_imgbb(a_file)
                    if url:
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        sh.append_row([a_id, "Card", a_name, a_set, int(a_qty), a_buy, a_fee, a_mkt, a_grd, url, 0, "Active"])
                        st.cache_data.clear(); st.rerun()
else:
    st.info("Awaiting data sync...")
