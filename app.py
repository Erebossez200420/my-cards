import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import time

# --- CONFIG ---
PRICECHARTING_TOKEN = "c0b53bce27c1bdab90b1605249e600dc43dfd1d5"
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTJncpOFgpWjWoU0kXjPoPeqj3pvrppiy0MeBNHIP2tv7pGQREloJB4CCw0UNONN4R64W6BBJS61VTO/pub?output=csv"
SHEET_NAME_URL = "https://docs.google.com/spreadsheets/d/1oiHsqmiqd5b159EAuIZ2DcyhjoYCpXDYftQnsVq6RRA/edit" 

def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

def fetch_realtime_price(category, name, card_num):
    # ปรับ Logic: ใช้ Category + เลขการ์ด เพื่อให้ PriceCharting หาเจอแม่นขึ้น
    search_term = f"{category} {card_num}".replace(" ", "+")
    url = f"https://www.pricecharting.com/api/products?t={PRICECHARTING_TOKEN}&q={search_term}"
    
    try:
        res = requests.get(url).json()
        if res.get("status") == "success" and res.get("products"):
            product = res["products"][0]
            # ราคาหน่วย pennies หาร 100
            price = product.get("price-guide-details", {}).get("loose-price", 0)
            return float(price) / 100
    except:
        return 0.0
    return 0.0

st.set_page_config(page_title="Ultra Card Portfolio", layout="wide")
st.title("🛡️ Ultra Card Portfolio")

# --- ส่วนเพิ่มข้อมูล ---
with st.expander("➕ Add New Card"):
    with st.form("new_card", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            c_id = st.text_input("Card ID / Number (เช่น OP05-119)")
            cat = st.selectbox("Category", ["One Piece", "Pokemon", "F1", "Football"])
            name = st.text_input("Card Name")
        with c2:
            c_set = st.text_input("Set Name")
            qty = st.number_input("Quantity", min_value=1, value=1)
            buy = st.number_input("Buy Price ($)", min_value=0.0)
            img_url = st.text_input("Image URL (Link รูปภาพ)")
        
        if st.form_submit_button("Save to Google Sheet"):
            try:
                client = get_gspread_client()
                sh = client.open_by_url(SHEET_NAME_URL).sheet1
                sh.append_row([c_id, cat, name, c_set, qty, buy, 0, img_url])
                st.success("บันทึกสำเร็จ! ข้อมูลจะปรากฏบนเว็บใน 1-2 นาที")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"บันทึกไม่ได้: {e}")

# --- ส่วนแสดงผล ---
@st.cache_data(ttl=60)
def load_data():
    return pd.read_csv(SHEET_URL)

try:
    df = load_data()
    
    # คำนวณภาพรวมพอร์ต
    total_val = (df['Market_Price'] * df['Quantity']).sum()
    st.metric("Total Portfolio Value", f"${total_val:,.2f}")

    # แสดงตารางข้อมูล
    st.dataframe(df, use_container_width=True)
    
    # ระบบ Sync ราคา
    if st.button("🔄 Sync Market Prices (API)"):
        client = get_gspread_client()
        sh = client.open_by_url(SHEET_NAME_URL).sheet1
        
        with st.status("กำลังอัปเดตราคาตลาดจาก PriceCharting...", expanded=True) as status:
            for i, row in df.iterrows():
                # --- จุดที่แก้ไข: ส่งค่าให้ครบตามที่ฟังก์ชันต้องการ ---
                live_p = fetch_realtime_price(row['Category'], row['Card_Name'], row['Card_ID'])
                
                sh.update_cell(i + 2, 7, live_p) # คอลัมน์ G
                st.write(f"✅ {row['Card_Name']} ({row['Card_ID']}): ${live_p}")
                time.sleep(1.1)
            status.update(label="Sync เสร็จสมบูรณ์!", state="complete")
        
        st.cache_data.clear()
        st.rerun()

    # แถม: ส่วนแสดงรูปภาพการ์ดแบบ Gallery
    if st.checkbox("Show Card Gallery"):
        cols = st.columns(4)
        for idx, row in df.iterrows():
            with cols[idx % 4]:
                if pd.notna(row['Image_URL']) and str(row['Image_URL']).startswith('http'):
                    st.image(row['Image_URL'], caption=row['Card_Name'], use_container_width=True)
                else:
                    st.write(f"🖼️ {row['Card_Name']} (No Image)")

except Exception as e:
    st.info("ระบบกำลังโหลดข้อมูลหรือรอการตั้งค่าโครงสร้างตาราง...")
