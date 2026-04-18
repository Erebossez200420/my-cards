import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import time

# --- CONFIG ---
PRICECHARTING_TOKEN = "c0b53bce27c1bdab90b1605249e600dc43dfd1d5"
# ลิงก์ CSV สำหรับอ่าน (แสดงผล)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTJncpOFgpWjWoU0kXjPoPeqj3pvrppiy0MeBNHIP2tv7pGQREloJB4CCw0UNONN4R64W6BBJS61VTO/pub?output=csv"
# ลิงก์ Sheet ปกติสำหรับเขียน (บันทึก)
SHEET_NAME_URL = "https://docs.google.com/spreadsheets/d/1oiHsqmiqd5b159EAuIZ2DcyhjoYCpXDYftQnsVq6RRA/edit?gid=1680643019#gid=1680643019" 

def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

# ฟังก์ชันดึงราคา
def fetch_realtime_price(category, name, card_num):
    # ปรับปรุง: เอา Category มาผสมกับรหัสเพื่อให้ API หาเจอแน่นอน
    # เช่น "One Piece OP13-119"
    search_term = f"{category} {card_num}".replace(" ", "+")
    url = f"https://www.pricecharting.com/api/products?t={PRICECHARTING_TOKEN}&q={search_term}"
    
    try:
        res = requests.get(url).json()
        if res.get("status") == "success" and res.get("products"):
            # ดึงราคาของผลลัพธ์ตัวแรกที่เจอ
            product = res["products"][0]
            price = product.get("price-guide-details", {}).get("loose-price", 0)
            return float(price) / 100
    except:
        return 0.0
    return 0.0

# และในตอนเรียกใช้ฟังก์ชัน (ตอนกดปุ่ม Sync):
# ให้แก้เป็น: live_p = fetch_realtime_price(row['Category'], row['Card_Name'], row['Card_ID'])

st.title("🛡️ Ultra Card Portfolio")

# --- ส่วนเพิ่มข้อมูล ---
with st.expander("➕ Add New Card"):
    with st.form("new_card"):
        c1, c2 = st.columns(2)
        with c1:
            c_id = st.text_input("Card ID (เช่น OP13-119)")
            cat = st.selectbox("Category", ["Pokemon", "One Piece", "F1", "Football"])
            name = st.text_input("Card Name")
        with c2:
            c_set = st.text_input("Set Name")
            qty = st.number_input("Quantity", min_value=1, value=1)
            buy = st.number_input("Buy Price ($)", min_value=0.0)
        
        if st.form_submit_button("Save to Google Sheet"):
            try:
                client = get_gspread_client()
                sh = client.open_by_url(SHEET_NAME_URL).sheet1
                # บันทึกโดยเรียงลำดับตามหัวข้อตาราง (A-H)
                sh.append_row([c_id, cat, name, c_set, qty, buy, 0, ""])
                st.success("บันทึกสำเร็จ! ข้อมูลจะปรากฏบนเว็บใน 1-2 นาที (เนื่องจาก Google Delay)")
                st.cache_data.clear() # บังคับล้างคลาวด์เพื่อให้ดึงใหม่
            except Exception as e:
                st.error(f"บันทึกไม่ได้: {e}")

# --- ส่วนแสดงผล ---
@st.cache_data(ttl=60) # ตั้งให้ดึงใหม่ทุก 60 วินาที
def load_data():
    return pd.read_csv(SHEET_URL)

try:
    df = load_data()
    # แสดงตาราง
    st.dataframe(df, use_container_width=True)
    
    if st.button("🔄 Sync Market Prices (API)"):
        client = get_gspread_client()
        sh = client.open_by_url(SHEET_NAME_URL).sheet1
        st.info("กำลังอัปเดตราคาตลาด... กรุณารอสักครู่")
        
        for i, row in df.iterrows():
            # ใช้ Card Name กับ Card ID ในการหา
            live_p = fetch_realtime_price(row['Card_Name'], row['Card_ID'])
            sh.update_cell(i + 2, 7, live_p) # อัปเดตคอลัมน์ G (7)
            time.sleep(1.1)
        
        st.success("อัปเดตราคาตลาดเรียบร้อย!")
        st.cache_data.clear()
        st.rerun()
except:
    st.info("กำลังรอข้อมูลจาก Google Sheets...")
