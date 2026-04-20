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
st.set_page_config(page_title="BOSS TANG | ASSET VAULT", layout="wide", page_icon="💰")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00f2ff; }
    .card-frame { border: 1px solid #1a1a1a; padding: 15px; border-radius: 10px; background: #0a0a0a; text-align: center; margin-bottom: 20px; position: relative; }
    .card-frame:hover { border-color: #00f2ff; box-shadow: 0 0 20px rgba(0, 242, 255, 0.2); }
    .status-active { color: #00ff88; font-size: 10px; font-weight: bold; border: 1px solid #00ff88; padding: 2px 5px; border-radius: 5px; }
    .status-sold { color: #ff4444; font-size: 10px; font-weight: bold; border: 1px solid #ff4444; padding: 2px 5px; border-radius: 5px; }
    label { color: #00f2ff !important; font-weight: bold; text-transform: uppercase; }
    [data-testid="stMetricValue"] { color: #00f2ff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER ---
c_h1, c_h2 = st.columns([0.7, 0.3])
with c_h1:
    st.title("📟 ULTRA-VAULT v7.1")
    st.caption("// MODULE: PORTFOLIO_MANAGEMENT // STATUS: ENHANCED")
with c_h2:
    privacy_mode = st.toggle("🔒 Privacy Mode", value=False)
    if st.button("🔄 Sync Neural Link"):
        st.cache_data.clear()
        st.rerun()

# --- 1. DATA LOADING & CLEANING ---
@st.cache_data(ttl=10)
def load_data():
    try:
        data = pd.read_csv(SHEET_URL)
        # ปรับความสะอาดข้อมูลตัวเลข (ลบ Comma และ Dollar Sign)
        numeric_cols = ['Quantity', 'Buy_Price', 'Grade_Fee', 'Market_Price', 'Sell_Price']
        for col in numeric_cols:
            if col in data.columns:
                data[col] = data[col].astype(str).str.replace(',', '').str.replace('$', '')
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        
        # ตั้งค่า Default Status หากไม่มีข้อมูล
        if 'Status' not in data.columns:
            data['Status'] = 'Active'
        return data
    except: return pd.DataFrame()

df = load_data()

if not df.empty:
    # --- Advanced Calculations ---
    df['Unit_Cost'] = df['Buy_Price'] + df['Grade_Fee']
    df['Total_Cost'] = df['Unit_Cost'] * df['Quantity']
    
    # กำไรที่ยังไม่ขาย (Unrealized) vs กำไรที่ขายแล้วจริง (Realized)
    df['Unrealized_PL'] = (df['Market_Price'] - df['Unit_Cost']) * df['Quantity']
    df['Realized_PL'] = (df['Sell_Price'] - df['Unit_Cost']) * df['Quantity']
    
    # แยกกลุ่มเพื่อแสดงผล
    active_assets = df[df['Status'] != 'Sold']
    sold_assets = df[df['Status'] == 'Sold']

    # --- Metrics Dashboard ---
    def f_v(v): return "********" if privacy_mode else f"${v:,.2f}"
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("VAULT VALUE", f_v(active_assets['Total_Cost'].sum()))
    m2.metric("HOLDING P/L", f_v(active_assets['Unrealized_PL'].sum()), 
              delta=f_v(active_assets['Unrealized_PL'].sum()) if not privacy_mode else None)
    m3.metric("REALIZED PROFIT", f_v(sold_assets['Realized_PL'].sum()))
    m4.metric("ASSET COUNT", f"{len(df)} PCS")

    st.divider()

    # --- 2. TABS ---
    t_gallery, t_manage, t_add = st.tabs(["🖼️ ARCHIVE", "⚙️ ASSET & SALES MANAGER", "➕ ADD NEW"])

    with t_gallery:
        view_filter = st.radio("VIEW MODE", ["ALL", "IN VAULT", "SOLD OUT"], horizontal=True)
        display_df = df
        if view_filter == "IN VAULT": display_df = active_assets
        elif view_filter == "SOLD OUT": display_df = sold_assets

        cols = st.columns(4)
        for idx, row in display_df.reset_index().iterrows():
            with cols[idx % 4]:
                is_sold = row['Status'] == 'Sold'
                # คำนวณ P/L ตามสถานะจริง
                current_pl = (row['Sell_Price'] if is_sold else row['Market_Price']) - row['Unit_Cost']
                color = "#00ff88" if current_pl >= 0 else "#ff4444"
                
                st.markdown('<div class="card-frame">', unsafe_allow_html=True)
                st.write(f"**{row['Card_Name']}**")
                
                # Image
                img = row.get('Image_URL', "")
                st.image(img if (pd.notna(img) and str(img).startswith('http')) else "https://via.placeholder.com/300", use_container_width=True)
                
                # Badges
                st.markdown(f'<span class="{"status-sold" if is_sold else "status-active"}">{"SOLD OUT" if is_sold else "IN VAULT"}</span>', unsafe_allow_html=True)
                st.caption(f"GRADE: {row['Grade_Score']} | QTY: {int(row['Quantity'])}")
                
                # Price Display
                label_p = "SOLD AT" if is_sold else "MARKET"
                price_p = row['Sell_Price'] if is_sold else row['Market_Price']
                
                # Fix Walrus Error by pre-defining pl_label
                pl_label = "PROFIT" if current_pl >= 0 else "LOSS"
                
                st.markdown(f"<div style='color:{color}; font-size:20px; font-weight:bold;'>{f_v(price_p)}</div>", unsafe_allow_html=True)
                st.markdown(f'<div style="color:{color}; font-size:11px; font-weight:bold;">{label_p} {pl_label}: {f_v(current_pl)}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    with t_manage:
        st.subheader("🛠️ UNIVERSAL EDITOR")
        target_card = st.selectbox("CHOOSE ASSET TO EDIT", df['Card_Name'].tolist())
        r_idx = df[df['Card_Name'] == target_card].index[0]
        
        with st.form("universal_manager"):
            e1, e2, e3 = st.columns(3)
            with e1:
                st.markdown("📦 **BASIC INFO**")
                m_price = st.number_input("MARKET PRICE ($)", value=float(df.at[r_idx, 'Market_Price']))
                m_qty = st.number_input("QUANTITY", value=int(df.at[r_idx, 'Quantity']))
                m_status = st.selectbox("ASSET STATUS", ["Active", "Sold"], index=0 if df.at[r_idx, 'Status'] != 'Sold' else 1)
            with e2:
                st.markdown("💎 **GRADING**")
                m_grade = st.text_input("GRADE SCORE", value=str(df.at[r_idx, 'Grade_Score']))
                m_fee = st.number_input("GRADE FEE ($)", value=float(df.at[r_idx, 'Grade_Fee']))
            with e3:
                st.markdown("💰 **SALE LOG**")
                m_sell = st.number_input("FINAL SELL PRICE ($)", value=float(df.at[r_idx, 'Sell_Price']))
                m_photo = st.file_uploader("REPLACE PHOTO", type=['jpg','png'])

            if st.form_submit_button("💾 UPDATE DATA ON CLOUD"):
                try:
                    with st.spinner("SYNCING WITH GOOGLE SHEETS..."):
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        g_row = r_idx + 2
                        
                        # คอลัมน์: 8:Market, 5:Qty, 12:Status, 9:Grade, 7:Fee, 11:Sell_Price
                        sh.update_cell(g_row, 8, m_price)
                        sh.update_cell(g_row, 5, m_qty)
                        sh.update_cell(g_row, 12, m_status)
                        sh.update_cell(g_row, 9, m_grade)
                        sh.update_cell(g_row, 7, m_fee)
                        sh.update_cell(g_row, 11, m_sell)
                        
                        if m_photo:
                            new_url = upload_to_imgbb(m_photo)
                            if new_url: sh.update_cell(g_row, 10, new_url)
                        
                        st.success(f"ASSET '{target_card}' HAS BEEN UPDATED.")
                        st.cache_data.clear()
                        st.rerun()
                except Exception as e: st.error(f"SYNC ERROR: {e}")

    with t_add:
        st.subheader("➕ ADD NEW ASSET")
        with st.form("new_asset", clear_on_submit=True):
            a1, a2, a3 = st.columns(3)
            with a1:
                n_cat = st.selectbox("CATEGORY", ["One Piece", "Pokemon", "F1", "Others"])
                n_name = st.text_input("CARD/ASSET NAME")
                n_id = st.text_input("SERIAL/ID")
            with a2:
                n_set = st.text_input("SET NAME")
                n_buy = st.number_input("BUY PRICE ($)", min_value=0.0)
                n_fee = st.number_input("EST. GRADE FEE ($)", min_value=0.0)
            with a3:
                n_score = st.text_input("GRADE (RAW/PSA/BGS)")
                n_market = st.number_input("INITIAL MARKET ($)", min_value=0.0)
                n_qty = st.number_input("QTY", min_value=1)
            
            n_file = st.file_uploader("ATTACH IMAGE", type=['jpg','png','jpeg'])
            if st.form_submit_button("🚀 RECORD NEW ASSET"):
                if n_file:
                    with st.spinner("UPLOADING PHOTO..."):
                        n_img = upload_to_imgbb(n_file)
                        if n_img:
                            client = get_gspread_client()
                            sh = client.open_by_url(SHEET_NAME_URL).sheet1
                            # ลำดับคอลัมน์: ID, Cat, Name, Set, Qty, Buy, Fee, Market, Grade, Image, Sell_Price, Status
                            sh.append_row([n_id, n_cat, n_name, n_set, int(n_qty), n_buy, n_fee, n_market, n_score, n_img, 0, "Active"])
                            st.success("ASSET RECORDED!")
                            st.cache_data.clear()
                            st.rerun()
                else: st.warning("PHOTO IS REQUIRED FOR VISUAL TRACKING.")
else:
    st.info("⚡ SYSTEM READY: PLEASE ADD YOUR FIRST ASSET.")
