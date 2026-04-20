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
st.set_page_config(page_title="PRO VAULT v13.5", layout="wide", page_icon="💎")

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

# --- DATA ENGINE (ULTRA-SAFE) ---
@st.cache_data(ttl=5)
def load_data():
    try:
        raw = pd.read_csv(SHEET_URL)
        # ล้างช่องว่างในชื่อ Column ทั้งหมด
        raw.columns = [str(c).strip() for c in raw.columns]
        
        # บังคับสร้าง Column ที่จำเป็น (ถ้าไม่มีใน Google Sheet จะไม่พัง แต่จะแสดงเป็นค่าว่าง)
        essential_cols = ['Card_Name', 'Status', 'Quantity', 'Buy_Price', 'Grade_Fee', 'Market_Price', 'Sell_Price', 'Image_URL', 'Grade_Score']
        for col in essential_cols:
            if col not in raw.columns:
                raw[col] = 0 if any(x in col for x in ['Price', 'Fee', 'Quantity']) else "N/A"

        # บันทึกตำแหน่งแถว
        raw['gsheet_row'] = raw.index + 2
        
        # ทำความสะอาดตัวเลข
        for col in ['Quantity', 'Buy_Price', 'Grade_Fee', 'Market_Price', 'Sell_Price']:
            raw[col] = pd.to_numeric(raw[col].astype(str).str.replace(r'[$, ]', '', regex=True), errors='coerce').fillna(0)
        
        # คำนวณกำไรและมูลค่า
        raw['Unit_Cost'] = raw['Buy_Price'] + raw['Grade_Fee']
        raw['Total_Cost'] = raw['Unit_Cost'] * raw['Quantity']
        # ถ้า Status เป็น Sold ให้ใช้ราคาขาย ถ้าไม่ให้ใช้ราคากลาง
        raw['Current_Val'] = raw.apply(lambda x: x['Sell_Price'] if str(x['Status']).strip().lower() == 'sold' else x['Market_Price'], axis=1)
        raw['Total_Value'] = raw['Current_Val'] * raw['Quantity']
        raw['Net_Profit'] = raw['Total_Value'] - raw['Total_Cost']
        raw['ROI_Pct'] = (raw['Net_Profit'] / raw['Total_Cost'].replace(0, 0.01)) * 100
        
        return raw
    except Exception as e:
        st.error(f"Waiting for valid data connection... ({e})")
        return pd.DataFrame()

df = load_data()

# --- APP UI ---
h_c1, h_c2 = st.columns([0.7, 0.3])
with h_c1:
    st.markdown("<h1 style='margin:0;'>PRO VAULT 13.5</h1>", unsafe_allow_html=True)
with h_c2:
    st.markdown('<div class="btn-sync">', unsafe_allow_html=True)
    if st.button("🔄 REFRESH"):
        st.cache_data.clear(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

if not df.empty:
    # คำนวณ Dashboard แบบ Safe
    total_val = df[df['Status'].astype(str).str.strip().lower() != 'sold']['Total_Value'].sum()
    total_profit = df['Net_Profit'].sum()
    
    m1, m2, m3 = st.columns(3)
    m1.metric("HOLDING VALUE", f"${total_val:,.2f}")
    m2.metric("NET P/L", f"${total_profit:,.2f}", delta=f"{total_profit:+.0f}")
    m3.metric("ROI (%)", f"{(total_profit / df['Total_Cost'].sum() * 100 if df['Total_Cost'].sum() > 0 else 0):+.1f}%")

    st.divider()

    # Search
    q = st.text_input("🔍 Search Asset", placeholder="Enter card name...")
    view_df = df.copy()
    if q:
        view_df = view_df[view_df['Card_Name'].astype(str).str.contains(q, case=False, na=False)]

    for idx, row in view_df.iterrows():
        p_color = "#3fb950" if row['Net_Profit'] >= 0 else "#f85149"
        
        with st.expander(f"{row['Card_Name']} ┃ ${row['Current_Val']:,.0f}"):
            lc, rc = st.columns([0.4, 0.6])
            with lc:
                st.image(row['Image_URL'] if pd.notna(row['Image_URL']) and str(row['Image_URL']).startswith('http') else "https://via.placeholder.com/300/161b22/30363d?text=NO+IMAGE", use_container_width=True)
            with rc:
                st.markdown(f'''
                    <p style="margin-bottom:2px; font-size:12px; color:#8b949e;">VALUATION</p>
                    <p style="font-size:20px; font-weight:800; margin-top:0;">${row['Current_Val']:,.2f} <span style="font-size:14px; color:{p_color};">({row['ROI_Pct']:+.1f}%)</span></p>
                    <p>Profit: <span style="color:{p_color}; font-weight:700;">${row['Net_Profit']:,.2f}</span></p>
                ''', unsafe_allow_html=True)
                
                with st.popover("⚙️ MANAGE"):
                    with st.form(f"form_{row['gsheet_row']}"):
                        u_mkt = st.number_input("Market Price", value=float(row['Market_Price']))
                        u_sta = st.selectbox("Status", ["Active", "Sold"], index=0 if str(row['Status']).lower() != 'sold' else 1)
                        u_sel = st.number_input("Sold Price", value=float(row['Sell_Price']))
                        u_qty = st.number_input("Quantity", value=int(row['Quantity']))
                        u_fee = st.number_input("Grade Fee", value=float(row['Grade_Fee']))
                        u_grd = st.text_input("Grade", value=str(row['Grade_Score']))
                        
                        if st.form_submit_button("SAVE"):
                            client = get_gspread_client()
                            sh = client.open_by_url(SHEET_NAME_URL).sheet1
                            r = int(row['gsheet_row'])
                            # อัปเดตข้อมูลกลับไปยัง Google Sheet
                            sh.update_cell(r, 8, u_mkt); sh.update_cell(r, 11, u_sel); sh.update_cell(r, 12, u_sta)
                            sh.update_cell(r, 5, u_qty); sh.update_cell(r, 9, u_grd); sh.update_cell(r, 7, u_fee)
                            st.cache_data.clear(); st.rerun()
                    
                    st.divider()
                    conf = st.checkbox("Delete this row?", key=f"c_{row['gsheet_row']}")
                    st.markdown('<div class="btn-delete">', unsafe_allow_html=True)
                    if st.button("CONFIRM DELETE", key=f"b_{row['gsheet_row']}", disabled=not conf):
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        r = int(row['gsheet_row'])
                        if r > 1:
                            sh.delete_rows(r)
                            st.cache_data.clear(); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # ADD NEW
    st.divider()
    with st.expander("➕ ADD NEW ASSET"):
        with st.form("add_new"):
            a_name = st.text_input("Name")
            a_buy = st.number_input("Buy ($)")
            a_mkt = st.number_input("Market ($)")
            a_qty = st.number_input("Qty", value=1)
            a_file = st.file_uploader("Photo", type=['jpg', 'png', 'jpeg'])
            if st.form_submit_button("DEPLOY"):
                if a_name and a_file:
                    url = upload_to_imgbb(a_file)
                    if url:
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        sh.append_row(["N/A", "Card", a_name, "N/A", int(a_qty), a_buy, 0, a_mkt, "N/A", url, 0, "Active"])
                        st.cache_data.clear(); st.rerun()
else:
    st.info("Searching for your data... Please ensure your Google Sheet has at least one row of data.")
