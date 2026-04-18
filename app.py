import streamlit as st
import pandas as pd
import requests
import gspread
from google.oauth2.service_account import Credentials
import time

# --- 1. CONFIG & CONNECTION ---
# ใส่ข้อมูลส่วนตัวของคุณ
PRICECHARTING_TOKEN = "c0b53bce27c1bdab90b1605249e600dc43dfd1d5"
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTJncpOFgpWjWoU0kXjPoPeqj3pvrppiy0MeBNHIP2tv7pGQREloJB4CCw0UNONN4R64W6BBJS61VTO/pub?output=csv"
SHEET_NAME_URL = "https://docs.google.com/spreadsheets/d/1oiHsqmiqd5b159EAuIZ2DcyhjoYCpXDYftQnsVq6RRA/edit?gid=1680643019#gid=1680643019" # แก้เป็น URL หน้าปกติของ Sheet คุณ

# เชื่อมต่อ Google Sheets (Write Access)
def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

# --- 2. FUNCTIONS ---
def fetch_realtime_price(name, card_num):
    # ค้นหาด้วยชื่อและเลขการ์ดเพื่อให้แม่นยำ
    query = f"{name} {card_num}".replace(" ", "+")
    url = f"https://www.pricecharting.com/api/products?t={PRICECHARTING_TOKEN}&q={query}"
    try:
        response = requests.get(url)
        data = response.json()
        if data.get("status") == "success" and data.get("products"):
            # ดึงราคา Loose Price และหาร 100 เพราะ API ส่งหน่วยเป็น pennies
            price = data["products"][0].get("price-guide-details", {}).get("loose-price", 0)
            return float(price) / 100
    except:
        return 0.0
    return 0.0

# --- 3. UI DASHBOARD ---
st.title("🛡️ Ultra Card Portfolio Manager")

# ตรวจสอบว่าแชร์สิทธิ์หรือยัง
client = get_gspread_client()
# เปิด Sheet โดยใช้ URL (ต้องแชร์ Editor ให้เมลบอทก่อน)
try:
    sh = client.open_by_url(SHEET_NAME_URL).sheet1
except:
    st.warning("กรุณาแชร์สิทธิ์ Editor ใน Google Sheets ให้เมลบอทของคุณก่อนครับ")

# --- ส่วนเพิ่มข้อมูลใหม่ ---
with st.expander("➕ เพิ่มการ์ดใหม่เข้าคลัง (Add New Card)"):
    with st.form("new_card", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            cat = st.selectbox("Category", ["Pokemon", "One Piece", "Dragon Ball", "F1", "Football"])
            c_name = st.text_input("ชื่อการ์ด / นักแข่ง")
            c_set = st.text_input("ชื่อชุด (Set Name)")
        with col2:
            c_num = st.text_input("เลขการ์ด (Card # เช่น OP01-016)")
            buy_p = st.number_input("ราคาซื้อ ($)", min_value=0.0)
            qty = st.number_input("จำนวน", min_value=1, step=1)
            img = st.text_input("Link รูปภาพ")
            
        if st.form_submit_button("บันทึกลง Google Sheet"):
            new_row = [c_num, cat, c_name, c_set, qty, buy_p, 0.0, img]
            sh.append_row(new_row)
            st.success(f"บันทึก {c_name} ลง Google Sheet สำเร็จ!")
            st.cache_data.clear() # ล้าง Cache เพื่อให้ข้อมูลใหม่โชว์ทันที

# --- ส่วนแสดงผล Portfolio ---
@st.cache_data(ttl=60)
def load_data():
    return pd.read_csv(SHEET_URL)

try:
    df = load_data()
    
    # คำนวณเบื้องต้น
    df['Market_Price'] = df['Market_Price'].fillna(0)
    df['Current_Value'] = df['Market_Price'] * df['Quantity']
    df['Profit/Loss'] = df['Current_Value'] - (df['Buy_Price'] * df['Quantity'])

    # Dashboard Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Value", f"${df['Current_Value'].sum():,.2f}")
    m2.metric("Total Profit/Loss", f"${df['Profit/Loss'].sum():,.2f}")
    m3.metric("Total Cards", f"{df['Quantity'].sum()} items")

    # ระบบอัปเดตราคาตลาด
    if st.button("🔄 อัปเดตราคาตลาดล่าสุด (Sync Prices)"):
        st.info("กำลังดึงราคาจาก PriceCharting API... กรุณารอสักครู่")
        updated_prices = []
        progress_bar = st.progress(0)
        
        for i, row in df.iterrows():
            new_p = fetch_realtime_price(row['Card_Name'], row['Card_ID'])
            updated_prices.append(new_p)
            # อัปเดตใน Google Sheet ทีละแถว (คอลัมน์ Market_Price คือคอลัมน์ที่ 7)
            sh.update_cell(i + 2, 7, new_p) 
            progress_bar.progress((i + 1) / len(df))
            time.sleep(1.1) # กฎ 1 request ต่อวินาที
            
        st.success("อัปเดตราคาตลาดและบันทึกลง Sheet เรียบร้อย!")
        st.cache_data.clear()
        st.rerun()

    st.dataframe(df, use_container_width=True)

except Exception as e:
    st.error(f"กรุณาตรวจสอบโครงสร้างตารางใน Google Sheet: {e}")
