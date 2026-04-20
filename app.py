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

# --- UI IPHONE OPTIMIZED & HIGH CONTRAST ---
st.set_page_config(page_title="PRO VAULT", layout="wide", page_icon="📟")

st.markdown("""
    <style>
    /* Force high contrast for iPhone */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    .stApp { background-color: #000000; color: #FFFFFF; }
    
    /* Text Brightness */
    h1, h2, h3 { color: #00ffff !important; font-weight: 800; text-shadow: 0px 0px 5px rgba(0,255,255,0.2); }
    p, span, label, .stMarkdown { color: #FFFFFF !important; font-weight: 600 !important; }
    
    /* Metric Cards - High Visibility */
    [data-testid="stMetric"] {
        background: #1a1a1a;
        padding: 20px;
        border-radius: 15px;
        border: 2px solid #333333;
        margin-bottom: 10px;
    }
    [data-testid="stMetricValue"] { color: #00ffff !important; font-size: 35px !important; }
    [data-testid="stMetricLabel"] { color: #aaaaaa !important; font-size: 14px !important; }

    /* Asset Card Design */
    .card-frame { 
        border: 2px solid #333333; padding: 15px; border-radius: 20px; 
        background: #121212;
        text-align: center; margin-bottom: 20px;
    }
    
    .status-badge { font-size: 11px; font-weight: 900; padding: 5px 12px; border-radius: 8px; }
    .active-badge { background: #00ff88; color: #000000 !important; }
    .sold-badge { background: #ff4444; color: #ffffff !important; }
    
    /* iPhone Friendly Buttons & Inputs */
    .stButton button { 
        border-radius: 15px; background: #00ffff; color: #000000 !important; 
        font-weight: 900; height: 4em; width: 100%; border: none;
        font-size: 18px !important;
    }
    
    /* Forms & Selectboxes for Thumbs */
    input, select, textarea, .stSelectbox div {
        background-color: #1a1a1a !important; color: #ffffff !important; 
        border: 1px solid #444 !important; height: 3em !important;
    }

    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1a1a; border-radius: 12px; padding: 15px; 
        color: #FFFFFF !important; border: 1px solid #333;
    }
    .stTabs [aria-selected="true"] { 
        background-color: #00ffff !important; color: #000000 !important; font-weight: bold !important;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 1. DATA LOADING ---
@st.cache_data(ttl=5)
def load_data():
    try:
        raw_df = pd.read_csv(SHEET_URL)
        for col in ['Quantity', 'Buy_Price', 'Grade_Fee', 'Market_Price', 'Sell_Price']:
            if col in raw_df.columns:
                raw_df[col] = pd.to_numeric(raw_df[col].astype(str).str.replace(',', '').str.replace('$', ''), errors='coerce').fillna(0)
        
        raw_df['Unit_Cost'] = raw_df['Buy_Price'] + raw_df['Grade_Fee']
        raw_df['Current_Value'] = raw_df.apply(lambda x: x['Sell_Price'] if x['Status'] == 'Sold' else x['Market_Price'], axis=1)
        raw_df['Total_Profit'] = (raw_df['Current_Value'] - raw_df['Unit_Cost']) * raw_df['Quantity']
        
        cost_for_roi = (raw_df['Unit_Cost'] * raw_df['Quantity']).replace(0, 0.01)
        raw_df['ROI'] = (raw_df['Total_Profit'] / cost_for_roi) * 100
        return raw_df
    except: return pd.DataFrame()

df = load_data()

# --- HEADER ---
h1, h2 = st.columns([0.6, 0.4])
with h1:
    st.title("📟 VAULT 8.1")
with h2:
    if st.button("🔄 REFRESH"):
        st.cache_data.clear()
        st.rerun()
    privacy_mode = st.toggle("🔒 Privacy", value=False)

if not df.empty:
    def f_v(v): return "********" if privacy_mode else f"${v:,.2f}"
    
    # Global Metrics (Vertical on Mobile)
    m1, m2, m3 = st.columns(3)
    active_m = df['Status'] != 'Sold'
    m1.metric("VAULT NET", f_v((df[active_m]['Unit_Cost'] * df[active_m]['Quantity']).sum()))
    m2.metric("P/L", f_v(df['Total_Profit'].sum()))
    m3.metric("ROI", f"{(df['Total_Profit'].sum() / (df['Unit_Cost'] * df['Quantity']).sum() * 100):+.1f}%")

    st.divider()

    t_port, t_mgmt, t_add = st.tabs(["🖼️ ASSETS", "⚙️ EDIT", "➕ ADD"])

    with t_port:
        q = st.text_input("🔍 Search Card Name...", placeholder="Type here...")
        c1, c2 = st.columns(2)
        s_filter = c1.selectbox("Status", ["All", "Active", "Sold"])
        o_filter = c2.selectbox("Order", ["Latest", "Value", "ROI"])

        # Filter Logic
        view_df = df.copy()
        if q:
            view_df = view_df[view_df['Card_Name'].str.contains(q, case=False, na=False)]
        if s_filter == "Active": view_df = view_df[view_df['Status'] != 'Sold']
        elif s_filter == "Sold": view_df = view_df[view_df['Status'] == 'Sold']

        if o_filter == "Value": view_df = view_df.sort_values('Current_Value', ascending=False)
        elif o_filter == "ROI": view_df = view_df.sort_values('ROI', ascending=False)
        else: view_df = view_df.sort_index(ascending=False)

        # Render Grid (Optimized for iPhone Scrolling)
        cols = st.columns(2)
        for i in range(len(view_df)):
            row = view_df.iloc[i]
            with cols[i % 2]:
                is_sold = row['Status'] == 'Sold'
                p_color = "#00ff88" if row['ROI'] >= 0 else "#ff4444"
                
                st.markdown(f'''
                    <div class="card-frame">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 10px;">
                            <span class="status-badge {"sold-badge" if is_sold else "active-badge"}">{"SOLD" if is_sold else "ACTIVE"}</span>
                            <span style="color:{p_color}; font-weight:900;">{row['ROI']:+.1f}%</span>
                        </div>
                        <div style="color:#FFFFFF; font-size:14px; font-weight:bold; height:35px; overflow:hidden; margin-bottom:5px;">{row['Card_Name']}</div>
                ''', unsafe_allow_html=True)
                
                img = row.get('Image_URL', "")
                st.image(img if (pd.notna(img) and str(img).startswith('http')) else "https://via.placeholder.com/300/222/00ffff?text=NO+IMAGE", use_container_width=True)
                
                st.markdown(f"""
                        <div style="margin-top:10px;">
                            <div style="color:{p_color}; font-size:22px; font-weight:900; font-family:monospace;">{f_v(row['Current_Value'])}</div>
                            <div style="color:#FFFFFF; font-size:11px; margin-top:2px;">{row['Grade_Score']} | P/L: {f_v(row['Total_Profit'])}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    with t_mgmt:
        target = st.selectbox("🎯 Target Asset", df['Card_Name'].tolist())
        r_idx = df[df['Card_Name'] == target].index[0]
        
        st.info(f"💎 Break-even: {f_v(df.at[r_idx, 'Unit_Cost'])}")
        
        with st.form("iphone_edit"):
            u_mkt = st.number_input("Market Price ($)", value=float(df.at[r_idx, 'Market_Price']))
            u_sel = st.number_input("Sell Price ($)", value=float(df.at[r_idx, 'Sell_Price']))
            u_sta = st.selectbox("Status", ["Active", "Sold"], index=0 if df.at[r_idx, 'Status'] != 'Sold' else 1)
            u_qty = st.number_input("Qty", value=int(df.at[r_idx, 'Quantity']))
            u_grd = st.text_input("Grade", value=str(df.at[r_idx, 'Grade_Score']))
            u_fee = st.number_input("Fee ($)", value=float(df.at[r_idx, 'Grade_Fee']))
            u_pic = st.file_uploader("Update Photo", type=['jpg', 'png'])
            
            if st.form_submit_button("💾 SYNC DATA"):
                client = get_gspread_client()
                sh = client.open_by_url(SHEET_NAME_URL).sheet1
                r = int(r_idx) + 2
                sh.update_cell(r, 8, u_mkt); sh.update_cell(r, 11, u_sel); sh.update_cell(r, 12, u_sta)
                sh.update_cell(r, 5, u_qty); sh.update_cell(r, 9, u_grd); sh.update_cell(r, 7, u_fee)
                if u_pic:
                    url = upload_to_imgbb(u_pic)
                    if url: sh.update_cell(r, 10, url)
                st.cache_data.clear(); st.rerun()

    with t_add:
        with st.form("iphone_add", clear_on_submit=True):
            st.subheader("➕ New Entry")
            a_name = st.text_input("Card Name")
            a_cat = st.selectbox("Type", ["One Piece", "Pokemon", "F1", "Others"])
            a_set = st.text_input("Set Name")
            a_buy = st.number_input("Buy Price ($)")
            a_fee = st.number_input("Grade Fee ($)")
            a_mkt = st.number_input("Market Price ($)")
            a_qty = st.number_input("Quantity", value=1)
            a_grd = st.text_input("Grade Score")
            a_id = st.text_input("Asset ID")
            a_file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])
            
            if st.form_submit_button("🚀 DEPLOY ASSET"):
                if a_name and a_file:
                    url = upload_to_imgbb(a_file)
                    if url:
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        sh.append_row([a_id, a_cat, a_name, a_set, int(a_qty), a_buy, a_fee, a_mkt, a_grd, url, 0, "Active"])
                        st.cache_data.clear(); st.rerun()
                else: st.warning("Required: Name & Photo")
else:
    st.info("No data connected.")
