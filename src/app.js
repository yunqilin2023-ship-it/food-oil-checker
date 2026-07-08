// 問題沙拉油查詢工具 - 前端邏輯(純靜態,無後端)
// 資料來源請見 data/*.json 內的「來源」欄位。

let PRODUCTS = [];
let BUSINESSES = [];
let META = { products: null, businesses: null };
let activeCategory = "";

const CATEGORY_ORDER = [
  "連鎖餐飲・咖啡・手搖飲・烘焙",
  "超市・量販・百貨",
  "傳統市場・雜糧行・商行",
  "飯店・團膳・機構餐飲",
  "食品廠商(超市/賣場包裝商品)",
  "物流・倉儲・批發配送(非消費者直接接觸)",
  "個人零售",
  "其他/無法判斷",
];

async function loadData() {
  const [productsRes, businessesRes] = await Promise.all([
    fetch("data/first-tier-products.json"),
    fetch("data/downstream-businesses.json"),
  ]);
  const productsJson = await productsRes.json();
  const businessesJson = await businessesRes.json();

  META.products = productsJson;
  META.businesses = businessesJson;
  PRODUCTS = productsJson.products;
  BUSINESSES = businessesJson.businesses;

  document.getElementById("data-updated-note").textContent =
    `油品品項資料截止於 ${productsJson.資料截止},下游業者名單截止於 ${businessesJson.資料截止}`;

  populateCityFilter();
  renderCategoryChips();
  renderBusinessMeta();
  renderProductResults(""); // 顯示全部 18 項
  renderBusinessResults("", "");
}

function populateCityFilter() {
  const cities = [...new Set(BUSINESSES.map((b) => b.縣市))].sort((a, b) =>
    a.localeCompare(b, "zh-Hant")
  );
  const select = document.getElementById("city-filter");
  for (const city of cities) {
    const opt = document.createElement("option");
    opt.value = city;
    opt.textContent = city;
    select.appendChild(opt);
  }
}

function renderCategoryChips() {
  const counts = {};
  for (const b of BUSINESSES) {
    if (b.狀態 !== "目前流入市面") continue; // 已排除/重複者不列入分類統計
    counts[b.消費情境分類] = (counts[b.消費情境分類] || 0) + 1;
  }
  const container = document.getElementById("category-chips");
  container.innerHTML = "";

  const allChip = document.createElement("button");
  allChip.className = "category-chip active";
  allChip.textContent = `全部 (${BUSINESSES.filter((b) => b.狀態 === "目前流入市面").length})`;
  allChip.addEventListener("click", () => selectCategory("", allChip));
  container.appendChild(allChip);

  for (const cat of CATEGORY_ORDER) {
    if (!counts[cat]) continue;
    const chip = document.createElement("button");
    chip.className = "category-chip";
    chip.innerHTML = `${escapeHtml(cat)} <span class="chip-count">(${counts[cat]})</span>`;
    chip.addEventListener("click", () => selectCategory(cat, chip));
    container.appendChild(chip);
  }
}

function selectCategory(cat, chipEl) {
  activeCategory = cat;
  document.querySelectorAll(".category-chip").forEach((c) => c.classList.remove("active"));
  chipEl.classList.add("active");
  renderBusinessResults(
    document.getElementById("business-search").value,
    document.getElementById("city-filter").value
  );
}

function renderBusinessMeta() {
  const excluded = BUSINESSES.filter((b) => b.狀態 !== "目前流入市面").length;
  document.getElementById("business-meta").textContent =
    `共收錄 ${BUSINESSES.length} 筆通報紀錄,其中 ${
      BUSINESSES.length - excluded
    } 筆標示為目前流入市面,其餘為重複通報 / 非食品用途 / 飼料用 / 經衛生局回復刪除。${META.businesses.說明}`;
}

// ---------- 產品比對 ----------

function normalize(s) {
  return (s || "")
    .toLowerCase()
    .replace(/[\s\-–—_()（）*]/g, "")
    .trim();
}

function matchProduct(query) {
  const q = normalize(query);
  return PRODUCTS.map((p) => {
    if (!q) return { product: p, level: "none" };
    const nameHit = normalize(p.品名).includes(q) || normalize(p.廠商).includes(q);
    const batchHit = p.批號.some((b) => normalize(b).includes(q) && q.length >= 4);
    if (batchHit) return { product: p, level: "exact" };
    if (nameHit) return { product: p, level: "partial" };
    return { product: p, level: "none" };
  }).filter((r) => (q ? r.level !== "none" : true));
}

