import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIG ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTJncpOFgpWjWoU0kXjPoPeqj3pvrppiy0MeBNHIP2tv7pGQREloJB4CCw0UNONN4R64W6BBJS61VTO/pub?output=csv"
SHEET_NAME_URL = "https://docs.google.com/spreadsheets/d/1oiHsqmiqd5b159EAuIZ2DcyhjoYCpXDYftQnsVq6RRA/edit"

def get_gspread_client():
    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
    return gspread.authorize(creds)

# --- UI SETTINGS ---
st.set_page_config(page_title="Boss Tang Card Vault", layout="wide", page_icon="🃏")

# Custom CSS เพื่อให้ UI ดูเท่ขึ้น
# --- UI SETTINGS ---
st.set_page_config(page_title="Boss Tang Card Vault", layout="wide", page_icon="🃏")

# แก้ไขบรรทัดนี้ครับ:
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stMetric { background-color: #161b22; border: 1px solid #30363d; padding: 15px; border-radius: 10px; }
    .stDataFrame { border: 1px solid #30363d; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🃏 BOSS TANG | Card Vault")
st.subheader("พอร์ตสะสมการ์ดและการลงทุน (Manual Tracker)")

# --- 1. DATA LOADING ---
@st.cache_data(ttl=30)
def load_data():
    data = pd.read_csv(SHEET_URL)
    # จัดการค่าว่าง
    data[['Buy_Price', 'Grade_Fee', 'Market_Price']] = data[['Buy_Price', 'Grade_Fee', 'Market_Price']].fillna(0)
    return data

try:
    df = load_data()

    # --- 2. SUMMARY METRICS ---
    # คำนวณต้นทุนรวม (ค่าเครื่อง + ค่าเกรด)
    df['Total_Cost'] = (df['Buy_Price'] + df['Grade_Fee']) * df['Quantity']
    df['Total_Market_Value'] = df['Market_Price'] * df['Quantity']
    df['Profit_Loss'] = df['Total_Market_Value'] - df['Total_Cost']

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("💰 Total Invested", f"${df['Total_Cost'].sum():,.2f}")
    m2.metric("📈 Market Value", f"${df['Total_Market_Value'].sum():,.2f}")
    
    p_l = df['Profit_Loss'].sum()
    m3.metric("🔥 Total P/L", f"${p_l:,.2f}", f"{(p_l/df['Total_Cost'].sum()*100) if df['Total_Cost'].sum()>0 else 0:.1f}%")
    m4.metric("📦 Total Items", f"{df['Quantity'].sum()} Cards")

    # --- 3. ADD NEW CARD FORM ---
    with st.expander("➕ บันทึกการ์ดใบใหม่ (Add New Record)"):
        with st.form("new_card_form", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                cat = st.selectbox("หมวดหมู่", ["One Piece", "Pokemon", "F1", "Football", "Other"])
                name = st.text_input("ชื่อการ์ด / นักแข่ง")
                c_id = st.text_input("รหัสการ์ด (เช่น OP05-119)")
            with c2:
                c_set = st.text_input("ชื่อชุด (Set Name)")
                buy = st.number_input("ราคาซื้อ ($)", min_value=0.0)
                fee = st.number_input("ค่าเกรด ($)", min_value=0.0)
            with c3:
                score = st.text_input("คะแนนเกรด (เช่น PSA 10, BGS 9.5)")
                market = st.number_input("ราคาตลาดปัจจุบัน ($)", min_value=0.0)
                qty = st.number_input("จำนวน", min_value=1, step=1)
            
            img = st.text_input("ลิงก์รูปภาพ (Direct Image Link)")
            
            if st.form_submit_button("🚀 บันทึกลงคลัง"):
                try:
                    client = get_gspread_client()
                    sh = client.open_by_url(SHEET_NAME_URL).sheet1
                    # ลำดับตามชีต: Card_ID, Category, Card_Name, Set_Name, Quantity, Buy_Price, Grade_Fee, Market_Price, Grade_Score, Image_URL
                    sh.append_row([c_id, cat, name, c_set, int(qty), buy, fee, market, score, img])
                    st.success(f"บันทึก {name} เรียบร้อยแล้ว! (รอ Google Update 1 นาที)")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"เกิดข้อผิดพลาด: {e}")

    # --- 4. GALLERY & DATA TABLE ---
    tab1, tab2 = st.tabs(["🖼️ Card Gallery", "📑 Detailed List"])

    with tab1:
        # แสดงรูปภาพแบบเท่ๆ
        cols = st.columns(4)
        for idx, row in df.iterrows():
            with cols[idx % 4]:
                st.markdown(f"**{row['Card_Name']}**")
                if pd.notna(row['Image_URL']) and str(row['Image_URL']).startswith('http'):
                    st.image(row['Image_URL'], use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/300x400?text=No+Image", use_container_width=True)
                
                # แสดงเกรดถ้ามี
                if pd.notna(row['Grade_Score']):
                    st.caption(f"⭐ Grade: {row['Grade_Score']}")
                st.write(f"Cost: ${row['Buy_Price'] + row['Grade_Fee']:.2f}")
                st.divider()

    with tab2:
        st.dataframe(df, use_container_width=True)

except Exception as e:
    st.info("กำลังรอข้อมูลจาก Google Sheets ของคุณ... หากตั้งค่าเสร็จแล้วข้อมูลจะปรากฏที่นี่")
