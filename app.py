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

# --- UI STEALTH THEME SETTINGS ---
st.set_page_config(page_title="BOSS TANG | VAULT", layout="wide", page_icon="📟")

st.markdown("""
    <style>
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    
    /* Main Background */
    .stApp { background-color: #0b0c10; color: #E0E0E0; font-family: 'Inter', sans-serif; }
    
    /* Global Text Visibility */
    p, span, label { color: #E0E0E0 !important; }
    h1, h2, h3 { color: #00f2ff !important; font-weight: 800; }
    
    /* Metric Enhancement */
    [data-testid="stMetricValue"] { color: #00f2ff !important; font-size: 28px !important; }
    [data-testid="stMetricLabel"] { color: #888888 !important; }

    /* Card Frame with Elevation */
    .card-frame { 
        border: 1px solid #1f2833; padding: 15px; border-radius: 18px; 
        background: linear-gradient(145deg, #11141a, #0b0c10);
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
        text-align: center; margin-bottom: 20px; 
        transition: transform 0.2s ease;
    }
    .card-frame:active { transform: scale(0.98); }

    /* Badges Style */
    .status-badge { font-size: 9px; font-weight: 900; padding: 3px 10px; border-radius: 20px; letter-spacing: 1px; }
    .active-badge { background-color: #00ff8822; color: #00ff88 !important; border: 1px solid #00ff88; }
    .sold-badge { background-color: #ff444422; color: #ff4444 !important; border: 1px solid #ff4444; }
    
    /* Input & Form Enhancement */
    .stTextInput input, .stNumberInput input, .stSelectbox div {
        background-color: #1f2833 !important; color: #ffffff !important; border: 1px solid #45a29e !important;
    }
    
    /* Mobile Thumb-Friendly Buttons */
    .stButton button { 
        border-radius: 12px; background: #45a29e; color: #0b0c10 !important; 
        font-weight: bold; border: none; width: 100%; height: 3.5em;
        box-shadow: 0 4px 10px rgba(69, 162, 158, 0.3);
    }
    .stButton button:hover { background: #66fcf1; color: #0b0c10 !important; }
    
    /* Tab Styling */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1f2833; border-radius: 10px 10px 0 0; padding: 10px 20px; color: #888 !important;
    }
    .stTabs [aria-selected="true"] { background-color: #45a29e !important; color: #0b0c10 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA LOADING ---
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

# --- APP HEADER ---
c_h1, c_h2 = st.columns([0.7, 0.3])
with c_h1:
    st.title("📟 ELITE VAULT")
    st.caption("SECURE PORTFOLIO TERMINAL")
with c_h2:
    privacy_mode = st.toggle("🔒 Privacy", value=False)
    if st.button("🔄 REFRESH"):
        st.cache_data.clear()
        st.rerun()

if not df.empty:
    def f_v(v): return "********" if privacy_mode else f"${v:,.2f}"
    
    # Hero Metrics
    m1, m2, m3 = st.columns(3)
    active_m = df['Status'] != 'Sold'
    m1.metric("VAULT NET", f_v((df[active_m]['Unit_Cost'] * df[active_m]['Quantity']).sum()))
    m2.metric("PROFIT/LOSS", f_v(df['Total_Profit'].sum()), delta=f"{df['Total_Profit'].sum():+.2f}" if not privacy_mode else None)
    m3.metric("PORTFOLIO ROI", f"{(df['Total_Profit'].sum() / (df['Unit_Cost'] * df['Quantity']).sum() * 100):+.1f}%")

    st.divider()

    t_port, t_mgmt, t_add = st.tabs(["🖼️ PORTFOLIO", "⚙️ ASSET CONTROL", "➕ NEW ENTRY"])

    with t_port:
        # Search & Filter
        f1, f2, f3 = st.columns([0.4, 0.3, 0.3])
        query = f1.text_input("🔍 Search Asset...", placeholder="Name or Set...")
        s_filter = f2.selectbox("Vault Status", ["All", "Active", "Sold"])
        o_filter = f3.selectbox("Order By", ["Latest", "Value", "ROI %"])

        view_df = df.copy()
        if query:
            view_df = view_df[view_df['Card_Name'].str.contains(query, case=False, na=False) | 
                             view_df['Set_Name'].str.contains(query, case=False, na=False)]
        if s_filter == "Active": view_df = view_df[view_df['Status'] != 'Sold']
        elif s_filter == "Sold": view_df = view_df[view_df['Status'] == 'Sold']

        if o_filter == "Value": view_df = view_df.sort_values('Current_Value', ascending=False)
        elif o_filter == "ROI %": view_df = view_df.sort_values('ROI', ascending=False)
        else: view_df = view_df.index.to_series().sort_values(ascending=False).map(view_df.loc)

        # Card Grid
        cols = st.columns(2)
        for i, (idx, row) in enumerate(view_df.iterrows()):
            with cols[i % 2]:
                is_sold = row['Status'] == 'Sold'
                p_color = "#00ff88" if row['ROI'] >= 0 else "#ff4444"
                
                st.markdown(f'''
                    <div class="card-frame">
                        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
                            <span class="status-badge {"sold-badge" if is_sold else "active-badge"}">{"SOLD" if is_sold else "IN VAULT"}</span>
                            <span style="color:{p_color}; font-weight:bold;">{row['ROI']:+.1f}%</span>
                        </div>
                        <div style="font-weight:700; font-size:16px; margin-bottom:10px; color:#ffffff;">{row['Card_Name']}</div>
                ''', unsafe_allow_html=True)
                
                img = row.get('Image_URL', "")
                st.image(img if (pd.notna(img) and str(img).startswith('http')) else "https://via.placeholder.com/300/111/45a29e?text=NO+IMAGE", use_container_width=True)
                
                st.markdown(f"""
                    <div style="margin-top:12px;">
                        <div style="color:{p_color}; font-size:24px; font-weight:800; font-family:'Courier New';">{f_v(row['Current_Value'])}</div>
                        <div style="color:#888; font-size:11px; margin-top:4px;">{row['Set_Name']} | {row['Grade_Score']}</div>
                        <div style="color:#45a29e; font-size:10px; font-weight:bold; margin-top:2px;">P/L: {f_v(row['Total_Profit'])}</div>
                    </div>
                    </div>
                """, unsafe_allow_html=True)

    with t_mgmt:
        target = st.selectbox("🎯 Select Target Asset", df['Card_Name'].tolist())
        r_idx = df[df['Card_Name'] == target].index[0]
        
        st.success(f"💎 **Investment Intel:** Current Break-even is **{f_v(df.at[r_idx, 'Unit_Cost'])}**")
        
        with st.form("elite_edit"):
            e1, e2 = st.columns(2)
            with e1:
                u_mkt = st.number_input("Market Value ($)", value=float(df.at[r_idx, 'Market_Price']))
                u_sel = st.number_input("Final Sale ($)", value=float(df.at[r_idx, 'Sell_Price']))
                u_sta = st.selectbox("Asset Status", ["Active", "Sold"], index=0 if df.at[r_idx, 'Status'] != 'Sold' else 1)
            with e2:
                u_qty = st.number_input("Qty", value=int(df.at[r_idx, 'Quantity']))
                u_grd = st.text_input("Grade", value=str(df.at[r_idx, 'Grade_Score']))
                u_fee = st.number_input("Grading Fee ($)", value=float(df.at[r_idx, 'Grade_Fee']))
            
            u_pic = st.file_uploader("Update Visual Asset", type=['jpg', 'png'])
            if st.form_submit_button("💾 UPDATE VAULT RECORD"):
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
        with st.form("elite_add", clear_on_submit=True):
            st.markdown("### ➕ Register New Asset")
            a_name = st.text_input("Asset Name")
            a_cat = st.selectbox("Category", ["One Piece", "Pokemon", "F1", "Others"])
            a_set = st.text_input("Set / Collection")
            
            a1, a2 = st.columns(2)
            with a1:
                a_buy = st.number_input("Buy Price ($)")
                a_qty = st.number_input("Quantity", value=1)
            with a2:
                a_fee = st.number_input("Grade Fee ($)")
                a_mkt = st.number_input("Market Value ($)")
            
            a_grd = st.text_input("Grade (PSA/BGS/RAW)")
            a_id = st.text_input("Asset ID / Serial")
            a_file = st.file_uploader("Capture/Upload Image", type=['jpg', 'png', 'jpeg'])
            
            if st.form_submit_button("🚀 DEPLOY TO VAULT"):
                if a_name and a_file:
                    url = upload_to_imgbb(a_file)
                    if url:
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        sh.append_row([a_id, a_cat, a_name, a_set, int(a_qty), a_buy, a_fee, a_mkt, a_grd, url, 0, "Active"])
                        st.cache_data.clear(); st.rerun()
                else: st.warning("Visual Data and Name are required.")
else:
    st.info("System Offline. Check Cloud Connection.")
