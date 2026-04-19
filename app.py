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

# --- 📸 AUTO-UPLOAD TO IMGBB FUNCTION ---
def upload_to_imgbb(file):
    try:
        url = "https://api.imgbb.com/1/upload"
        file_content = file.read()
        payload = {
            "key": IMGBB_API_KEY,
            "image": base64.b64encode(file_content).decode('utf-8'),
        }
        res = requests.post(url, payload)
        return res.json()['data']['url']
    except Exception as e:
        st.error(f"UPLOAD_FAILED: {e}")
        return None

# --- UI SETTINGS ---
st.set_page_config(page_title="BOSS TANG | NEON VAULT", layout="wide", page_icon="📟")

# --- SCI-FI UI DESIGN (CSS) ---
st.markdown("""
    <style>
    .stApp { background-color: #050505; color: #00f2ff; }
    [data-testid="stMetricValue"] { color: #00f2ff !important; text-shadow: 0 0 10px #00f2ff; }
    .stMetric { background: rgba(0, 242, 255, 0.05); border: 1px solid #00f2ff; border-radius: 5px; padding: 20px; }
    .stButton>button {
        background-color: transparent; color: #00f2ff; border: 2px solid #00f2ff;
        width: 100%; text-transform: uppercase; font-weight: bold; transition: 0.3s;
    }
    .stButton>button:hover { background-color: #00f2ff !important; color: #000 !important; box-shadow: 0 0 20px #00f2ff; }
    .card-frame {
        border: 1px solid #1a1a1a; padding: 15px; border-radius: 10px;
        background: #0a0a0a; transition: all 0.4s; text-align: center; margin-bottom: 20px;
    }
    .card-frame:hover { border-color: #00f2ff; transform: translateY(-5px); box-shadow: 0 5px 15px rgba(0, 242, 255, 0.3); }
    label { color: #00f2ff !important; font-weight: bold; text-transform: uppercase; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input { background-color: #0a0a0a !important; color: #00f2ff !important; border: 1px solid #333 !important; }
    button[data-baseweb="tab"] p { font-size: 18px !important; color: #00f2ff !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER SECTION ---
col_h1, col_h2 = st.columns([0.8, 0.2])
with col_h1:
    st.title("📟 ULTRA-CARD VAULT v4.0")
    st.caption("// NEURAL_LINK: ACTIVE // STORAGE: IMGBB_CLOUD")
with col_h2:
    privacy_mode = st.toggle("🔒 Privacy Mode", value=False)

# --- 1. DATA LOADING ---
@st.cache_data(ttl=15)
def load_data():
    try:
        data = pd.read_csv(SHEET_URL)
        cols = ['Buy_Price', 'Grade_Fee', 'Market_Price', 'Quantity']
        for col in cols:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        return data
    except: return pd.DataFrame()

df = load_data()

# --- 2. MAIN LOGIC ---
if not df.empty:
    df['Total_Cost'] = (df['Buy_Price'] + df.get('Grade_Fee', 0)) * df['Quantity']
    df['Total_Market_Value'] = df['Market_Price'] * df['Quantity']
    df['Net_Profit'] = df['Total_Market_Value'] - df['Total_Cost']

    def f_v(v): return "********" if privacy_mode else f"${v:,.2f}"
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("INITIAL_CAPITAL", f_v(df['Total_Cost'].sum()))
    m2.metric("CURRENT_VALUATION", f_v(df['Total_Market_Value'].sum()))
    m3.metric("NET_PROFIT", f_v(df['Net_Profit'].sum()))
    m4.metric("ASSET_COUNT", f"{int(df['Quantity'].sum())} UNITS")

    st.write("---")

    with st.expander("📝 NEW_ENTRY_SEQUENCER"):
        with st.form("scifi_entry", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            with c1:
                cat = st.selectbox("TYPE", ["One Piece", "Pokemon", "F1", "Football", "Others"])
                name = st.text_input("ASSET_NAME")
                c_id = st.text_input("SERIAL_ID")
            with c2:
                c_set = st.text_input("BATCH/SET")
                buy = st.number_input("COST ($)", min_value=0.0)
                fee = st.number_input("FEE ($)", min_value=0.0)
            with c3:
                score = st.text_input("GRADE (PSA/BGS)")
                market = st.number_input("MARKET ($)", min_value=0.0)
                qty = st.number_input("QUANTITY", min_value=1, step=1)
            
            uploaded_file = st.file_uploader("📸 UPLOAD CARD IMAGE (AUTO-SYNC)", type=['jpg', 'jpeg', 'png'])
            
            if st.form_submit_button("EXECUTE_RECORD_DATA"):
                if uploaded_file:
                    with st.spinner("UPLOADING..."):
                        img_url = upload_to_imgbb(uploaded_file)
                        if img_url:
                            try:
                                client = get_gspread_client()
                                sh = client.open_by_url(SHEET_NAME_URL).sheet1
                                sh.append_row([c_id, cat, name, c_set, int(qty), buy, fee, market, score, img_url])
                                st.success("SYNC_COMPLETE")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e: st.error(f"SHEET_ERROR: {e}")
                else:
                    st.warning("ERROR: IMAGE REQUIRED")

    tab1, tab2 = st.tabs(["💾 VISUAL_ARCHIVE", "📊 DATA_LOG"])

    with tab1:
        cols = st.columns(4)
        for idx, row in df.iterrows():
            with cols[idx % 4]:
                unit_cost = row.get('Buy_Price', 0) + row.get('Grade_Fee', 0)
                pl = row.get('Market_Price', 0) - unit_cost
                status_color = "#00ff88" if pl >= 0 else "#ff4444"
                
                st.markdown(f'<div class="card-frame">', unsafe_allow_html=True)
                st.write(f"**{row.get('Card_Name', 'Unknown')}**")
                
                # --- 🛡️ IMAGE GUARD: ป้องกัน Error จากค่าว่าง ---
                raw_img = row.get('Image_URL', "")
                if pd.notna(raw_img) and isinstance(raw_img, str) and raw_img.startswith("http"):
                    st.image(raw_img, use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/300x400/0a0a0a/00f2ff?text=IMAGE+NOT+FOUND", use_container_width=True)
                
                st.caption(f"ID: {row.get('Card_ID', 'N/A')} // {row.get('Grade_Score', 'N/A')}")
                price_display = "********" if privacy_mode else f"${row.get('Market_Price', 0):,.2f}"
                st.markdown(f"<span style='color:{status_color}; font-size:20px; font-weight:bold;'>{price_display}</span>", unsafe_allow_html=True)
                st.markdown(f'<div style="color:{status_color}; font-size:10px; font-weight:bold;">{"▲ PROFIT" if pl >= 0 else "▼ LOSS"}</div>', unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)

    with tab2:
        st.dataframe(df, use_container_width=True)
else:
    st.warning("⚠️ SYSTEM_OFFLINE: CHECK GOOGLE_SHEET_CONNECTION")
