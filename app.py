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

# --- UI PREMIUM THEME ---
st.set_page_config(page_title="PRO VAULT | BOSS TANG", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    /* Global Styles */
    .stApp { background-color: #0b0c10; color: #E0E0E0; }
    h1, h2, h3 { color: #00f2ff !important; font-family: 'Inter', sans-serif; }
    
    /* Metrics Area */
    [data-testid="stMetric"] {
        background: rgba(31, 40, 51, 0.4);
        padding: 15px;
        border-radius: 15px;
        border: 1px solid #1f2833;
    }
    [data-testid="stMetricValue"] { color: #00f2ff !important; font-size: 32px !important; font-family: monospace; }

    /* Enhanced Card Design */
    .card-frame { 
        border: 1px solid #1f2833; padding: 18px; border-radius: 22px; 
        background: linear-gradient(145deg, #161b22, #0d1117);
        box-shadow: 0 10px 30px rgba(0,0,0,0.6);
        text-align: center; margin-bottom: 25px;
        position: relative;
        overflow: hidden;
    }
    
    /* ROI Glow Effect */
    .roi-positive { border-bottom: 3px solid #00ff88; }
    .roi-negative { border-bottom: 3px solid #ff4444; }

    .status-badge { font-size: 10px; font-weight: bold; padding: 4px 12px; border-radius: 50px; text-transform: uppercase; }
    .active-badge { background: rgba(0, 255, 136, 0.1); color: #00ff88 !important; border: 1px solid #00ff88; }
    .sold-badge { background: rgba(255, 68, 68, 0.1); color: #ff4444 !important; border: 1px solid #ff4444; }
    
    /* Buttons */
    .stButton button { 
        border-radius: 14px; background: linear-gradient(90deg, #45a29e, #66fcf1); 
        color: #0b0c10 !important; font-weight: 800; border: none; height: 3.8em;
        transition: all 0.3s ease;
    }
    .stButton button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(102, 252, 241, 0.4); }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] { gap: 15px; }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent; border-radius: 12px; padding: 12px 25px; color: #888 !important;
        border: 1px solid #1f2833;
    }
    .stTabs [aria-selected="true"] { background-color: #45a29e !important; color: #0b0c10 !important; border: none !important; }
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
header_col1, header_col2 = st.columns([0.7, 0.3])
with header_col1:
    st.title("📈 MASTER VAULT v8.0")
    st.caption("ELITE ASSET TRACKING SYSTEM")
with header_col2:
    privacy_mode = st.toggle("🔒 Privacy", value=False)
    if st.button("🔄 REFRESH SYSTEM"):
        st.cache_data.clear()
        st.rerun()

if not df.empty:
    def f_v(v): return "********" if privacy_mode else f"${v:,.2f}"
    
    # Global Metrics
    m1, m2, m3 = st.columns(3)
    active_m = df['Status'] != 'Sold'
    total_cost = (df[active_m]['Unit_Cost'] * df[active_m]['Quantity']).sum()
    total_p_l = df['Total_Profit'].sum()
    
    m1.metric("VAULT VALUE", f_v(total_cost))
    m2.metric("PROFIT/LOSS", f_v(total_p_l), delta=None if privacy_mode else f"{total_p_l:+.2f}")
    m3.metric("AVG ROI", f"{(total_p_l / (df['Unit_Cost'] * df['Quantity']).sum() * 100):+.1f}%")

    st.divider()

    t_port, t_mgmt, t_add = st.tabs(["🖼️ PORTFOLIO", "⚙️ CONTROL", "➕ REGISTER"])

    with t_port:
        f1, f2, f3 = st.columns([0.4, 0.3, 0.3])
        query = f1.text_input("🔍 Search", placeholder="Card or Set Name...")
        s_filter = f2.selectbox("Filter Status", ["All", "Active", "Sold"])
        o_filter = f3.selectbox("Sort by", ["Newest", "Value (High)", "ROI % (High)"])

        # Process View
        view_df = df.copy()
        if query:
            view_df = view_df[view_df['Card_Name'].str.contains(query, case=False, na=False) | 
                             view_df['Set_Name'].str.contains(query, case=False, na=False)]
        if s_filter == "Active": view_df = view_df[view_df['Status'] != 'Sold']
        elif s_filter == "Sold": view_df = view_df[view_df['Status'] == 'Sold']

        if o_filter == "Value (High)": view_df = view_df.sort_values('Current_Value', ascending=False)
        elif o_filter == "ROI % (High)": view_df = view_df.sort_values('ROI', ascending=False)
        else: view_df = view_df.sort_index(ascending=False)

        # Render Grid
        cols = st.columns(2)
        for i in range(len(view_df)):
            row = view_df.iloc[i]
            with cols[i % 2]:
                is_sold = row['Status'] == 'Sold'
                p_color = "#00ff88" if row['ROI'] >= 0 else "#ff4444"
                roi_class = "roi-positive" if row['ROI'] >= 0 else "roi-negative"
                
                st.markdown(f'''
                    <div class="card-frame {roi_class}">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px;">
                            <span class="status-badge {"sold-badge" if is_sold else "active-badge"}">{"SOLD" if is_sold else "ACTIVE"}</span>
                            <span style="color:{p_color}; font-weight:900; font-family:monospace; font-size:16px;">{row['ROI']:+.1f}%</span>
                        </div>
                        <div style="font-weight:700; font-size:15px; color:#ffffff; height:38px; line-height:1.2; overflow:hidden; margin-bottom:10px;">{row['Card_Name']}</div>
                ''', unsafe_allow_html=True)
                
                img = row.get('Image_URL', "")
                st.image(img if (pd.notna(img) and str(img).startswith('http')) else "https://via.placeholder.com/300/111/45a29e?text=NO+IMAGE", use_container_width=True)
                
                st.markdown(f"""
                        <div style="margin-top:15px; padding-top:10px; border-top: 1px solid #1f2833;">
                            <div style="color:{p_color}; font-size:24px; font-weight:800; font-family:monospace;">{f_v(row['Current_Value'])}</div>
                            <div style="color:#888; font-size:11px; margin-top:5px; font-weight:bold;">{row['Grade_Score']} | P/L: {f_v(row['Total_Profit'])}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    with t_mgmt:
        target = st.selectbox("🎯 Select Card", df['Card_Name'].tolist())
        r_idx = df[df['Card_Name'] == target].index[0]
        
        st.success(f"💎 Break-even Intel: **{f_v(df.at[r_idx, 'Unit_Cost'])}**")
        
        with st.form("elite_edit_v8"):
            e1, e2 = st.columns(2)
            with e1:
                u_mkt = st.number_input("Market Price ($)", value=float(df.at[r_idx, 'Market_Price']))
                u_sel = st.number_input("Final Sale ($)", value=float(df.at[r_idx, 'Sell_Price']))
                u_sta = st.selectbox("Asset Status", ["Active", "Sold"], index=0 if df.at[r_idx, 'Status'] != 'Sold' else 1)
            with e2:
                u_qty = st.number_input("Qty", value=int(df.at[r_idx, 'Quantity']))
                u_grd = st.text_input("Grade", value=str(df.at[r_idx, 'Grade_Score']))
                u_fee = st.number_input("Grading Fee ($)", value=float(df.at[r_idx, 'Grade_Fee']))
            
            u_pic = st.file_uploader("Update Visual Asset", type=['jpg', 'png'])
            if st.form_submit_button("💾 UPDATE CLOUD RECORD"):
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
        with st.form("elite_add_v8", clear_on_submit=True):
            st.markdown("### ➕ Add New Investment")
            a_name = st.text_input("Name")
            a_cat = st.selectbox("Category", ["One Piece", "Pokemon", "F1", "Others"])
            a_set = st.text_input("Set")
            a1, a2 = st.columns(2)
            with a1:
                a_buy = st.number_input("Buy ($)")
                a_qty = st.number_input("Quantity", value=1)
            with a2:
                a_fee = st.number_input("Grade Fee ($)")
                a_mkt = st.number_input("Market ($)")
            
            a_grd = st.text_input("Grade Score")
            a_id = st.text_input("Asset ID")
            a_file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])
            
            if st.form_submit_button("🚀 DEPLOY TO VAULT"):
                if a_name and a_file:
                    url = upload_to_imgbb(a_file)
                    if url:
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        sh.append_row([a_id, a_cat, a_name, a_set, int(a_qty), a_buy, a_fee, a_mkt, a_grd, url, 0, "Active"])
                        st.cache_data.clear(); st.rerun()
                else: st.warning("Name and Photo are required.")
else:
    st.info("System Ready. Waiting for Data...")
