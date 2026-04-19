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

# --- CORE FUNCTIONS ---
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
st.set_page_config(page_title="BOSS TANG | ULTIMATE VAULT", layout="wide", page_icon="📟")

st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00f2ff; }
    .card-frame { border: 1px solid #1a1a1a; padding: 15px; border-radius: 10px; background: #0a0a0a; text-align: center; margin-bottom: 20px; }
    .card-frame:hover { border-color: #00f2ff; box-shadow: 0 0 15px rgba(0, 242, 255, 0.2); }
    label { color: #00f2ff !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER & CONTROLS ---
col_h1, col_h2 = st.columns([0.7, 0.3])
with col_h1:
    st.title("📟 ULTRA-VAULT v5.0")
with col_h2:
    privacy_mode = st.toggle("🔒 Privacy Mode", value=False)
    if st.button("🔄 Force Reload (Sync Sheet)"):
        st.cache_data.clear()
        st.rerun()

# --- 1. DATA LOADING & CLEANING ---
@st.cache_data(ttl=10)
def load_data():
    try:
        data = pd.read_csv(SHEET_URL)
        # บังคับให้เป็นตัวเลข ป้องกันคำนวณพลาด
        numeric_cols = ['Quantity', 'Buy_Price', 'Grade_Fee', 'Market_Price']
        for col in numeric_cols:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        return data
    except: return pd.DataFrame()

df = load_data()

if not df.empty:
    # Calculations
    df['Unit_Cost'] = df['Buy_Price'] + df.get('Grade_Fee', 0)
    df['Total_Cost'] = df['Unit_Cost'] * df['Quantity']
    df['Total_Market_Value'] = df['Market_Price'] * df['Quantity']
    df['Profit_Loss'] = df['Total_Market_Value'] - df['Total_Cost']

    # Dashboard
    def f_v(v): return "********" if privacy_mode else f"${v:,.2f}"
    m1, m2, m3 = st.columns(3)
    m1.metric("TOTAL CAPITAL", f_v(df['Total_Cost'].sum()))
    m2.metric("VAULT VALUE", f_v(df['Total_Market_Value'].sum()))
    m3.metric("NET PROFIT", f_v(df['Profit_Loss'].sum()))

    st.divider()

    # --- 2. INPUT & EDIT SYSTEM ---
    tab_gallery, tab_edit, tab_add = st.tabs(["🖼️ ARCHIVE", "⚙️ EDIT ASSETS", "➕ ADD NEW"])

    with tab_gallery:
        cols = st.columns(4)
        for idx, row in df.iterrows():
            with cols[idx % 4]:
                pl = row['Market_Price'] - row['Unit_Cost']
                color = "#00ff88" if pl >= 0 else "#ff4444"
                st.markdown(f'<div class="card-frame">', unsafe_allow_html=True)
                st.write(f"**{row['Card_Name']}**")
                
                img = row.get('Image_URL', "")
                if pd.notna(img) and isinstance(img, str) and img.startswith('http'):
                    st.image(img, use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/200", use_container_width=True)
                
                price_txt = "********" if privacy_mode else f"${row['Market_Price']:,.2f}"
                st.markdown(f"<div style='color:{color}; font-size:20px; font-weight:bold;'>{price_txt}</div>", unsafe_allow_html=True)
                st.markdown(f'<div style="color:{color}; font-size:10px;">{"▲ PROFIT" if pl >= 0 else "▼ LOSS"}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    with tab_edit:
        st.subheader("🛠️ QUICK MARKET PRICE UPDATE")
        # เลือกการ์ดที่จะแก้
        card_to_edit = st.selectbox("SELECT CARD TO UPDATE", df['Card_Name'].tolist())
        row_idx = df[df['Card_Name'] == card_to_edit].index[0]
        
        with st.form("edit_form"):
            col_e1, col_e2 = st.columns(2)
            with col_e1:
                new_market = st.number_input("UPDATE MARKET PRICE ($)", value=float(df.at[row_idx, 'Market_Price']))
            with col_e2:
                new_qty = st.number_input("UPDATE QUANTITY", value=int(df.at[row_idx, 'Quantity']), step=1)
            
            if st.form_submit_button("SAVE CHANGES"):
                try:
                    client = get_gspread_client()
                    sh = client.open_by_url(SHEET_NAME_URL).sheet1
                    # Google Sheet row = index + 2 (Header is 1)
                    sh.update_cell(row_idx + 2, 8, new_market) # Column 8 = Market_Price
                    sh.update_cell(row_idx + 2, 5, new_qty)    # Column 5 = Quantity
                    st.success(f"UPDATED: {card_to_edit}")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e: st.error(f"SYNC ERROR: {e}")

    with tab_add:
        with st.form("new_entry", clear_on_submit=True):
            a1, a2, a3 = st.columns(3)
            with a1:
                cat = st.selectbox("TYPE", ["One Piece", "Pokemon", "F1", "Others"])
                name = st.text_input("NAME")
                c_id = st.text_input("ID")
            with a2:
                c_set = st.text_input("SET")
                buy = st.number_input("COST ($)", min_value=0.0)
                fee = st.number_input("FEE ($)", min_value=0.0)
            with a3:
                score = st.text_input("GRADE")
                market_in = st.number_input("INITIAL MARKET ($)", min_value=0.0)
                qty_in = st.number_input("QTY", min_value=1, step=1)
            
            up_file = st.file_uploader("📸 PHOTO", type=['jpg','png','jpeg'])
            if st.form_submit_button("ADD TO VAULT"):
                if up_file:
                    new_img = upload_to_imgbb(up_file)
                    if new_img:
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        sh.append_row([c_id, cat, name, c_set, int(qty_in), buy, fee, market_in, score, new_img])
                        st.cache_data.clear()
                        st.rerun()
                else: st.warning("PHOTO REQUIRED")

else:
    st.warning("⚠️ SYSTEM WAITING FOR DATA...")
