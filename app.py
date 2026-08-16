import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# 頁面基本設定
st.set_page_config(page_title="個人資產管理 APP", layout="wide")

# -----------------------------------------------------------------------------
# 初始化 Session State
# -----------------------------------------------------------------------------
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=[
        "股票代碼", "股票名稱", "買入日期", "成本價", "股數", "當日收盤價", "市值", "未實現損益", "報酬率(%)", "預估年股息"
    ])
if 'loans' not in st.session_state:
    st.session_state.loans = pd.DataFrame(columns=[
        "類型", "金融機構", "借款金額", "年利率(%)", "每月利息", "質押股票", "維持率(%)"
    ])
if 'cash' not in st.session_state:
    st.session_state.cash = 500000.0
if 'income' not in st.session_state:
    st.session_state.income = 60000.0

# -----------------------------------------------------------------------------
# 核心網路功能：穩定的抓取機制
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600)
def fetch_tw_stock(symbol):
    """
    使用 history 方法抓取價格，比 info 更穩定且不易被封鎖
    """
    symbol = symbol.strip()
    # 嘗試兩種後綴，直到成功為止
    for suffix in ['.TW', '.TWO']:
        ticker_code = symbol if (symbol.endswith('.TW') or symbol.endswith('.TWO')) else f"{symbol}{suffix}"
        try:
            ticker = yf.Ticker(ticker_code)
            # 優先嘗試取得當日歷史收盤價
            hist = ticker.history(period="1d")
            if not hist.empty:
                price = hist['Close'].iloc[-1]
                # 嘗試取得名稱與股息資訊 (這部分如果失敗不影響價格)
                try:
                    info = ticker.info
                    name = info.get('longName', symbol)
                    div_yield = info.get('dividendYield', 0.0) or 0.0
                except:
                    name = symbol
                    div_yield = 0.0
                
                return {"success": True, "name": name, "price": float(price), "div_yield": float(div_yield)}
        except:
            continue
    return {"success": False, "error": "無法在 Yahoo Finance 找到該代碼，請確認代碼是否正確"}

# -----------------------------------------------------------------------------
# 介面顯示
# -----------------------------------------------------------------------------
st.title("📱 個人資產管理系統")

menu = st.sidebar.selectbox("功能選單", [
    "1. 股票庫存管理", "2. 借貸與質押", "3. 現金與曝險", "4. 月現金流", "5. 使用說明"
])

# --- 1. 股票庫存 ---
if menu == "1. 股票庫存管理":
    st.header("📈 股票庫存管理")
    tab1, tab2 = st.tabs(["庫存總覽", "新增庫存"])
    
    with tab2:
        st.subheader("新增股票")
        code = st.text_input("輸入股票代碼 (例: 2330, 0050)")
        if st.button("查詢並新增"):
            with st.spinner("正在聯網查詢..."):
                res = fetch_tw_stock(code)
                if res['success']:
                    st.success(f"找到: {res['name']} | 當前股價: {res['price']}")
                    # 新增邏輯
                    shares = st.number_input("股數", value=1000)
                    cost = st.number_input("買入成本", value=res['price'])
                    if st.button("確認寫入"):
                        new_data = {
                            "股票代碼": code, "股票名稱": res['name'], "買入日期": str(datetime.date.today()),
                            "成本價": cost, "股數": shares, "當日收盤價": res['price'],
                            "市值": res['price'] * shares,
                            "未實現損益": (res['price'] - cost) * shares,
                            "報酬率(%)": round(((res['price'] - cost) / cost) * 100, 2),
                            "預估年股息": round(res['price'] * shares * res['div_yield'], 0)
                        }
                        st.session_state.stocks = pd.concat([st.session_state.stocks, pd.DataFrame([new_data])], ignore_index=True)
                        st.rerun()
                else:
                    st.error(res['error'])
    
    with tab1:
        if not st.session_state.stocks.empty:
            st.dataframe(st.session_state.stocks, use_container_width=True)
            if st.button("🗑️ 清空所有庫存"):
                st.session_state.stocks = pd.DataFrame(columns=st.session_state.stocks.columns)
                st.rerun()

# --- 其他選單對應 ---
elif menu == "2. 借貸與質押":
    st.header("💳 借貸與質押管理")
    st.info("此區塊可手動輸入借貸金額與維持率計算...")

elif menu == "3. 現金與曝險":
    st.header("💵 備用現金與總曝險比")
    st.session_state.cash = st.number_input("目前備用現金", value=st.session_state.cash)
    st.write(f"系統總資產: ${st.session_state.cash + st.session_state.stocks['市值'].sum():,.0f}")

elif menu == "4. 月現金流":
    st.header("💰 月現金流試算")
    income = st.number_input("每月收入", value=st.session_state.income)
    st.write("淨現金流計算中...")

else:
    st.write("歡迎使用，請從左側選單選擇功能。")
