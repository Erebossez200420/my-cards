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

# --- UI DESIGN SYSTEM ---
st.set_page_config(page_title="VAULT PRO v13.1", layout="wide", page_icon="💎")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800&display=swap');
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #0d1117; font-family: 'Inter', sans-serif; color: #ffffff; }
    h1, h2, h3 { color: #ffffff !important; }
    p, span, label, div { color: #f0f6fc !important; }
    
    /* Better Input Visibility */
    .stTextInput input, .stSelectbox div[data-baseweb="select"], .stNumberInput input {
        background-color: #161b22 !important; color: #ffffff !important; 
        border: 1px solid #30363d !important; border-radius: 10px !important;
    }
    
    /* Professional Metrics */
    [data-testid="stMetric"] { background: #161b22; border: 1px solid #30363d; border-radius: 16px; padding: 20px; }
    [data-testid="stMetricValue"] { color: #58a6ff !important; font-weight: 800 !important; }

    /* Expanders & Popovers */
    .st-expander { background-color: #0d1117 !important; border: 1px solid #30363d !important; border-radius: 12px !important; }
    
    /* Buttons */
    .stButton button { border-radius: 10px !important; font-weight: 700 !important; height: 3.5rem; width: 100%; border: none !important; }
    .btn-sync button { background: #238636 !important; color: white !important; }
    .btn-update button { background: #1f6feb !important; color: white !important; }
    .btn-delete button { background: #da3633 !important; color: white !important; }
    
    .p-bar-bg { background: #30363d; height: 10px; border-radius: 5px; width: 100%; margin: 12px 0; }
    .p-bar-fill { height: 100%; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

# --- DATA ENGINE (PRECISION CLEANING) ---
@st.cache_data(ttl=5)
def load_data():
    try:
        raw = pd.read_csv(SHEET_URL)
        raw['gsheet_row'] = raw.index + 2
        
        # Clean numeric columns strictly
        num_cols = ['Quantity', 'Buy_Price', 'Grade_Fee', 'Market_Price', 'Sell_Price']
        for col in num_cols:
            if col in raw.columns:
                raw[col] = (raw[col].astype(str)
                           .str.replace(r'[$, ]', '', regex=True)
                           .replace('', '0'))
                raw[col] = pd.to_numeric(raw[col], errors='coerce').fillna(0)
        
        # Logic: If Sold use Sell_Price, else use Market_Price
        raw['Unit_Cost'] = raw['Buy_Price'] + raw['Grade_Fee']
        raw['Total_Cost'] = raw['Unit_Cost'] * raw['Quantity']
        raw['Current_Price'] = raw.apply(lambda x: x['Sell_Price'] if str(x['Status']).strip().lower() == 'sold' else x['Market_Price'], axis=1)
        raw['Total_Value'] = raw['Current_Price'] * raw['Quantity']
        raw['Net_Profit'] = raw['Total_Value'] - raw['Total_Cost']
        raw['ROI_Pct'] = (raw['Net_Profit'] / raw['Total_Cost'].replace(0, 0.01)) * 100
        return raw
    except Exception as e:
        st.error(f"Error loading data: {e}")
        return pd.DataFrame()

df = load_data()

# --- TOP NAV ---
c1, c2 = st.columns([0.7, 0.3])
with c1:
    st.markdown("<h1 style='margin:0;'>VAULT 13.1</h1>", unsafe_allow_html=True)
with c2:
    st.markdown('<div class="btn-sync">', unsafe_allow_html=True)
    if st.button("🔄 REFRESH"):
        st.cache_data.clear(); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

if not df.empty:
    # Portfolio Snapshot
    m1, m2, m3 = st.columns(3)
    active_mask = df['Status'].astype(str).str.strip().lower() != 'sold'
    m1.metric("HOLDING VALUE", f"${df[active_mask]['Total_Value'].sum():,.2f}")
    m2.metric("NET P/L", f"${df['Net_Profit'].sum():,.2f}", delta=f"{df['Net_Profit'].sum():+.2f}")
    m3.metric("ROI (%)", f"{(df['Net_Profit'].sum() / df['Total_Cost'].sum() * 100 if df['Total_Cost'].sum() > 0 else 0):+.1f}%")

    st.divider()

    # Search & View Control
    sc1, sc2 = st.columns([0.6, 0.4])
    q = sc1.text_input("🔍 Search", placeholder="Card name...")
    sort_by = sc2.selectbox("Sort", ["Latest", "Profit ($)", "ROI %"])

    view_df = df.copy()
    if q: view_df = view_df[view_df['Card_Name'].astype(str).str.contains(q, case=False, na=False)]
    if sort_by == "Profit ($)": view_df = view_df.sort_values('Net_Profit', ascending=False)
    elif sort_by == "ROI %": view_df = view_df.sort_values('ROI_Pct', ascending=False)
    else: view_df = view_df.sort_index(ascending=False)

    # Collection List
    for idx, row in view_df.iterrows():
        p_color = "#3fb950" if row['Net_Profit'] >= 0 else "#f85149"
        
        with st.expander(f"{row['Card_Name']} ┃ ${row['Current_Price']:,.0f}", expanded=False):
            l_col, r_col = st.columns([0.4, 0.6])
            with l_col:
                st.image(row['Image_URL'] if pd.notna(row['Image_URL']) else "https://via.placeholder.com/300/161b22/30363d", use_container_width=True)
            with r_col:
                # Progress Bar
                safe_cost = max(row['Unit_Cost'], 0.01)
                meter = min(max((row['Current_Price'] / safe_cost) * 50, 5), 100)
                st.markdown(f'''
                    <div style="font-size:12px; color:#8b949e; margin-bottom:5px;">VALUATION STATUS</div>
                    <div class="p-bar-bg"><div class="p-bar-fill" style="width:{meter}%; background:{p_color}; box-shadow: 0 0 8px {p_color}66;"></div></div>
                    <p style="margin: 10px 0;">Live Value: <b>${row['Current_Price']:,.2f}</b> | P/L: <span style="color:{p_color}; font-weight:800;">${row['Net_Profit']:,.2f}</span></p>
                ''', unsafe_allow_html=True)
                
                # Management Popover
                with st.popover("⚙️ ACTIONS"):
                    with st.form(f"f_{row['gsheet_row']}"):
                        st.markdown("#### 🛠️ Edit Information")
                        u_mkt = st.number_input("Market Price", value=float(row['Market_Price']))
                        u_sel = st.number_input("Sold Price", value=float(row['Sell_Price']))
                        u_sta = st.selectbox("Status", ["Active", "Sold"], index=0 if str(row['Status']).lower() != 'sold' else 1)
                        u_qty = st.number_input("Qty", value=int(row['Quantity']))
                        u_fee = st.number_input("Grade Fee", value=float(row['Grade_Fee']))
                        u_grd = st.text_input("Grade", value=str(row['Grade_Score']))
                        u_img = st.file_uploader("Change Image", type=['jpg', 'png'])
                        
                        st.markdown('<div class="btn-update">', unsafe_allow_html=True)
                        if st.form_submit_button("SAVE DATA"):
                            client = get_gspread_client()
                            sh = client.open_by_url(SHEET_NAME_URL).sheet1
                            r = int(row['gsheet_row'])
                            sh.update_cell(r, 8, u_mkt); sh.update_cell(r, 11, u_sel); sh.update_cell(r, 12, u_sta)
                            sh.update_cell(r, 5, u_qty); sh.update_cell(r, 9, u_grd); sh.update_cell(r, 7, u_fee)
                            if u_img:
                                url = upload_to_imgbb(u_img)
                                if url: sh.update_cell(r, 10, url)
                            st.cache_data.clear(); st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    st.divider()
                    st.markdown("#### 🗑️ Remove Asset")
                    confirm = st.checkbox(f"Permanently remove {row['Card_Name']}?", key=f"del_c_{row['gsheet_row']}")
                    st.markdown('<div class="btn-delete">', unsafe_allow_html=True)
                    if st.button("DELETE NOW", key=f"del_b_{row['gsheet_row']}", disabled=not confirm):
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        r = int(row['gsheet_row'])
                        if r > 1:
                            sh.delete_rows(r)
                            st.cache_data.clear(); st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

    # ADD NEW
    st.divider()
    with st.expander("➕ ADD NEW ASSET", expanded=False):
        with st.form("add_v13_1", clear_on_submit=True):
            a_name = st.text_input("Card Name")
            a_set = st.text_input("Set Name")
            a_buy = st.number_input("Purchase Price ($)")
            a_mkt = st.number_input("Market Price ($)")
            a_qty = st.number_input("Quantity", value=1)
            a_fee = st.number_input("Grading Fee ($)")
            a_grd = st.text_input("Grade")
            a_id = st.text_input("Serial ID")
            a_file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])
            
            if st.form_submit_button("DEPLOY TO VAULT"):
                if a_name and a_file:
                    url = upload_to_imgbb(a_file)
                    if url:
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        sh.append_row([a_id, "Card", a_name, a_set, int(a_qty), a_buy, a_fee, a_mkt, a_grd, url, 0, "Active"])
                        st.cache_data.clear(); st.rerun()
else:
    st.warning("No data found or connection lost.")
