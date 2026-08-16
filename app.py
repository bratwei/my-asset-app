import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import json

# 頁面基本設定
st.set_page_config(page_title="個人資產管理 APP", layout="wide", initial_sidebar_state="expanded")

# -----------------------------------------------------------------------------
# 初始化 Session State (記憶內部資料)
# -----------------------------------------------------------------------------
if 'stocks' not in st.session_state:
    st.session_state.stocks = pd.DataFrame(columns=[
        "股票代碼", "股票名稱", "買入日期", "成本價", "股數", "當日收盤價", "市值", "未實現損益", "報酬率(%)", "預估年股息"
    ])

if 'loans' not in st.session_state:
    st.session_state.loans = pd.DataFrame(columns=[
        "類型", "金融機構/券商", "借款金額", "年利率(%)", "每月利息支出", "質押股票代碼", "質押股數", "當前淨值", "單筆維持率(%)"
    ])

if 'cash' not in st.session_state:
    st.session_state.cash = 500000.0

if 'income' not in st.session_state:
    st.session_state.income = 60000.0

# -----------------------------------------------------------------------------
# 核心網路功能：自動抓取台股價格與數據
# -----------------------------------------------------------------------------
@st.cache_data(ttl=600)  # 快取 10 分鐘，避免頻繁請求
def fetch_tw_stock(symbol):
    try:
        # 台股自動補上 .TW
        ticker_code = f"{symbol.strip()}.TW" if not symbol.endswith(('.TW', '.TWO')) else symbol.strip()
        ticker = yf.Ticker(ticker_code)
        info = ticker.info
        
        # 取得最新價格與名稱
        price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose') or 0.0
        name = info.get('longName') or info.get('shortName') or symbol
        div_yield = info.get('dividendYield') or 0.0  # 小數點表示，例 0.04
        
        return {"success": True, "name": name, "price": float(price), "div_yield": float(div_yield)}
    except Exception as e:
        return {"success": False, "error": str(e)}

# -----------------------------------------------------------------------------
# App 標頭與主選單 (1, 2, 3, 4, 5 架構)
# -----------------------------------------------------------------------------
st.title("📱 個人資產管理系統")

menu = st.sidebar.selectbox(
    "📌 功能選單 (Menu)",
    [
        "1. 股票庫存 (總覽/新增/刪減)",
        "2. 借貸與質押管理 (維持率計算)",
        "3. 備用現金與總曝險比",
        "4. 月現金流試算",
        "5. 系統架構與公式說明"
    ]
)

st.sidebar.markdown("---")
st.sidebar.caption("數據來源：Yahoo Finance (自動連網)")

