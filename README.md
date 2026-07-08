# 問題沙拉油查詢工具

中聯油脂苯駢芘超標大豆沙拉油事件消費者查詢工具。輸入品牌、品名、批號或上傳標籤照片,比對食藥署公布的問題油品與下游業者名單。

- 資料來源:[衛生福利部食品藥物管理署 中聯油脂案專區](https://www.fda.gov.tw/tc/siteList.aspx?sid=13708)
- 純靜態網站,無後端,資料檔於 `data/*.json`
- 本站非官方系統,查詢結果僅供初步比對,請以食藥署官方公告為準

## 更新資料

食藥署下游業者名單會持續更新。取得新版 PDF 後:

```bash
curl -sL -o scripts/downstream360.pdf "<食藥署新版 PDF 網址>"
python3 -m pdfplumber ... # 或參考 scripts/parse_downstream.py 的作法重新抽取文字後執行
python3 scripts/parse_downstream.py
```

18 項第一層油品資料(`data/first-tier-products.json`)為人工核對圖片版 PDF 產生,如有新增品項需手動比對更新。
