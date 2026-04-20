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

# --- UI DESIGN SYSTEM v11 (ULTRA MODERN DARK) ---
st.set_page_config(page_title="PRO VAULT v11", layout="wide", page_icon="📈")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {visibility: hidden;}
    .stApp { background-color: #050505; font-family: 'Inter', sans-serif; }
    
    /* Global Text Visibility */
    p, span, label, .stMarkdown { color: #FFFFFF !important; }
    
    /* Glassmorphism Cards */
    .st-expander { background-color: #111111 !important; border: 1px solid #222 !important; border-radius: 20px !important; margin-bottom: 10px !important; }
    
    /* Metrics Box */
    [data-testid="stMetric"] {
        background: linear-gradient(145deg, #0f0f0f, #1a1a1a);
        border-radius: 20px; padding: 15px; border: 1px solid #333;
    }
    [data-testid="stMetricValue"] { color: #00f2ff !important; font-size: 28px !important; font-weight: 800 !important; }

    /* Button Styling */
    .stButton button {
        background: #00f2ff !important; color: #000 !important;
        border-radius: 12px !important; font-weight: 800 !important; height: 3.5rem !important; width: 100%; border: none;
    }
    
    /* Custom Investment Bar */
    .p-bar-bg { background: #222; height: 8px; border-radius: 10px; width: 100%; margin: 10px 0; overflow: hidden; }
    .p-bar-fill { height: 100%; border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- ENGINE ---
@st.cache_data(ttl=5)
def load_data():
    try:
        raw = pd.read_csv(SHEET_URL)
        for col in ['Quantity', 'Buy_Price', 'Grade_Fee', 'Market_Price', 'Sell_Price']:
            if col in raw.columns:
                raw[col] = pd.to_numeric(raw[col].astype(str).str.replace(',', '').str.replace('$', ''), errors='coerce').fillna(0)
        raw['gsheet_row'] = raw.index + 2
        raw['Cost_Total'] = (raw['Buy_Price'] + raw['Grade_Fee']) * raw['Quantity']
        raw['Unit_Cost'] = (raw['Buy_Price'] + raw['Grade_Fee'])
        raw['Current_Val'] = raw.apply(lambda x: x['Sell_Price'] if x['Status'] == 'Sold' else x['Market_Price'], axis=1)
        raw['Current_Total_Val'] = raw['Current_Val'] * raw['Quantity']
        raw['Profit'] = raw['Current_Total_Val'] - raw['Cost_Total']
        raw['ROI'] = (raw['Profit'] / raw['Cost_Total'].replace(0, 0.01)) * 100
        return raw
    except: return pd.DataFrame()

df = load_data()

# --- TOP DASHBOARD CONTROLS ---
c_head, c_refresh = st.columns([0.7, 0.3])
with c_head:
    st.markdown("<h1 style='margin:0;'>VAULT 11.0</h1>", unsafe_allow_html=True)
with c_refresh:
    if st.button("🔄 SYNC"):
        st.cache_data.clear()
        st.rerun()

if not df.empty:
    # Key Stats
    m1, m2, m3 = st.columns(3)
    active_df = df[df['Status'] != 'Sold']
    m1.metric("PORTFOLIO", f"${active_df['Current_Total_Val'].sum():,.0f}")
    m2.metric("TOTAL P/L", f"${df['Profit'].sum():,.0f}", delta=f"{df['Profit'].sum():+.0f}")
    m3.metric("ROI", f"{(df['Profit'].sum() / df['Cost_Total'].sum() * 100):+.1f}%")

    st.divider()

    # Search & Filter
    s1, s2 = st.columns([0.6, 0.4])
    q = s1.text_input("🔍 Search Asset...", placeholder="Name, Set, Serial")
    sort_by = s2.selectbox("Order", ["Latest", "Highest Profit", "Best ROI %"])

    view_df = df.copy()
    if q:
        view_df = view_df[view_df['Card_Name'].str.contains(q, case=False, na=False)]
    
    if sort_by == "Highest Profit": view_df = view_df.sort_values('Profit', ascending=False)
    elif sort_by == "Best ROI %": view_df = view_df.sort_values('ROI', ascending=False)
    else: view_df = view_df.sort_index(ascending=False)

    # Asset Grid
    st.markdown("### 🖼️ YOUR COLLECTION")
    for index, row in view_df.iterrows():
        # Title with ROI Badge
        roi_color = "#00ffcc" if row['ROI'] >= 0 else "#ff4d4d"
        
        # UI EXPANDER (Clickable Card)
        with st.expander(f"{row['Card_Name']} ┃ {row['ROI']:+.1f}%", expanded=False):
            d1, d2 = st.columns([0.4, 0.6])
            
            with d1:
                st.image(row['Image_URL'] if pd.notna(row['Image_URL']) else "https://via.placeholder.com/300/111", use_container_width=True)
            
            with d2:
                st.markdown(f"#### Asset Intelligence")
                st.markdown(f"**Status:** `{row['Status'].upper()}`")
                
                # Visual Profit Line
                st.markdown(f"**Value Progression**")
                p_percent = min(max((row['Current_Val'] / row['Unit_Cost'].replace(0, 0.01)) * 50, 5), 100)
                st.markdown(f'''
                    <div class="p-bar-bg">
                        <div class="p-bar-fill" style="width:{p_percent}%; background:{roi_color};"></div>
                    </div>
                ''', unsafe_allow_html=True)
                
                st.markdown(f"""
                - **Quantity:** {int(row['Quantity'])}
                - **Unit Cost:** ${row['Unit_Cost']:,.2f}
                - **Market Price:** ${row['Current_Val']:,.2f}
                - **Net Profit:** <span style="color:{roi_color}; font-weight:800;">${row['Profit']:,.2f}</span>
                """, unsafe_allow_html=True)
                
                # POP-OVER EDIT (Modern Way to Edit)
                with st.popover("⚙️ QUICK EDIT"):
                    with st.form(f"edit_{row['gsheet_row']}"):
                        u_mkt = st.number_input("Market Price ($)", value=float(row['Market_Price']))
                        u_sel = st.number_input("Sold For ($)", value=float(row['Sell_Price']))
                        u_sta = st.selectbox("Status", ["Active", "Sold"], index=0 if row['Status'] != 'Sold' else 1)
                        u_qty = st.number_input("Qty", value=int(row['Quantity']))
                        u_fee = st.number_input("Grade Fee ($)", value=float(row['Grade_Fee']))
                        u_grd = st.text_input("Grade Label", value=str(row['Grade_Score']))
                        u_img = st.file_uploader("Update Image", type=['jpg', 'png'])
                        
                        if st.form_submit_button("💾 UPDATE CLOUD"):
                            client = get_gspread_client()
                            sh = client.open_by_url(SHEET_NAME_URL).sheet1
                            r = int(row['gsheet_row'])
                            sh.update_cell(r, 8, u_mkt); sh.update_cell(r, 11, u_sel); sh.update_cell(r, 12, u_sta)
                            sh.update_cell(r, 5, u_qty); sh.update_cell(r, 9, u_grd); sh.update_cell(r, 7, u_fee)
                            if u_img:
                                url = upload_to_imgbb(u_img)
                                if url: sh.update_cell(r, 10, url)
                            st.cache_data.clear(); st.rerun()

    # ADD NEW SECTION (Always at bottom for iPhone)
    st.divider()
    with st.expander("➕ REGISTER NEW ASSET", expanded=False):
        with st.form("add_new_v11", clear_on_submit=True):
            a_name = st.text_input("Card Name")
            a_set = st.text_input("Set Name")
            c1, c2 = st.columns(2)
            with c1:
                a_buy = st.number_input("Buy ($)")
                a_mkt = st.number_input("Market ($)")
            with c2:
                a_qty = st.number_input("Qty", value=1)
                a_fee = st.number_input("Fee ($)")
            
            a_grd = st.text_input("Grade")
            a_id = st.text_input("Serial ID")
            a_file = st.file_uploader("Capture Photo", type=['jpg', 'png', 'jpeg'])
            
            if st.form_submit_button("🚀 DEPLOY TO VAULT"):
                if a_name and a_file:
                    url = upload_to_imgbb(a_file)
                    if url:
                        client = get_gspread_client()
                        sh = client.open_by_url(SHEET_NAME_URL).sheet1
                        sh.append_row([a_id, "Card", a_name, a_set, int(a_qty), a_buy, a_fee, a_mkt, a_grd, url, 0, "Active"])
                        st.cache_data.clear(); st.rerun()
else:
    st.warning("PLEASE CHECK DATA CONNECTION.")
