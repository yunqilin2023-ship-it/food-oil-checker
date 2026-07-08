"""
解析食藥署「中聯油脂案專區」下游業者清單 PDF 抽取文字(downstream360.txt),
產出結構化 JSON。

來源:衛生福利部食品藥物管理署 中聯油脂案專區
https://www.fda.gov.tw/tc/siteList.aspx?sid=13708
「下游業者360家清單(截至7月8日)」PDF

原則:僅擷取可明確辨識、不會誤植的欄位(序號、縣市、業者名稱),
避免因 PDF 表格斷行造成品項與批號誤配對。品項/批號原始文字整段保留
供比對與人工核對,不做無法保證正確性的欄位拆分。
"""
import re
import json

SRC = "/private/tmp/claude-502/-Users-aprillin-ai-vault/af74136f-127a-4c12-a0e4-9e9ad5a3fb9f/scratchpad/oil-data/downstream360.txt"
OUT = "/Users/aprillin/food-oil-checker/data/downstream-businesses.json"

CITY_SUFFIX = ("市", "縣")

with open(SRC, encoding="utf-8") as f:
    raw_lines = [line.rstrip("\n") for line in f]

# 去除每行前的 pdfplumber 行號 tab(格式為 "123\t內容")
lines = []
for l in raw_lines:
    m = re.match(r"^\d+\t(.*)$", l)
    lines.append(m.group(1) if m else l)

# 移除頁首/頁尾雜訊
NOISE_PATTERNS = [
    r"^中聯油脂\(油槽315\)$",
    r"^福懋、福壽及泰山油品下游業者清單",
    r"^序號 縣市 業者 品項 批號 有效日期$",
    r"^第 \d+ 頁，共 \d+ 頁$",
]
noise_re = re.compile("|".join(NOISE_PATTERNS))

# 找出備註區塊起點,分離正文與備註
body_lines = []
note_lines = []
in_notes = False
for l in lines:
    if l.strip() == "備註：":
        in_notes = True
        continue
    if in_notes:
        note_lines.append(l)
        continue
    if noise_re.match(l.strip()):
        continue
    if l.strip() == "":
        continue
    body_lines.append(l)

# 每個業者條目以 "N[*] 縣市 業者名稱 ..." 開頭
entry_start_re = re.compile(
    r"^(?P<serial>\d+)(?P<star>\*?)\s+(?P<city>\S*?[市縣])\s*(?P<rest>.*)$"
)

entries = []
current = None

for l in body_lines:
    m = entry_start_re.match(l)
    if m and (current is None or m.group("rest").strip()):
        # 新條目開頭:必須有 rest(業者名稱),避免誤判純城市延續行
        current = {
            "序號": int(m.group("serial")),
            "有註記": bool(m.group("star")),
            "縣市": m.group("city"),
            "業者": "",
            "detail_lines": [],
        }
        rest = m.group("rest").strip()
        # rest 開頭通常是業者名稱,其後才是品項/批號/日期
        # 業者名稱與品項之間沒有固定分隔符,故整段先放 detail_lines,
        # 業者名稱另用啟發式:取到第一個常見品項關鍵字之前的文字
        current["_first_rest"] = rest
        entries.append(current)
    else:
        if current is not None:
            current["detail_lines"].append(l)

# 從 _first_rest 中切出業者名稱(取「品項」關鍵字前的文字作為業者名,
# 品項關鍵字集合來自 18 項第一層產品常見詞)
PRODUCT_HINTS = [
    # 泰山品牌完整品項前綴(需放在「沙拉油」等泛用詞之前,
    # 避免把「泰山XX」誤判為業者名稱的一部分;
    # 泰山自家倉庫如「泰山公司北配倉」「泰山北倉-宏大」不受影響,
    # 因其後接的是公司/倉庫用詞而非下列品項後綴)
    "泰山不飽和大豆沙拉油", "泰山花生風味調和油", "泰山精選蔬菜油",
    "泰山好理調合油", "泰山歐式果實精華調合油", "泰山大豆沙拉油",
    "益康大豆沙拉油", "益康烹調油", "一級黃豆油", "環保鐵桶沙拉油",
    "沙拉油", "健味香油", "黃豆油", "烹調油", "調合油", "調和油",
    "耐炸油", "原油", "蔬菜油", "花生風味", "益康",
]
hint_re = re.compile("|".join(re.escape(h) for h in PRODUCT_HINTS))

# 業者名稱結尾若殘留批號/日期(PDF斷行導致誤黏),予以清除並歸還品項欄位。
# 批號樣式如 C2140426O、20270410000407、BL240426L;日期樣式如
# 2027.10.13 或 115.9.30。
TRAILING_CODE_DATE_RE = re.compile(
    r"\s*((?:[A-Z]\d{6,}[A-Z]?|\d{8,})\s*)?(\d{2,4}\.\d{1,2}\.\d{1,2})?\s*$"
)

