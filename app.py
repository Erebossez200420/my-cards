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

def upload_to_imgbb(file):
    try:
        url = "https://api.imgbb.com/1/upload"
        payload = {"key": IMGBB_API_KEY, "image": base64.b64encode(file.read()).decode('utf-8')}
        res = requests.post(url, payload)
        return res.json()['data']['url']
    except: return None

# --- UI DESIGN SYSTEM (TRENDY GLASSMORPHISM) ---
st.set_page_config(page_title="VAULT 9.0", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;800&display=swap');
    
    /* Global Reset */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #05070a; font-family: 'Inter', sans-serif; }
    
    /* High Contrast Typography */
    h1, h2, h3 { color: #ffffff !important; font-weight: 800 !important; letter-spacing: -1px; }
    p, span, label { color: #ffffff !important; font-weight: 500; }
    
    /* Trendy Metric Cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #11141a 0%, #05070a 100%);
        padding: 20px; border-radius: 20px; border: 1px solid #1f2833;
        box-shadow: 0 10px 20px rgba(0,0,0,0.4);
    }
    [data-testid="stMetricValue"] { color: #00f2ff !important; font-weight: 800 !important; font-size: 32px !important; }
    [data-testid="stMetricLabel"] { color: #8892b0 !important; text-transform: uppercase; letter-spacing: 1px; }

    /* Asset Card - Modern Glass Look */
    .card-container {
        background: #11141a;
        border: 1px solid #1f2833;
        border-radius: 24px;
        padding: 16px;
        margin-bottom: 24px;
        transition: transform 0.3s ease, border-color 0.3s ease;
    }
    .card-container:hover { border-color: #00f2ff; transform: translateY(-5px); }
    
    /* Badges */
    .badge { font-size: 10px; font-weight: 800; padding: 5px 12px; border-radius: 10px; text-transform: uppercase; }
    .badge-active { background: #00f2ff; color: #05070a !important; }
    .badge-sold { background: #ff4d4d; color: #ffffff !important; }

    /* iPhone Friendly Buttons */
    .stButton button {
        background: linear-gradient(90deg, #00f2ff, #0072ff);
        color: #ffffff !important; border: none; border-radius: 16px;
        height: 3.5rem; font-weight: 800; font-size: 16px !important;
        width: 100%; transition: 0.3s;
    }
    .stButton button:hover { box-shadow: 0 0 20px rgba(0, 242, 255, 0.4); }

    /* Inputs & Forms */
    .stTextInput input, .stNumberInput input, .stSelectbox div {
        background-color: #11141a !important; color: #ffffff !important;
        border: 1px solid #1f2833 !important; border-radius: 12px !important;
        height: 3rem !important;
    }
    
    /* Tab System Customization */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; background: #11141a; padding: 5px; border-radius: 15px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; border-radius: 12px; color: #8892b0 !important; font-weight: 700;
    }
    .stTabs [aria-selected="true"] { background: #1f2833 !important; color: #00f2ff !important; border: 1px solid #00f2ff !important; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA ENGINE ---
@st.cache_data(ttl=5)
def load_data():
    try:
        raw = pd.read_csv(SHEET_URL)
        # Standardize Columns
        for col in ['Quantity', 'Buy_Price', 'Grade_Fee', 'Market_Price', 'Sell_Price']:
            if col in raw.columns:
                raw[col] = pd.to_numeric(raw[col].astype(str).str.replace(',', '').str.replace('$', ''), errors='coerce').fillna(0)
        
        raw['Cost_Basis'] = raw['Buy_Price'] + raw['Grade_Fee']
        raw['Live_Val'] = raw.apply(lambda x: x['Sell_Price'] if x['Status'] == 'Sold' else x['Market_Price'], axis=1)
        raw['Net_Profit'] = (raw['Live_Val'] - raw['Cost_Basis']) * raw['Quantity']
        raw['ROI_Pct'] = (raw['Net_Profit'] / (raw['Cost_Basis'] * raw['Quantity']).replace(0, 0.01)) * 100
        return raw
    except: return pd.DataFrame()

df = load_data()

# --- APP HEADER ---
st.markdown("<h1 style='text-align: center; margin-bottom: 0;'>💎 THE VAULT</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #8892b0 !important; margin-bottom: 20px;'>ELITE ASSET TERMINAL v9.0</p>", unsafe_allow_html=True)

if not df.empty:
    # Top Utility Bar
    ut_1, ut_2 = st.columns([0.8, 0.2])
    with ut_2:
        if st.button("🔄 REFRESH"):
            st.cache_data.clear()
            st.rerun()
    
    # Portfolio Highlights
    m1, m2, m3 = st.columns(3)
    active_mask = df['Status'] != 'Sold'
    m1.metric("HOLDING COST", f"${(df[active_mask]['Cost_Basis'] * df[active_mask]['Quantity']).sum():,.0f}")
    m2.metric("PROFIT / LOSS", f"${df['Net_Profit'].sum():,.0f}", delta=f"{df['Net_Profit'].sum():+.0f}")
    m3.metric("AVG ROI", f"{df['ROI_Pct'].mean():+.1f}%")

    st.divider()

    # Navigation Tabs
    t_main, t_edit, t_add = st.tabs(["🖼️ PORTFOLIO", "🛠️ MANAGEMENT", "✨ NEW ASSET"])

    with t_main:
        # Trendy Search & Filter
        s1, s2 = st.columns([0.6, 0.4])
        search_q = s1.text_input("🔍 Search Vault", placeholder="Card name, Set, or ID...")
        sort_by = s2.selectbox("Sort Priority", ["Latest First", "Highest Value", "Best ROI %"])

        display_df = df.copy()
        if search_q:
            display_df = display_df[display_df['Card_Name'].str.contains(search_q, case=False, na=False)]
        
        if sort_by == "Highest Value": display_df = display_df.sort_values('Live_Val', ascending=False)
        elif sort_by == "Best ROI %": display_df = display_df.sort_values('ROI_Pct', ascending=False)
        else: display_df = display_df.sort_index(ascending=False)

        # Responsive Card Grid
        grid_cols = st.columns(2)
        for i in range(len(display_df)):
            row = display_df.iloc[i]
            with grid_cols[i % 2]:
                is_sold = row['Status'] == 'Sold'
                p_color = "#00f2ff" if row['ROI_Pct'] >= 0 else "#ff4d4d"
                
                st.markdown(f'''
                    <div class="card-container">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <span class="badge {"badge-sold" if is_sold else "badge-active"}">{"SOLD" if is_sold else "IN VAULT"}</span>
                            <span style="color:{p_color}; font-weight:800; font-size:18px;">{row['ROI_Pct']:+.1f}%</span>
                        </div>
                        <div style="font-size: 15px; font-weight: 800; color: #ffffff; margin-bottom: 12px; height: 40px; overflow: hidden;">{row['Card_Name']}</div>
                ''', unsafe_allow_html=True)
                
                img_url = row.get('Image_URL', "")
                st.image(img_url if (pd.notna(img_url) and str(img_url).startswith('http')) else "https://via.placeholder.com/400x560/11141a/1f2833?text=NO+IMAGE", use_container_width=True)
                
                st.markdown(f'''
                        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #1f2833;">
                            <div style="color: {p_color}; font-size: 26px; font-weight: 800; font-family: monospace;">${row['Live_Val']:,.2f}</div>
                            <div style="color: #8892b0; font-size: 12px; margin-top: 4px;">{row['Grade_Score']} • P/L: ${row['Net_Profit']:,.2f}</div>
                        </div>
                    </div>
                ''', unsafe_allow_html=True)

    with t_edit:
        st.subheader("🛠️ Update Asset Intelligence")
        target_card = st.selectbox("Select Asset to Modify", df['Card_Name'].tolist())
        r_data = df[df['Card_Name'] == target_card].iloc[0]
        r_idx = df[df['Card_Name'] == target_card].index[0]

        with st.form("edit_form_v9"):
            col_a, col_b = st.columns(2)
            with col_a:
                new_mkt = st.number_input("Live Market Value ($)", value=float(r_data['Market_Price']))
                new_status = st.selectbox("Lifecycle Status", ["Active", "Sold"], index=0 if r_data['Status'] != 'Sold' else 1)
                new_qty = st.number_input("Quantity", value=int(r_data['Quantity']))
            with col_b:
                new_sell = st.number_input("Final Sale Price ($)", value=float(r_data['Sell_Price']))
                new_grade = st.text_input("Grade Label", value=str(r_data['Grade_Score']))
                new_fee = st.number_input("Grading Investment ($)", value=float(r_data['Grade_Fee']))
            
            new_img = st.file_uploader("Replace Visual Proof", type=['jpg', 'png'])
            
            if st.form_submit_button("⚡ UPDATE SECURE RECORD"):
                client = get_gspread_client()
                sh = client.open_by_url(SHEET_NAME_URL).sheet1
                row_num = int(r_idx) + 2
                sh.update_cell(row_num, 8, new_mkt); sh.update_cell(row_num, 11, new_sell); sh.update_cell(row_num, 12, new_status)
                sh.update_cell(row_num, 5, new_qty); sh.update_cell(row_num, 9, new_grade); sh.update_cell(row_num, 7, new_fee)
                if new_img:
                    url = upload_to_imgbb(new_img)
                    if url: sh.update_cell(row_num, 10, url)
                st.cache_data.clear(); st.rerun()

    with t_add:
        st.subheader("✨ Deploy New Asset to Vault")
        with st.form("add_form_v9", clear_on_submit=True):
            a_name = st.text_input("Card Full Name")
            a_set = st.text_input("Set / Collection")
            c_1, c_2 = st.columns(2)
            with c_1:
                a_buy = st.number_input("Purchase Price ($)")
                a_mkt = st.number_input("Initial Market ($)")
            with c_2:
                a_qty = st.number_input("Quantity", value=1)
                a_fee = st.number_input("Grading Fee ($)")
            
            a_grd = st.text_input("Grade (PSA/BGS/CGC)")
            a_id = st.text_input("Serial / Asset ID")
            a_pic = st.file_uploader("Capture Image Proof", type=['jpg', 'png', 'jpeg'])
            
            if st.form_submit_button("🚀 INITIATE DEPLOYMENT"):
                if a_name and a_pic:
                    url = upload_to_imgbb(a_pic)
                    if url:
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        sh.append_row([a_id, "Card", a_name, a_set, int(a_qty), a_buy, a_fee, a_mkt, a_grd, url, 0, "Active"])
                        st.cache_data.clear(); st.rerun()
                else: st.warning("Identity & Image required.")
else:
    st.error("⚠️ SECURE CONNECTION FAILED. CHECK GOOGLE SHEET CONFIG.")
