---
name: trip-mini-app
description: 幫一群朋友做出國旅行用的手機網站（行程、地圖、口袋名單、待辦／記事本、記帳分帳＋收據辨識＋還款核銷），用 trip-mini-app-template 框架，部署在 GitHub Pages、多人同步走 Google Sheet＋Apps Script。使用者說「幫我做一個 XX 旅行的網站／mini app／行程＋記帳網站」時使用。
---

# Trip Mini App

框架就是這個 repo（trip-mini-app-template）。**不要從零寫**：先收集 Input → 跑初始化 → 匯入資料 → 驗證 → 部署。細節和指令都在 `README.md`，本檔講流程與判斷。

## 1. 先問清楚 Input（一次問完，用 AskUserQuestion 或條列）
必填：旅程名稱（含主畫面短名）、日期、成員（名字、英文名、誰提早走）、城市、當地貨幣／本國貨幣。
選填，逐項問「有沒有」：住宿地址、航班、Google Sheet（餐廳清單／每日安排）、要不要多人同步（決定要不要部署 Apps Script）、IG 群組匯出檔、Threads 匯出檔、Google Maps 清單連結、要不要每日匯率、Google Places API key。
- 城市有 preset（`presets/<城市>`）就用；沒有就查城市中心座標、bbox，`data/areas.json` 可以先放空陣列，之後再補區域
- 成員 `aliases` 要對到 IG／Threads 上的顯示名稱；對不上的要問使用者，不可以猜

## 2. 建立
1. 把模板複製到新資料夾（或在 GitHub 用 template 建新 repo）
2. 寫 `setup.json` → `python tools/new_trip.py setup.json`
3. `python tools/make_icon.py "<代表這個城市的 emoji>"`，或自己畫 SVG（東京鐵塔範例在 `presets/tokyo/icon.svg`）
4. 匯入口袋名單（有的才做）：
   - Google Maps 清單：`tools/importers/gmaps_list.py`
   - IG／Threads：先跑匯入工具拿到原文，再照 `tools/importers/EXTRACT_PROMPT.md` 開 subagent 分批抽地點（每批 70–80 則）；跑之前先問使用者同不同意用多個 subagent，然後 `python tools/build_data.py _raw`
   - 匯出檔含整個帳號的私人資料，放 `_raw/`，**絕對不可以進 repo**
5. `python tools/sync_sheet.py` → `data/places.json`
6. 每日匯率：`tools/importers/bank_fx.py`（臺灣銀行）；本國貨幣不是台幣要換資料來源，格式不變

## 3. 驗證（交付前一定要做）
- `python tools/verify_smoke.py`：6 個分頁＋記一筆帳，抓 JS 錯誤、水平溢出，截圖在 `_shots/`；**截圖要實際打開來看**
- 自己寫的任何測試都要攔截 `config.js`、把 `sheetApi` 清空，不然會寫進真的帳本
- 要預覽真實資料時只能讀：擋掉所有送往 `script.google.com` 的 POST
- 手機尺寸 390×844 為主

## 4. 部署
- GitHub Pages：push 到 `main` → Settings → Pages → `main` / root。repo 名稱、要不要公開，先問使用者
- 多人同步：照 README 第三節帶使用者部署 Apps Script。使用者要貼程式碼時，**給整段完整的 Code.gs**，不要只給片段
- 授權要跑 `authorizeDrive`，授權畫面要全部勾選；之後改版一律「管理部署作業 → 新版本」
- 分享連結用 `https://<帳號>.github.io/<repo>/?openExternalBrowser=1`（LINE 會改用外部瀏覽器開）
- 有 Google Sheet 就保留 `.github/workflows/sync-sheet.yml`，請使用者到 Actions 手動 Run 一次確認

## 5. 跟使用者溝通
- 用繁體中文，口吻依對象調整（給朋友的介紹文要親近）
- 改了會影響帳務的東西（匯率、分帳規則），要列出每個人改之前和改之後的金額
- 網站上不要寫成員的私事，例如誰提早回國、誰搭廉價航空；用 `until` 處理就好
- 跟真的帳本有關的動作（寫入、刪除）先講清楚會發生什麼；動之前先備份 `GET /exec` 的結果
