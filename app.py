import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import requests
import time

# --- CONFIG ---
# สำหรับ Pokemon เราจะใช้ API ฟรีจาก pokemontcg.io
# สำหรับ One Piece เนื่องจากไม่มี API ฟรีที่ให้ราคาตรงๆ เราจะใช้ระบบค้นหาเบื้องต้น
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTJncpOFgpWjWoU0kXjPoPeqj3pvrppiy0MeBNHIP2tv7pGQREloJB4CCw0UNONN4R64W6BBJS61VTO/pub?output=csv"
SHEET_NAME_URL = "https://docs.google.com/spreadsheets/d/1oiHsqmiqd5b159EAuIZ2DcyhjoYCpXDYftQnsVq6RRA/edit" 

def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

# --- ฟังก์ชันดึงราคา "สายฟรี" ---
def fetch_free_market_price(category, card_id, name):
    cat = category.lower()
    
    try:
        # 1. ถ้าเป็น Pokemon (ใช้ API ฟรีของ pokemontcg.io)
        if "pokemon" in cat:
            # card_id ต้องเป็นรูปแบบเช่น 'sv4pt5-234'
            url = f"https://api.pokemontcg.io/v2/cards?q=id:{card_id}"
            res = requests.get(url).json()
            if res.get('data'):
                # ดึงราคากลางจาก TCGPlayer (Market Price)
                prices = res['data'][0].get('tcgplayer', {}).get('prices', {})
                # เลือกราคาแรกที่เจอ (เช่น holofoil หรือ normal)
                first_type = list(prices.keys())[0]
                return float(prices[first_type].get('market', 0))
        
        # 2. ถ้าเป็น One Piece (เนื่องจาก API ฟรีหายาก เราจะใช้ระบบจำลองราคาหรือหาจากแหล่งอื่น)
        elif "one piece" in cat:
            # ในอนาคตคุณสามารถใช้ IMPORTXML ใน Google Sheet จะง่ายกว่า
            # ตอนนี้จะคืนค่า 0 เพื่อให้คุณกรอกเอง หรือดึงจากหน้าเว็บแบบง่าย
            return 0.0 
            
    except:
        return 0.0
    return 0.0

st.set_page_config(page_title="Ultra Card Portfolio (FREE Version)", layout="wide")
st.title("🛡️ Ultra Card Portfolio")
st.caption("ระบบดึงราคาอัตโนมัติ (ฟรีสำหรับ Pokemon) | สำหรับ One Piece แนะนำกรอกใน Google Sheet")

# --- ส่วนเพิ่มข้อมูล ---
with st.expander("➕ Add New Card"):
    with st.form("new_card", clear_on_submit=True):
        c1, c2 = st.columns(2)
        with c1:
            c_id = st.text_input("Card ID (เช่น sv4pt5-234 หรือ OP05-119)")
            cat = st.selectbox("Category", ["Pokemon", "One Piece", "F1", "Football"])
            name = st.text_input("Card Name")
        with c2:
            c_set = st.text_input("Set Name")
            qty = st.number_input("Quantity", min_value=1, value=1)
            buy = st.number_input("Buy Price ($)", min_value=0.0)
            img_url = st.text_input("Image URL")
        
        if st.form_submit_button("Save to Google Sheet"):
            try:
                client = get_gspread_client()
                sh = client.open_by_url(SHEET_NAME_URL).sheet1
                sh.append_row([c_id, cat, name, c_set, qty, buy, 0, img_url])
                st.success("บันทึกข้อมูลเรียบร้อย!")
                st.cache_data.clear()
            except Exception as e:
                st.error(f"Error: {e}")

# --- ส่วนแสดงผล ---
@st.cache_data(ttl=30)
def load_data():
    return pd.read_csv(SHEET_URL)

try:
    df = load_data()
    
    # สรุปค่า
    total_buy = (df['Buy_Price'] * df['Quantity']).sum()
    total_market = (df['Market_Price'] * df['Quantity']).sum()
    
    col_m1, col_m2 = st.columns(2)
    col_m1.metric("Total Investment", f"${total_buy:,.2f}")
    col_m2.metric("Market Value", f"${total_market:,.2f}", f"{total_market - total_buy:,.2f}")

    st.dataframe(df, use_container_width=True)
    
    # ปุ่ม Sync ราคาแบบฟรี
    if st.button("🔄 Sync Market Prices (FREE API)"):
        client = get_gspread_client()
        sh = client.open_by_url(SHEET_NAME_URL).sheet1
        
        with st.status("กำลังดึงราคาจากแหล่งข้อมูลฟรี...") as status:
            for i, row in df.iterrows():
                new_price = fetch_free_market_price(row['Category'], row['Card_ID'], row['Card_Name'])
                if new_price > 0:
                    sh.update_cell(i + 2, 7, new_price)
                    st.write(f"✅ {row['Card_Name']}: ${new_price}")
                else:
                    st.write(f"❌ {row['Card_Name']}: หาราคาฟรีไม่พบ")
                time.sleep(0.5)
            status.update(label="Sync เสร็จสมบูรณ์!", state="complete")
        st.cache_data.clear()
        st.rerun()

except Exception as e:
    st.info("กำลังรอข้อมูลจาก Google Sheets...")