for e in entries:
    rest = e.pop("_first_rest")
    m = hint_re.search(rest)
    if m:
        name_part = rest[: m.start()].strip()
        first_detail = rest[m.start():].strip()
    else:
        name_part = rest.strip()
        first_detail = ""

    # 清掉業者名稱尾端誤黏的批號/日期殘留字串
    cm = TRAILING_CODE_DATE_RE.search(name_part)
    if cm and (cm.group(1) or cm.group(2)):
        leaked = name_part[cm.start():].strip()
        name_part = name_part[: cm.start()].strip()
        if leaked:
            first_detail = (leaked + " " + first_detail).strip()

    e["業者"] = name_part
    if first_detail:
        e["detail_lines"].insert(0, first_detail)

    # 少數條目因 PDF 品項欄位跨行,業者名稱被推到後續行(如
    # 「泰山大豆沙拉油0.6L*12入(新」/「155 苗栗縣 2027041301 2027.04.13」/
    # 「口美商社 版)」三行合一儲存格),導致本行沒有可用的業者名稱。
    # 於後續行中尋找「看起來像業者名稱」的候選行(無品項關鍵字、無批號/日期)
    # 補回業者欄位。
    if not e["業者"]:
        for i, dl in enumerate(e["detail_lines"]):
            candidate = re.sub(r"\s*[\(（]?新?版[\)）]?\s*$", "", dl).strip()
            if (
                candidate
                and not hint_re.search(candidate)
                and not re.fullmatch(r"[A-Z0-9. ]+", candidate)
            ):
                e["業者"] = candidate
                remainder = dl[len(candidate):].strip()
                if remainder:
                    e["detail_lines"][i] = remainder
                else:
                    e["detail_lines"].pop(i)
                break

    e["品項備註原文"] = " / ".join(x for x in e["detail_lines"] if x.strip())
    del e["detail_lines"]

# 套用官方備註修正(見 downstream360.txt 備註區):
# 1) 序號 98、331 與 96(建樹企業有限公司)重複
# 2) 序號 104、243、298、345 經衛生局回復應刪除
# 3) 序號 274 為工業用途(環氧大豆油),非食品烹製用途
# 4) 序號 240、266、267、301、322 為飼料用途,非供人食用
# 5) 序號 360 業者名稱應為「和香行」(單據誤植為「誠一食品有限公司」)
DUPLICATE_OF = {98: 96, 331: 96}
REMOVED_BY_HEALTH_BUREAU = {104, 243, 298, 345}
NON_FOOD_USE = {274}
FEED_USE = {240, 266, 267, 301, 322}
NAME_FIX = {360: "和香行"}

for e in entries:
    sn = e["序號"]
    e["狀態"] = "目前流入市面"
    if sn in DUPLICATE_OF:
        e["狀態"] = f"與序號 {DUPLICATE_OF[sn]} 重複(同一業者)"
    elif sn in REMOVED_BY_HEALTH_BUREAU:
        e["狀態"] = "衛生局回復應刪除(未實際販售該批問題油品)"
    elif sn in NON_FOOD_USE:
        e["狀態"] = "非供食品烹製用途(工業用環氧大豆油原料)"
    elif sn in FEED_USE:
        e["狀態"] = "飼料用途,非供人食用"
    if sn in NAME_FIX:
        e["業者"] = NAME_FIX[sn]

# 特殊修正:序號 120/121、132/133 因原始 PDF 為跨縣市/跨行合併儲存格,
# 文字抽取時業者標記(如「121 美食家食材通路股份有限公司」)混入前一條目內文。
# 以下手動切分,避免兩個業者名稱被誤併為同一條目、或遺漏其序號。
by_serial = {e["序號"]: e for e in entries}

def split_embedded(host_serial, embed_serial, embed_name, embed_city_note, host_city_note=None):
    host = by_serial[host_serial]
    marker = f"{embed_serial} {embed_name}"
    text = host["品項備註原文"]
    idx = text.find(marker)
    if idx == -1:
        print(f"警告:找不到序號 {embed_serial} 的切分標記,略過修正")
        return
    before = text[:idx].rstrip(" /")
    after = text[idx + len(marker):].lstrip(" /")
    host["品項備註原文"] = before
    if host_city_note:
        host["縣市"] = host_city_note
    new_entry = {
        "序號": embed_serial,
        "有註記": False,
        "縣市": embed_city_note,
        "業者": embed_name,
        "品項備註原文": after,
        "狀態": "目前流入市面",
    }
    entries.append(new_entry)

# 家樂福環東倉(120)與美食家食材通路(121):原始表格顯示同一業者
# 在新北市、臺中市、臺南市、高雄市、桃園市皆有登記倉別,無法從抽取文字
# 精確還原「哪個縣市對應哪個批號」,因此縣市註記為「多縣市」,
# 品項/批號原文整段保留供人工比對,務必以官方公告 PDF 為準。
split_embedded(
    120, 121, "美食家食材通路股份有限公司",
    embed_city_note="多縣市(新北/臺中/臺南/高雄/桃園,詳見官方公告)",
    host_city_note="多縣市(新北/臺中/臺南/高雄/桃園,詳見官方公告)",
)

# 大富食品行(133):與文發商行(132)同屬新竹市,僅為表格斷行,非跨縣市問題。
split_embedded(132, 133, "大富食品行", embed_city_note="新竹市")

entries.sort(key=lambda e: e["序號"])

print(f"共解析 {len(entries)} 筆業者條目")
# 簡單檢查
bad = [e for e in entries if not e["業者"]]
print(f"業者名稱為空的條目數: {len(bad)}")
for e in bad[:10]:
    print(" ", e)

with open(OUT, "w", encoding="utf-8") as f:
    json.dump(
        {
            "來源": "衛生福利部食品藥物管理署 中聯油脂案專區 - 下游業者360家清單",
            "來源網址": "https://www.fda.gov.tw/tc/siteList.aspx?sid=13708",
            "資料截止": "2026-07-08 12:00",
            "說明": "扣除重複、非食品用途、飼料用途及經衛生局回復刪除者後,目前流入市面計348家。品項/批號因原始PDF表格跨行,無法保證逐一精確配對,故以原文整段保留,如需確認特定批號請以官方公告PDF為準。",
            "businesses": entries,
        },
        f,
        ensure_ascii=False,
        indent=2,
    )
print("寫入", OUT)
