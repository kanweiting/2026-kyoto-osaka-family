# Trip Mini App 模板

給一群朋友出國用的手機網站：行程、地圖、口袋名單、待辦／記事本、記帳分帳。
純靜態網站，放在 GitHub Pages；多人同步用一份 Google Sheet＋Apps Script，免費、不用維運。
第一個實際案例是「2026 兄弟東京行」（5 人、1,000 多個口袋名單、42 筆記帳）。

## 功能
| 分頁 | 內容 | 資料存哪 |
|---|---|---|
| 🗓️ 行程 | 每日時間軸、今日重點（自動整理＋負責人摘要）、拖拉排序、站間交通估算、當日路線地圖 | 共享 |
| 🗺️ 地圖 | 依類型上色、類別開關＋全部關閉、★ 收藏圖層、◎ 我在哪一區、滑動卡片 | 共享（收藏）／手機（篩選） |
| 🔍 探索 | 搜尋、篩區域／「那天有開」、排離我最近；找不到可「在 Google 地圖搜尋」或貼 Google Maps 連結新增 | 共享 |
| ✅ 準備 | 待辦清單（可自訂）＋記事本 | 只存在自己手機 |
| 📊 統計 | 各區候選數、類型 × 區域矩陣 | — |
| 💴 記帳 | 拍收據自動帶入金額時間、類別、均分／比例／金額、每日小計、每天匯率、最少轉帳結算、還款＋核銷雙重確認 | 共享 |

---

## 一、開始前要準備的 Input
**必填**（寫進 `setup.json`，範例在 `setup.example.json`）
| Input | 說明 |
|---|---|
| 旅程名稱 | `title`（網站內標題）、`short`（左上角）、`homeScreenName`（加到主畫面的名字） |
| 日期 | `start`、`end` |
| 成員 | 每人一個 `id`（小寫英文）、`name`（頭像上的字，1 個字最好看）、`en`（選身分時顯示的名字）；有人提早離開就加 `until`（之後的帳預設不分給他）；`aliases` 填他在 IG／Threads 上的顯示名稱 |
| 城市 | 用 `"preset": "tokyo"`；或自己填 `name`、`nameEn`、`center`、`bbox`、`region`、`addressKeys`、`flag`、`heroEmoji` |
| 幣別 | 當地貨幣／本國貨幣的代碼、符號、名稱 |

**選填**
| Input | 用途 | 沒有的話 |
|---|---|---|
| 住宿地址＋座標 | 行程上的「從住宿出發」、交通估算、地圖上的 🏠 | 不顯示 |
| 航班 | 寫進 `days` 當提醒 | 自己在網站上加 |
| Google Sheet（公開檢視） | 大家在 Sheet 上維護餐廳清單／每日安排，每 3 小時自動同步 | 只用網站上的資料 |
| Apps Script `/exec` 網址 | 多人同步（記帳、收藏、行程、今日重點、新增地點、收據照片） | 資料只存在各自手機 |
| IG 匯出檔（只勾「訊息」、JSON） | 把群組裡分享的 Reels／貼文變成口袋名單＋評論 | — |
| Threads 匯出檔 | 把按讚過的貼文變成口袋名單 | — |
| Google Maps 清單分享連結 | 朋友推薦的清單一鍵併入 | — |
| 每日匯率 | `tools/importers/bank_fx.py`（臺灣銀行，本國貨幣＝台幣） | 用 `fxFallback` 固定匯率 |
| Google Places API key | 搜尋時顯示真正的店名＋評分 | 免費版，店名用使用者輸入的字 |

## 二、步驟
```bash
pip install openpyxl playwright && playwright install chromium

cp setup.example.json setup.json        # 改成你們的資料
python tools/new_trip.py setup.json      # → data/trip.json、config.js、manifest、網頁標題
python tools/make_icon.py "🏯"           # 主畫面圖示（或 --svg 你的圖.svg）

# （選用）匯入口袋名單
python tools/importers/gmaps_list.py <Google Maps 清單連結> "某某的清單" <成員 id>
python tools/importers/ig_dm_links.py <IG 匯出.zip> "<群組名稱>" _raw
python tools/importers/threads_likes.py <Threads 匯出.zip> _raw "東京|日本|Tokyo"
#   → 依 tools/importers/EXTRACT_PROMPT.md 請 Claude 抽地點 → python tools/build_data.py _raw
python tools/importers/bank_fx.py JPY 2027-03-20 2027-03-24   # 每日匯率

python tools/sync_sheet.py               # → data/places.json（沒有 Sheet 就直接用 base_places）
python tools/verify_smoke.py             # 煙霧測試，不會碰真的帳本
```
推上 GitHub → repo Settings → Pages → `main` / root → 網址 `https://<帳號>.github.io/<repo>/`

## 三、多人同步（Google Sheet＋Apps Script，約 5 分鐘）
1. 新建一份 Google Sheet → 擴充功能 → Apps Script → 貼上 `apps-script/Code.gs`（先清空）→ **Ctrl+S**
2. 函式選單選 `authorizeDrive` → 執行 → 授權畫面**全部勾選**（收據照片要 Drive 權限）
3. 部署 → 新增部署作業 → 網頁應用程式：執行身分「我」、存取權「任何人」→ 複製 `/exec` 網址
4. 填進 `setup.json` 的 `sheetApi` → 重跑 `new_trip.py` → push
5. **之後改 Code.gs 一律用「管理部署作業 → ✏️ → 新版本」**；按「新增部署作業」網址會變

> 同步網址寫在 `config.js`，公開 repo 看得到；懂程式的人能讀寫帳本。不想公開就清空 `sheetApi`，改用網站內「右上角頭像 → 貼上邀請連結」（網址只存在各自手機）。

## 四、Google Sheet 格式（選用）
- **餐廳清單**分頁第一列：`項次 | 餐廳類型 | 餐廳名稱 | 公休 | 備註 | Google Map 連結 | 介紹連結 | 投票`；「Google Map 連結」那格要放 Google Maps 分享連結（超連結），才抓得到座標
- **餐廳安排**分頁：B 欄是時段（早餐／午餐／下午／晚餐／BAR…），下一列「時間」；C2 起放日期；「XXX想去」欄會變成那個人的收藏
- 分頁名稱填在 `setup.json` 的 `sheet.listTab`、`sheet.planTab`；GitHub Actions 每 3 小時同步一次（免費帳號實際約一天 3 次）

## 五、踩過的坑
- **分享連結加 `?openExternalBrowser=1`**：LINE 內建瀏覽器不保留資料，每次都要重選身分
- iPhone「加入主畫面」和 Safari 是兩個分開的儲存空間；第一次連上同步時，手機裡的資料會自動補傳
- Windows 上 8000 port 常被 WorkDocs 占用，本機預覽改用其他 port
- 測試一律攔截 `config.js`（`verify_smoke.py` 已處理），不然測試資料會寫進真的帳本
- 臺灣銀行網站有 JS 驗證，要用 Playwright 抓；週末沒有牌價就沿用前一營業日
- Apps Script 新版授權畫面可以逐項勾選，少勾 Drive 權限，收據照片會傳不上去
- 收據辨識（Tesseract.js）是照日本收據調的（合計／お預り／お釣り）；其他國家要調 `parseReceipt`
- 網站上不要寫成員的私事（例如誰提早回國、搭廉價航空），用 `until` 默默處理就好