function renderProductResults(query) {
  const container = document.getElementById("product-results");
  const matches = matchProduct(query);
  container.innerHTML = "";

  if (query && matches.length === 0) {
    container.innerHTML = `<div class="no-result">沒有找到符合「${escapeHtml(
      query
    )}」的第一層問題油品。<br>提醒:本站僅收錄 18 項第一層(泰山/福壽/福懋)油品,若您買的是使用這些油品的下游二次加工食品(如烘焙、餐飲品項),請改用「查店家/業者」分頁,或查閱食藥署完整 401 項清單。</div>`;
    return;
  }

  for (const { product, level } of matches) {
    const card = document.createElement("div");
    card.className =
      "result-card " + (level === "exact" ? "match-exact" : level === "partial" ? "match-partial" : "");
    const badge =
      level === "exact"
        ? '<span class="badge badge-danger">批號相符,是問題產品</span>'
        : level === "partial"
        ? '<span class="badge badge-warn">品牌/品名相符,請核對批號</span>'
        : "";
    card.innerHTML = `
      ${badge}
      <div class="result-title">${escapeHtml(product.品名)}(${escapeHtml(product.容量)})</div>
      <div class="result-meta">廠商:${escapeHtml(product.廠商)}</div>
      <div class="result-meta">批號:${product.批號
        .map((b) => `<code>${escapeHtml(b)}</code>`)
        .join(" ")}</div>
      <div class="result-meta">有效日期:${product.有效日期.join("、")}</div>
    `;
    container.appendChild(card);
  }
}

// ---------- 業者比對 ----------

function renderBusinessResults(query, city) {
  const container = document.getElementById("business-results");
  const q = normalize(query);
  let matches = BUSINESSES;
  if (activeCategory) matches = matches.filter((b) => b.消費情境分類 === activeCategory);
  if (city) matches = matches.filter((b) => b.縣市 === city);
  if (q) matches = matches.filter((b) => normalize(b.業者).includes(q));

  container.innerHTML = "";

  if (!q && !city && !activeCategory) {
    container.innerHTML = `<div class="no-result">請選擇上方分類、輸入業者名稱關鍵字,或選擇縣市開始查詢(共 ${BUSINESSES.length} 筆通報紀錄)。</div>`;
    return;
  }
  if (matches.length === 0) {
    container.innerHTML = `<div class="no-result">沒有找到符合的業者,可能代表該業者不在食藥署通報名單中,或名稱寫法不同,建議換個關鍵字再試。</div>`;
    return;
  }

  // 限制一次顯示數量,避免縣市篩選(全部)時一次渲染 300+ 筆卡頓
  const shown = matches.slice(0, 100);

  for (const b of shown) {
    const excluded = b.狀態 !== "目前流入市面";
    const card = document.createElement("div");
    card.className = "result-card " + (excluded ? "match-excluded" : "match-partial");
    const badge = excluded
      ? `<span class="badge badge-excluded">${escapeHtml(b.狀態)}</span>`
      : `<span class="badge badge-warn">通報序號 ${b.序號}・${escapeHtml(b.縣市)}</span>`;
    card.innerHTML = `
      ${badge}
      <div class="result-title">${escapeHtml(b.業者)}</div>
      <div class="result-meta">分類:${escapeHtml(b.消費情境分類)}</div>
      <div class="result-meta">通報品項/批號原文:${escapeHtml(b.品項備註原文)}</div>
    `;
    container.appendChild(card);
  }
  if (matches.length > shown.length) {
    const more = document.createElement("div");
    more.className = "no-result";
    more.textContent = `還有 ${matches.length - shown.length} 筆符合結果,請輸入更精確的關鍵字縮小範圍。`;
    container.appendChild(more);
  }
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[c]));
}

// ---------- Tabs ----------

function setupTabs() {
  document.querySelectorAll(".tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((p) => p.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById("tab-" + btn.dataset.tab).classList.add("active");
    });
  });
}

// ---------- OCR(拍照辨識) ----------

function setupOcr() {
  const input = document.getElementById("product-photo");
  const status = document.getElementById("ocr-status");
  input.addEventListener("change", async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    status.textContent = "辨識中,請稍候…(依照片大小可能需要 10-30 秒)";
    try {
      const result = await Tesseract.recognize(file, "chi_tra+eng", {
        logger: () => {},
      });
      const text = result.data.text.replace(/\s+/g, " ").trim();
      status.textContent = text
        ? `辨識到文字:「${text.slice(0, 60)}${text.length > 60 ? "…" : ""}」,已自動比對下方結果。`
        : "沒有辨識到清楚的文字,請換一張較清晰、正對標籤的照片再試。";
      document.getElementById("product-search").value = text;
      renderProductResults(text);
    } catch (err) {
      status.textContent = "辨識失敗,請改用手動輸入品牌或批號查詢。";
      console.error(err);
    }
  });
}

// ---------- Init ----------

document.getElementById("product-search").addEventListener("input", (e) => {
  renderProductResults(e.target.value);
});
document.getElementById("business-search").addEventListener("input", () => {
  renderBusinessResults(
    document.getElementById("business-search").value,
    document.getElementById("city-filter").value
  );
});
document.getElementById("city-filter").addEventListener("change", () => {
  renderBusinessResults(
    document.getElementById("business-search").value,
    document.getElementById("city-filter").value
  );
});

setupTabs();
setupOcr();
loadData().catch((err) => {
  console.error(err);
  document.getElementById("data-updated-note").textContent = "資料載入失敗,請重新整理頁面。";
});
