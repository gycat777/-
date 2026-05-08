def get_kgi_shilin_all_buys():
    # 凱基士林的分點代號是 9238 (或 9217，視資料來源而定)
    branch_id = '9238' 
    
    # 這裡是以「玩股網」或其他公開資訊站點為目標的範例 URL (邏輯示意)
    # 實際運作時，程式會去解析 HTML 表格
    url = f"https://www.wantgoo.com/stock/astock/agentbuy?agentId={branch_id}"
    
    try:
        # 使用 pandas 直接嘗試讀取網頁中的表格
        # 注意：實際執行可能需要 header 偽裝成瀏覽器，否則會被擋
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers)
        dfs = pd.read_html(response.text)
        
        # 取得買賣超表格 (通常是頁面上的第一個或第二個表格)
        df = dfs[0] 
        
        # 假設欄位名稱是 '股票名稱' 和 '買超張數'
        # 這裡會根據實際網頁欄位名稱做微調
        all_buys = df[df['買超張數'] > 0].sort_values(by='買超張數', ascending=False)
        return all_buys
        
    except Exception as e:
        print(f"抓取資料發生錯誤: {e}")
        # 如果抓不到真實資料，回傳空清單，避免程式崩潰
        return pd.DataFrame()
