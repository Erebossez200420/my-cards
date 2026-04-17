import streamlit as st
import pandas as pd
import requests

# --- ส่วนตั้งค่า (Configuration) ---
# 1. ลิงก์ Google Sheet ที่คุณ Publish เป็น CSV (สอนวิธีทำในข้อ 2)
SHEET_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTJncpOFgpWjWoU0kXjPoPeqj3pvrppiy0MeBNHIP2tv7pGQREloJB4CCw0UNONN4R64W6BBJS61VTO/pub?output=csv" 

# 2. API Key ของ Pokémon (ไปสมัครฟรีที่ pokemontcg.io)
POKEMON_API_KEY = "ใส่_API_KEY_ของคุณที่นี่"

st.set_page_config(page_title="Card Portfolio Tracker", layout="wide")

# --- ฟังก์ชันดึงราคา (API logic) ---
def get_market_price(row):
    game = row['Game_Sport'].lower()
    card_id = str(row['Card_ID'])
    
    # ดึงราคา Pokémon (ใช้ API จริง)
    if 'pokemon' in game:
        try:
            url = f"https://api.pokemontcg.io/v2/cards/{card_id}"
            headers = {"X-Api-Key": POKEMON_API_KEY}
            response = requests.get(url, headers=headers).json()
            return response['data']['tcgplayer']['prices']['holofoil']['market']
        except:
            return row['Market_Price'] # ถ้าดึงไม่ได้ ให้ใช้ราคาเดิมในตาราง

    # สำหรับ One Piece / F1 / Football 
    # ปัจจุบัน API ฟรีที่เสถียร 100% หายาก แนะนำให้ใส่ราคา Manual ใน Sheet 
    # หรือใช้ Logic คำนวณเบื้องต้นไปก่อน
    else:
        return row['Market_Price']

# --- หน้าจอหลัก ---
st.title("🏆 My Card Collection Dashboard")

try:
    # ดึงข้อมูลจาก Google Sheets
    df = pd.read_csv(SHEET_URL)
    
    # คำนวณค่าต่างๆ
    df['Current_Price'] = df.apply(get_market_price, axis=1)
    df['Total_Value'] = df['Current_Price'] * df['Quantity']
    df['Profit_Loss'] = df['Total_Value'] - (df['Buy_Price'] * df['Quantity'])

    # สรุปผลด้านบน
    col1, col2, col3 = st.columns(3)
    col1.metric("มูลค่าพอร์ตรวม", f"${df['Total_Value'].sum():,.2f}")
    col2.metric("กำไร/ขาดทุนรวม", f"${df['Profit_Loss'].sum():,.2f}", f"{ (df['Profit_Loss'].sum()/df['Total_Value'].sum())*100:.2f}%")
    col3.metric("จำนวนการ์ดทั้งหมด", f"{df['Quantity'].sum()} ใบ")

    st.divider()

    # แสดงตารางข้อมูล
    st.subheader("🗂️ รายการการ์ดในครอบครอง")
    st.dataframe(df[['Game_Sport', 'Card_Name', 'Set_Name', 'Quantity', 'Buy_Price', 'Current_Price', 'Total_Value']], use_container_width=True)

except:
    st.error("กรุณาตรวจสอบลิงก์ Google Sheet ของคุณ")
    st.info("อย่าลืม Publish Google Sheet เป็น CSV ก่อนนำลิงก์มาวางนะครับ")
