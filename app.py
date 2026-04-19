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
st.set_page_config(page_title="BOSS TANG | ELITE VAULT", layout="wide", page_icon="⚡")

# --- CYBERNETIC UI DESIGN (CSS) ---
st.markdown("""
    <style>
    /* Main Background & Fonts */
    .stApp { background-color: #050505; color: #00f2ff; }
    
    /* Neon Text Shadow */
    h1, h2, h3 { 
        text-shadow: 0 0 15px rgba(0, 242, 255, 0.7); 
        letter-spacing: 2px;
    }

    /* Privacy Mode Blur */
    .privacy-blur {
        filter: blur(8px);
        transition: 0.3s;
    }
    .privacy-blur:hover { filter: blur(0px); }

    /* Card Styling & Hover Effects */
    .card-frame {
        border: 1px solid #1a1a1a;
        padding: 15px;
        border-radius: 10px;
        background: linear-gradient(145deg, #0a0a0a, #111);
        transition: all 0.4s ease-in-out;
        text-align: center;
        margin-bottom: 20px;
    }
    .card-frame:hover {
        border-color: #00f2ff;
        transform: translateY(-10px) scale(1.02);
        box-shadow: 0 10px 30px rgba(0, 242, 255, 0.3);
    }

    /* Profit/Loss Badge */
    .status-badge {
        padding: 2px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
        text-transform: uppercase;
    }

    /* Input Fields Styling */
    label { color: #00f2ff !important; font-weight: bold; }
    .stTextInput>div>div>input, .stNumberInput>div>div>input {
        background-color: #0a0a0a !important;
        color: #00f2ff !important;
        border: 1px solid #333 !important;
    }

    /* Tabs Styling */
    button[data-baseweb="tab"] p { font-size: 18px !important; color: #00f2ff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- HEADER & PRIVACY TOGGLE ---
col_h1, col_h2 = st.columns([0.8, 0.2])
with col_h1:
    st.title("📟 ULTRA-CARD VAULT ELITE")
    st.caption("// SYSTEM STATUS: OPERATIONAL // AUTHORIZED ACCESS ONLY")
with col_h2:
    privacy_mode = st.toggle("🔒 Privacy Mode", value=False)

# --- 1. DATA LOADING ---
@st.cache_data(ttl=30)
def load_data():
    try:
        data = pd.read_csv(SHEET_URL)
        cols = ['Buy_Price', 'Grade_Fee', 'Market_Price', 'Quantity']
        for col in cols:
            if col in data.columns:
                data[col] = pd.to_numeric(data[col], errors='coerce').fillna(0)
        return data
    except:
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # --- 2. ADVANCED CALCULATIONS ---
    df['Unit_Cost'] = df['Buy_Price'] + df.get('Grade_Fee', 0)
    df['Total_Cost'] = df['Unit_Cost'] * df['Quantity']
    df['Total_Market_Value'] = df['Market_Price'] * df['Quantity']
    df['Profit_Loss'] = df['Total_Market_Value'] - df['Total_Cost']
    
    # --- 3. DASHBOARD METRICS ---
    def format_val(val):
        return "********" if privacy_mode else f"${val:,.2f}"

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("TOTAL_CAPITAL", format_val(df['Total_Cost'].sum()))
    m2.metric("VAULT_VALUATION", format_val(df['Total_Market_Value'].sum()))
    
    total_pl = df['Profit_Loss'].sum()
    pl_color = "normal" if total_pl >= 0 else "inverse"
    m3.metric("NET_RESULT", format_val(total_pl), delta=None if privacy_mode else f"{total_pl:,.2f}")
    m4.metric("ASSET_COUNT", f"{int(df['Quantity'].sum())} UNITS")

    st.divider()

    # --- 4. DATA ENTRY SYSTEM ---
    with st.expander("📝 RECORD_NEW_ASSET"):
        with st.form("entry_form"):
            f1, f2, f3 = st.columns(3)
            with f1:
                cat = st.selectbox("TYPE", ["One Piece", "Pokemon", "F1", "Football", "Others"])
                name = st.text_input("ASSET_NAME")
                c_id = st.text_input("SERIAL_ID")
            with f2:
                c_set = st.text_input("SET_ORIGIN")
                buy = st.number_input("BUY_PRICE ($)", min_value=0.0)
                fee = st.number_input("GRADE_FEE ($)", min_value=0.0)
            with f3:
                score = st.text_input("GRADE_SCORE (PSA/BGS)")
                market = st.number_input("CURRENT_MARKET ($)", min_value=0.0)
                qty = st.number_input("QUANTITY", min_value=1, step=1)
            
            img = st.text_input("IMAGE_URL")
            if st.form_submit_button("CONFIRM_DATA_ENTRY"):
                try:
                    client = get_gspread_client()
                    sh = client.open_by_url(SHEET_NAME_URL).sheet1
                    sh.append_row([c_id, cat, name, c_set, int(qty), buy, fee, market, score, img])
                    st.success("DATA_STRAND_SYNCED")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e: st.error(f"SYNC_ERROR: {e}")

    # --- 5. VISUAL ARCHIVE & ANALYTICS ---
    tab1, tab2, tab3 = st.tabs(["🖼️ VISUAL_ARCHIVE", "📊 ANALYTICS", "📑 RAW_LOG"])

    with tab1:
        cols = st.columns(4)
        for idx, row in df.iterrows():
            with cols[idx % 4]:
                pl = row['Market_Price'] - row['Unit_Cost']
                status_color = "#00ff88" if pl >= 0 else "#ff4444"
                status_text = "PROFIT" if pl >= 0 else "LOSS"
                
                st.markdown(f'''
                    <div class="card-frame">
                        <div style="font-size:14px; font-weight:bold; margin-bottom:10px;">{row['Card_Name']}</div>
                        <img src="{row['Image_URL'] if pd.notna(row['Image_URL']) else 'https://via.placeholder.com/200x280/0a0a0a/00f2ff?text=NO+DATA'}" 
                             style="width:100%; border-radius:5px; margin-bottom:10px;">
                        <div style="font-size:11px; color:#888;">{row['Card_ID']} // {row['Grade_Score']}</div>
                        <div style="color:{status_color}; font-weight:bold; font-size:18px; margin:5px 0;">
                            {"$ *****" if privacy_mode else f"${row['Market_Price']:,.2f}"}
                        </div>
                        <span class="status-badge" style="background-color:{status_color}22; color:{status_color}; border:1px solid {status_color}">
                            {status_text}
                        </span>
                    </div>
                ''', unsafe_allow_html=True)

    with tab2:
        st.subheader("// CATEGORY_DYNAMICS")
        # สรุปตามหมวดหมู่
        cat_analysis = df.groupby('Category').agg({
            'Quantity': 'sum',
            'Total_Cost': 'sum',
            'Total_Market_Value': 'sum',
            'Profit_Loss': 'sum'
        })
        st.dataframe(cat_analysis.style.background_gradient(subset=['Profit_Loss'], cmap='RdYlGn'), use_container_width=True)

    with tab3:
        st.dataframe(df, use_container_width=True)

else:
    st.warning("⚠️ SYSTEM_OFFLINE: PLEASE CHECK DATA_SOURCE_LINK")
