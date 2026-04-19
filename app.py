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
st.set_page_config(page_title="BOSS TANG | NEON VAULT", layout="wide", page_icon="📟")

# --- SCI-FI UI DESIGN (CSS) ---
st.markdown("""
    <style>
    /* Main Background */
    .stApp {
        background-color: #050505;
        color: #00f2ff;
    }
    
    /* แก้ไขสี Label (ชื่อช่องกรอกต่างๆ) ให้อ่านง่าย */
    label, .stSelectbox label, .stTextInput label, .stNumberInput label {
        color: #00f2ff !important;
        text-transform: uppercase;
        font-weight: bold;
        letter-spacing: 1px;
    }

    /* แก้ไขสีตัวหนังสือใน Tabs */
    button[data-baseweb="tab"] p {
        color: #00f2ff !important;
        font-size: 18px;
        font-weight: bold;
    }

    /* Metrics Styling */
    [data-testid="stMetricValue"] {
        color: #00f2ff !important;
        font-family: 'Courier New', Courier, monospace;
        text-shadow: 0 0 10px #00f2ff;
    }
    
    .stMetric {
        background: rgba(0, 242, 255, 0.05);
        border: 1px solid #00f2ff;
        border-radius: 5px;
        padding: 20px;
        box-shadow: inset 0 0 15px rgba(0, 242, 255, 0.1);
    }

    /* Sci-Fi Headers */
    h1, h2, h3 {
        color: #00f2ff !important;
        text-transform: uppercase;
        letter-spacing: 3px;
        font-family: 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
        border-left: 5px solid #00f2ff;
        padding-left: 15px;
    }

    /* Form & Buttons */
    .stButton>button {
        background-color: transparent;
        color: #00f2ff;
        border: 2px solid #00f2ff;
        width: 100%;
        text-transform: uppercase;
        font-weight: bold;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #00f2ff !important;
        color: #000 !important;
        box-shadow: 0 0 20px #00f2ff;
    }

    /* Card Gallery Frame */
    .card-frame {
        border: 1px solid #333;
        padding: 15px;
        border-radius: 5px;
        background: #0a0a0a;
        transition: 0.3s;
        text-align: center;
    }
    .card-frame:hover {
        border-color: #00f2ff;
        box-shadow: 0 0 15px rgba(0, 242, 255, 0.3);
    }
    
    /* Caption styling */
    .stCaption {
        color: #a0f9ff !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER SECTION ---
st.title("📟 ULTRA-CARD VAULT v3.0")
st.write("--- SYSTEM ONLINE // ACCESS GRANTED ---")

# --- 1. DATA LOADING ---
@st.cache_data(ttl=30)
def load_data():
    try:
        data = pd.read_csv(SHEET_URL)
        # ตรวจสอบชื่อคอลัมน์และแก้ไขค่านอนตัวเลข
        cols_to_fix = ['Buy_Price', 'Grade_Fee', 'Market_Price', 'Quantity']
        for col in cols_to_fix:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        return data
    except:
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # --- 2. SCI-FI DASHBOARD METRICS ---
    # ใช้ .get() เพื่อป้องกันกรณีชื่อคอลัมน์ใน Google Sheet ไม่ตรง
    df['Total_Cost'] = (df.get('Buy_Price', 0) + df.get('Grade_Fee', 0)) * df.get('Quantity', 0)
    df['Total_Market_Value'] = df.get('Market_Price', 0) * df.get('Quantity', 0)
    df['Net_Profit'] = df['Total_Market_Value'] - df['Total_Cost']

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("INITIAL_CAPITAL", f"${df['Total_Cost'].sum():,.2f}")
    m2.metric("CURRENT_VALUATION", f"${df['Total_Market_Value'].sum():,.2f}")
    m3.metric("NET_PROFIT_LOSS", f"${df['Net_Profit'].sum():,.2f}")
    m4.metric("TOTAL_ASSETS", f"{int(df['Quantity'].sum())} UNITS")

    st.write("---")

    # --- 3. INPUT SYSTEM ---
    with st.expander("📝 NEW_ENTRY_SEQUENCER"):
        with st.form("scifi_entry"):
            c1, c2, c3 = st.columns(3)
            with c1:
                cat = st.selectbox("TYPE", ["One Piece", "Pokemon", "F1", "Football", "Others"])
                name = st.text_input("ASSET_NAME")
                c_id = st.text_input("ASSET_SERIAL_ID")
            with c2:
                c_set = st.text_input("BATCH/SET")
                buy = st.number_input("ACQUISITION_COST ($)", min_value=0.0)
                fee = st.number_input("ENHANCEMENT_FEE ($)", min_value=0.0)
            with c3:
                score = st.text_input("STABILITY_GRADE (e.g. PSA 10)")
                market = st.number_input("CURRENT_MARKET ($)", min_value=0.0)
                qty = st.number_input("QUANTITY", min_value=1, step=1)
            
            img = st.text_input("VISUAL_DATA_LINK (Image URL)")
            
            if st.form_submit_button("EXECUTE_RECORD_DATA"):
                try:
                    client = get_gspread_client()
                    sh = client.open_by_url(SHEET_NAME_URL).sheet1
                    sh.append_row([c_id, cat, name, c_set, int(qty), buy, fee, market, score, img])
                    st.success("DATA_STRAND_ADDED_SUCCESSFULLY")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"SYSTEM_ERROR: {e}")

    # --- 4. VISUAL ARCHIVE (GALLERY) ---
    tab1, tab2 = st.tabs(["💾 VISUAL_ARCHIVE", "📊 RAW_DATA_LOG"])

    with tab1:
        st.write("### // SCANNING ASSETS...")
        cols = st.columns(4)
        for idx, row in df.iterrows():
            with cols[idx % 4]:
                st.markdown(f'<div class="card-frame">', unsafe_allow_html=True)
                st.markdown(f"**{row.get('Card_Name', 'Unknown')}**")
                
                # Image Logic
                img_url = row.get('Image_URL', '')
                if pd.notna(img_url) and str(img_url).startswith('http'):
                    st.image(img_url, use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/300x400/0a0a0a/00f2ff?text=NO+VISUAL+DATA", use_container_width=True)
                
                # Sub-data (ใช้ .get ป้องกัน Error)
                c_id_val = row.get('Card_ID', 'N/A')
                g_score = row.get('Grade_Score', 'RAW')
                m_price = row.get('Market_Price', 0)
                
                st.caption(f"ID: {c_id_val} // {g_score}")
                st.markdown(f"<span style='color:#00f2ff; font-weight:bold;'>VALUE: ${m_price:,.2f}</span>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
                st.write("") 

    with tab2:
        # ปรับแต่งตารางให้อ่านง่ายขึ้นใน Dark Mode
        st.dataframe(df, use_container_width=True)

else:
    st.warning("⚠️ WARNING: DATA_SOURCE_NOT_DETECTED. PLEASE CHECK GOOGLE_SHEETS_LINK.")
