"""
將 360 家下游業者依「消費者食用情境」分類,而非依法定公司名稱。

食藥署原始清單只有業者法定名稱,一般消費者通常不知道自己常去的店
背後的公司全名,因此本腳本用業者名稱關鍵字,概略歸類成幾種消費情境
(外食連鎖餐飲、超市量販、傳統市場雜糧行、食品廠商包裝商品、物流倉儲、
個人/其他),方便消費者用「我平常都去哪裡買/吃」的方式瀏覽,而不必先
知道正確的公司名稱。

注意:此分類為關鍵字推測,非食藥署官方分類,僅供消費者初步縮小範圍,
不代表對該業者性質的正式認定。
"""
import json
import re

PATH = "/Users/aprillin/food-oil-checker/data/downstream-businesses.json"

# 依優先順序比對(由上而下,第一個命中的規則勝出)。
# 順序原則:先排除「幕後供應鏈」(倉儲物流),再抓外食連鎖,
# 再抓知名量販超市,再抓傳統雜糧行商行,最後才是食品廠商/個人/其他。
RULES = [
    ("物流・倉儲・批發配送(非消費者直接接觸)", [
        "物流", "流通", "配送", "宅配通", "倉庫", "倉】", "北配倉", "北倉",
        "常溫倉", "岡山倉", "梧棲倉", "觀音倉", "營業所",
    ]),
    ("飯店・團膳・機構餐飲", [
        "酒店", "飯店", "團膳", "盒膳", "福利事業管理處", "農會", "國防部",
    ]),
    ("連鎖餐飲・咖啡・手搖飲・烘焙", [
        "餐飲", "咖啡", "燒臘", "麵包", "快餐", "海鮮館", "美食", "好樂迪",
        "爭鮮", "職人",
    ]),
    ("超市・量販・百貨", [
        "家樂福", "大買家", "惠康百貨", "大全聯", "好市多", "愛買", "全聯",
        "美廉社",
    ]),
    ("傳統市場・雜糧行・商行", [
        "雜糧行", "米店", "糧行", "油行", "南北雜貨", "商行", "商社", "行銷",
    ]),
    ("食品廠商(超市/賣場包裝商品)", [
        "食品", "實業", "事業", "企業", "生技", "工業",
    ]),
]

# 消費者普遍熟悉的食品/民生品牌,名稱本身未含上述關鍵字(如「聯合利華」
# 「老協珍」),但確實是市面常見包裝商品廠商,人工核對後補上。
KNOWN_BRANDS = [
    "老協珍", "聯合利華", "味王", "味源", "聯豐麵粉",
]

INDIVIDUAL_RE = re.compile(r"O")  # 姓名遮蔽格式,如「蔡O彤」

# 有幾家倉屬性明顯但名稱中帶「倉」以外字樣的個案,以及某些行政區購物中心
# 之類難以用單一關鍵字涵蓋,交由「其他」桶,不強行分類。

def categorize(name: str) -> str:
    for label, keywords in RULES:
        if any(kw in name for kw in keywords):
            return label
    # 「XX行」這種單字結尾也算?已涵蓋在「商行」規則的「行銷」和「商行」,
    # 但像「三和行」「久代商行」已含「商行」,「三億行」「昱誠-油脂」等
    # 未必含「商行」兩字,補一個寬鬆的「行」結尾規則:
    if name.endswith("行") or "-油脂" in name or name.endswith("店"):
        return "傳統市場・雜糧行・商行"
    if len(re.sub(r"[A-Za-z0-9()（）\-\s]", "", name)) <= 4 and INDIVIDUAL_RE.search(name):
        return "個人零售"
    if any(b in name for b in KNOWN_BRANDS):
        return "食品廠商(超市/賣場包裝商品)"
    return "其他/無法判斷"


def main():
    with open(PATH, encoding="utf-8") as f:
        data = json.load(f)

    counts = {}
    for e in data["businesses"]:
        cat = categorize(e["業者"])
        e["消費情境分類"] = cat
        counts[cat] = counts.get(cat, 0) + 1

    data["分類說明"] = (
        "「消費情境分類」為依業者名稱關鍵字自動概略歸類,方便消費者依「我平常都去哪裡"
        "買/吃」瀏覽,並非食藥署官方分類,實際業務性質請自行核實。"
    )

    with open(PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("分類統計:")
    for cat, n in sorted(counts.items(), key=lambda x: -x[1]):
        print(f"  {cat}: {n}")


if __name__ == "__main__":
    main()
