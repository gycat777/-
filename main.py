import os
import requests
import pandas as pd
import io

# 從 GitHub Secrets 取得變數
LINE_ACCESS_TOKEN = os.getenv('LINE_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

def get_kgi_shilin_from_source():
    # 這是 MoneyDJ 體系真正的資料查詢 API
    # a=9200 (凱基總公司體系), b=9238 (士林分點)
    url = "https://stock.capital.com.tw/z/zg/zgb/zgb0.djhtm?a=9200&b=9238"
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://stock.capital.com.tw/'
    }
    
    try:
        # 使用 Session 維持連線狀態
        session = requests.Session()
        res = session.get(url, headers=headers, timeout=20)
        res.encoding = 'big5'
        
        # 由於網頁可能使用了 script 轉向，我們改用 pandas 強制掃描所有表格
        # 這次我們不設過濾條件，先抓出所有 Table
        dfs = pd.read_html(io.StringIO(res.text))
        
        # 在所有表格中尋找「買賣超」這三個字
        df_result = None
        for temp_df in dfs:
            # 將所有欄位轉為字串方便搜尋
            df_content = temp_df.astype(str).values.flatten()
            if any("買賣超" in s for s in df_content if s):
                df_result = temp_df
                break
        
        if df_result is None:
            return None, "數據解析失敗：目標表格未出現在回傳內容中。"

        # 整理表格：去除多餘標題與雜質
        # 通常第 0 到 2 欄是我們要的：股票名稱、買張、賣張、買賣超
        # 重新定義欄位名稱
        df_result.columns = df_result.iloc[0] # 以第一列當標題
        df_result = df_result.drop(df_result.index[0]) # 刪除重複標題列
        
        # 欄位清洗 (處理可能存在的 Big5 亂碼或空白)
        df_result.columns = [str(c).strip() for c in df_result.columns]
        
        # 轉換數值
        df_result['買賣超'] = pd.to_numeric(df_result['買賣超'], errors='coerce')
        
        # 篩選買超大於 0 的股票
        final_buys = df_result[df_result['買賣超'] > 0].dropna(subset=['股票名稱'])
        # 排除掉表格底部出現的合計行
        final_buys = final_buys[~final_buys['股票名稱'].str.contains("合計|股票|期貨")]
        
        return final_buys, None

    except Exception as e:
        return None, f"系統執行異常: {str(e)}"

def send_line_message(buy_df, error_msg):
    url = "https://api.line.me/v2/bot/message/push"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}"
    }
    
    if error_msg:
        content = f"⚠️ 凱基士林監控報錯:\n{error_msg}"
    elif buy_df is None or buy_df.empty:
        content = "📋 今日【凱基士林】無買超標的 (或資料尚未更新)。"
    else:
        content = "📋 【凱基士林】今日買超清單\n"
        content += "--------------------------\n"
        # 整理清單輸出
        for _, row in buy_df.iterrows():
            name = str(row['股票名稱']).strip()
            count = int(row['買賣超'])
            content += f"✅ {name}: +{count}張\n"
    
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": content}]
    }
    
    response = requests.post(url, headers=headers, json=payload)
    print(f"LINE 傳送結果: {response.status_code}")

if __name__ == "__main__":
    df, err = get_kgi_shilin_from_source()
    send_line_message(df, err)