# -----------------------------------------------------------------------------
# 1. 股票庫存
# -----------------------------------------------------------------------------
if menu.startswith("1"):
    st.header("📈 1. 股票庫存管理")
    
    tab1, tab2, tab3 = st.tabs(["A. 庫存總覽", "B. 新增庫存 (自動抓價)", "C. 刪減/調整庫存"])
    
    # A. 庫存總覽
    with tab1:
        st.subheader("A. 庫存總覽 (資料由 B 自動計算帶入)")
        df = st.session_state.stocks
        
        if not df.empty:
            # 重新整理/更新當前即時股價
            if st.button("🔄 一鍵更新最新即時股價"):
                with st.spinner("正在連網更新股價..."):
                    for idx, row in df.iterrows():
                        res = fetch_tw_stock(row['股票代碼'])
                        if res['success'] and res['price'] > 0:
                            df.loc[idx, '當日收盤價'] = res['price']
                            df.loc[idx, '市值'] = res['price'] * df.loc[idx, '股數']
                            df.loc[idx, '未實現損益'] = df.loc[idx, '市值'] - (df.loc[idx, '成本價'] * df.loc[idx, '股數'])
                            if df.loc[idx, '成本價'] > 0:
                                df.loc[idx, '報酬率(%)'] = round((df.loc[idx, '未實現損益'] / (df.loc[idx, '成本價'] * df.loc[idx, '股數'])) * 100, 2)
                    st.session_state.stocks = df
                    st.success("股價更新完成！")
            
            # 彙總指標
            total_cost = (df['成本價'] * df['股數']).sum()
            total_market = df['市值'].sum()
            total_profit = total_market - total_cost
            total_ret = (total_profit / total_cost * 100) if total_cost > 0 else 0
            
            col1, col2, col3 = st.columns(3)
            col1.metric("總持股市值", f"${total_market:,.0f}")
            col2.metric("總未實現損益", f"${total_profit:,.0f}", delta=f"{total_profit:,.0f}")
            col3.metric("總投資報酬率", f"{total_ret:.2f}%")
            
            st.markdown("---")
            st.write("📊 **股票庫存明細表**")
            st.dataframe(df, use_container_width=True)
            
            # 報酬率走勢折線圖
            st.write("📈 **個股報酬率比較**")
            chart_data = df.set_index("股票代碼")[["報酬率(%)"]]
            st.line_chart(chart_data)
        else:
            st.info("目前尚無股票庫存，請切換至「B. 新增庫存」頁籤進行新增。")

    # B. 新增庫存
    with tab2:
        st.subheader("B. 新增庫存 (連網自動帶入名稱與當日市值)")
        
        col_search1, col_search2 = st.columns([3, 1])
        search_code = col_search1.text_input("輸入股票代碼 (例: 2330, 00662, 00675L)")
        search_btn = col_search2.button("🔍 查最新股價")
        
        auto_name = ""
        auto_price = 0.0
        auto_yield = 0.0
        
        if search_code:
            res = fetch_tw_stock(search_code)
            if res['success']:
                auto_name = res['name']
                auto_price = res['price']
                auto_yield = res['div_yield']
                st.success(f"✅ 成功獲取資料！名稱：{auto_name} | 當前收盤價：${auto_price}")
            else:
                st.warning("⚠️ 網路搜尋不到該代碼，您可以手動填寫以下欄位。")

        with st.form("add_stock_form"):
            code = st.text_input("股票代碼", value=search_code)
            name = st.text_input("股票名稱 (自動帶入/可修改)", value=auto_name)
            date = st.date_input("買入日期")
            cost = st.number_input("成本價 (元)", min_value=0.0, step=0.1, value=auto_price)
            shares = st.number_input("股數", min_value=0, step=1000, value=1000)
            price = st.number_input("當日收盤價 (自動連網帶入)", min_value=0.0, step=0.1, value=auto_price)
            
            submitted = st.form_submit_button("➕ 確認新增至庫存")
            if submitted:
                market_val = price * shares
                cost_val = cost * shares
                profit = market_val - cost_val
                ret = (profit / cost_val * 100) if cost_val > 0 else 0
                est_div = market_val * auto_yield
                
                new_row = {
                    "股票代碼": code, "股票名稱": name, "買入日期": str(date),
                    "成本價": cost, "股數": shares, "當日收盤價": price,
                    "市值": market_val, "未實現損益": profit, "報酬率(%)": round(ret, 2),
                    "預估年股息": round(est_div, 0)
                }
                st.session_state.stocks = pd.concat([st.session_state.stocks, pd.DataFrame([new_row])], ignore_index=True)
                st.success(f"已將 {name} ({code}) 儲存至庫存！")
                st.rerun()

    # C. 刪減庫存
    with tab3:
        st.subheader("C. 刪減庫存 / 手動加減股數")
        if not st.session_state.stocks.empty:
            selected_code = st.selectbox("選擇要處理的股票", st.session_state.stocks['股票代碼'].unique())
            action = st.radio("操作方式", ["調整股數", "整筆出清/刪減項目"])
            
            if action == "調整股數":
                new_shares = st.number_input("修改後的總股數", min_value=0, step=1000)
                if st.button("更新股數"):
                    idx = st.session_state.stocks[st.session_state.stocks['股票代碼'] == selected_code].index
                    st.session_state.stocks.loc[idx, '股數'] = new_shares
                    # 重算市值與損益
                    p = st.session_state.stocks.loc[idx, '當日收盤價'].values[0]
                    c = st.session_state.stocks.loc[idx, '成本價'].values[0]
                    st.session_state.stocks.loc[idx, '市值'] = p * new_shares
                    st.session_state.stocks.loc[idx, '未實現損益'] = (p - c) * new_shares
                    st.success("股數調整完成！")
                    st.rerun()
            else:
                if st.button("🗑️ 確認刪減出清該項目"):
                    st.session_state.stocks = st.session_state.stocks[st.session_state.stocks['股票代碼'] != selected_code]
                    st.success("項目已刪除！")
                    st.rerun()
        else:
            st.info("無庫存可進行調整。")

# -----------------------------------------------------------------------------
# 2. 借貸管理 (質押與維持率)
# -----------------------------------------------------------------------------
elif menu.startswith("2"):
    st.header("💳 2. 借貸與股票質押管理")
    
    with st.form("loan_form"):
        st.subheader("新增借貸 / 質押紀錄")
        l_type = st.selectbox("借貸類型", ["一般銀行借貸", "股票質押"])
        bank = st.text_input("金融機構 / 券商名稱 (例: 元大證券)")
        amount = st.number_input("借款金額 (元)", min_value=0.0, step=10000.0)
        rate = st.number_input("年利率 (%)", min_value=0.0, step=0.1, value=2.5)
        
        # 質押專用欄位
        p_code = ""
        p_shares = 0
        p_nav = 0.0
        
        if l_type == "股票質押":
            st.markdown("---")
            st.write("🔒 **股票質押明細設定**")
            p_code = st.text_input("質押股票代碼 (例: 00662)")
            p_shares = st.number_input("質押股數", min_value=0, step=1000)
            
            # 連網查當前淨值
            if p_code:
                res = fetch_tw_stock(p_code)
                if res['success']:
                    p_nav = res['price']
                    st.info(f"自動抓取當日前淨值/收盤價：${p_nav}")
            
            p_nav = st.number_input("當日淨值 / 收盤價 (可手動微調)", value=p_nav, step=0.1)
        
        submitted = st.form_submit_button("➕ 儲存借貸資料")
        if submitted:
            m_interest = (amount * (rate / 100)) / 12
            p_market = p_shares * p_nav
            maint_rate = (p_market / amount * 100) if amount > 0 else 0
            
            new_loan = {
                "類型": l_type, "金融機構/券商": bank, "借款金額": amount,
                "年利率(%)": rate, "每月利息支出": round(m_interest, 0),
                "質押股票代碼": p_code, "質押股數": p_shares, "當前淨值": p_nav,
                "單筆維持率(%)": round(maint_rate, 2)
            }
            st.session_state.loans = pd.concat([st.session_state.loans, pd.DataFrame([new_loan])], ignore_index=True)
            st.success("借貸紀錄已新增！")
            st.rerun()

    st.markdown("---")
    st.subheader("📋 借貸明細與整戶維持率計算")
    
    if not st.session_state.loans.empty:
        st.dataframe(st.session_state.loans, use_container_width=True)
        
        # 整戶維持率計算 (總質押市值 / 總質押借款金額)
        pledge_df = st.session_state.loans[st.session_state.loans['類型'] == "股票質押"]
        if not pledge_df.empty:
            total_p_val = (pledge_df['質押股數'] * pledge_df['當前淨值']).sum()
            total_p_loan = pledge_df['借款金額'].sum()
            overall_maint = (total_p_val / total_p_loan * 100) if total_p_loan > 0 else 0
            
            st.warning(f"⚠️ **整戶股票質押維持率：{overall_maint:.2f}%** (追繳警戒線一般為 130% ~ 140%)")
    else:
        st.info("目前無任何借貸紀錄。")

# -----------------------------------------------------------------------------
# 3. 備用現金與總曝險比
# -----------------------------------------------------------------------------
elif menu.startswith("3"):
    st.header("💵 3. 備用現金與曝險比計算")
    
    st.session_state.cash = st.number_input("目前備用現金總額 (元)", value=st.session_state.cash, step=10000.0)
    
    stock_val = st.session_state.stocks['市值'].sum() if not st.session_state.stocks.empty else 0
    total_assets = stock_val + st.session_state.cash
    exposure_ratio = (stock_val / total_assets * 100) if total_assets > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("備用現金", f"${st.session_state.cash:,.0f}")
    col2.metric("股票總市值", f"${stock_val:,.0f}")
    col3.metric("總資產曝險比", f"{exposure_ratio:.2f}%")
    
    st.progress(min(int(exposure_ratio), 100))
    if exposure_ratio > 80:
        st.caption("⚠️ 目前總資產曝險比高於 80%，建議留意備用現金是否足夠因應市場波動。")

# -----------------------------------------------------------------------------
# 4. 月現金流試算
# -----------------------------------------------------------------------------
elif menu.startswith("4"):
    st.header("💰 4. 月現金流試算")
    
    st.session_state.income = st.number_input("每月主動收入 (薪資/營業收入)", value=st.session_state.income, step=5000.0)
    
    # 自動加總利息支出
    total_interest = st.session_state.loans['每月利息支出'].sum() if not st.session_state.loans.empty else 0
    
    # 自動估計股票每月平均配息 (自動帶入 B 新增時抓取的殖利率，若無則以 4% 估算)
    if not st.session_state.stocks.empty and '預估年股息' in st.session_state.stocks.columns:
        annual_div = st.session_state.stocks['預估年股息'].sum()
        monthly_div = annual_div / 12
    else:
        monthly_div = 0.0
        
    net_cashflow = st.session_state.income + monthly_div - total_interest
    
    st.markdown("---")
    st.write(f"💵 **每月主動收入**：${st.session_state.income:,.0f}")
    st.write(f"📈 **預估每月股票配息 (自動計算)**：${monthly_div:,.0f}")
    st.write(f"💸 **每月借貸利息總支出**：-${total_interest:,.0f}")
    st.subheader(f"✨ 每月淨現金流：${net_cashflow:,.0f}")

# -----------------------------------------------------------------------------
# 5. 說明頁面
# -----------------------------------------------------------------------------
else:
    st.header("📖 5. 選單架構與專有名詞說明")
    
    st.markdown("""
    ### 📂 選單系統架構對照
    * **1. 股票庫存**：
        * A. 庫存總覽（含報酬率走勢與自動即時股價）
        * B. 新增庫存（**自動連網抓取當日收盤價與預估殖利率**）
        * C. 刪減庫存（增減股數與清空）
    * **2. 借貸管理**：銀行貸款與股票質押紀錄，自動試算**單筆維持率與整戶維持率**。
    * **3. 備用現金**：即時計算總資產曝險比。
    * **4. 現金流**：整合主動收入、自動股息與利息支出試算淨現金流。
    
    ---
    
    ### 📐 核心算式說明
    1. **股票質押維持率** = $(\\text{質押股票市值} \\div \\text{借款金額}) \\times 100\\%$
    2. **整戶維持率** = $(\\text{總質押股票市值} \\div \\text{總質押借貸金額}) \\times 100\\%$
    3. **總資產曝險比** = $(\\text{股票總市值} \\div (\\text{股票總市值} + \\text{備用現金})) \\times 100\\%$
    """)
