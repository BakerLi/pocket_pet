# Pocket Pet — 設計文件

桌面電子寵物(desktop mascot / Shimeji 類型)。靈感來自 Claude Code 的愚人節彩蛋 `/buddy`。

- **平台**:Windows 11(僅 Windows)
- **技術棧**:Python 3.11+ / PySide6(Qt)/ pywin32
- **目標**:寵物在桌面走動、停在其他程式視窗上緣、受重力墜落、與使用者互動,並具備完整養成系統(飢餓 / 心情 / 成長等)。

---

## 1. 核心技術方案

### 1.1 桌面覆蓋視窗(每隻寵物一個小視窗)

不做整片全螢幕透明覆蓋,而是**每隻寵物 = 一個剛好包住 sprite 的小型 top-level 視窗**,跟著寵物移動。
好處:寵物身上的點擊事件直接收得到,寵物以外的區域天然就穿透點擊,不用做 per-pixel hit-test。

關鍵旗標:
- `Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool`(`Tool` → 不出現在工作列)
- `setAttribute(Qt.WA_TranslucentBackground)`
- 視窗只在需要時才開啟滑鼠互動;不互動的裝飾(如說話泡泡)可另開穿透視窗。

### 1.2 視窗吸附(最難 — 要先 spike 驗證)

要讓寵物停在「別的程式視窗上緣」,必須讀取其他視窗的螢幕座標:
- `win32gui.EnumWindows` 列舉頂層視窗(回傳順序即 z-order,上到下)。
- 過濾:`IsWindowVisible`、非最小化、有標題、排除自己、排除桌面/Shell。
- **排除 DWM cloaked 幽靈視窗**:`DwmGetWindowAttribute(hwnd, DWMWA_CLOAKED)`(Win10/11 常見坑,UWP 背景視窗會是 cloaked)。
- **取得「視覺」邊框**:`GetWindowRect` 在 Win10/11 含隱形邊框,真正可視上緣要用
  `DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS)`。
- **平台 = 視窗上緣**。寵物腳下某個 x 的「可站平台」= 在該 x 處 z-order 最上層、且上緣在寵物下方的視窗。
- 在計時器上以較低頻率(每 200–500ms)重新整理視窗清單並快取,不要每幀都列舉(效能)。
- 當寵物腳下的視窗移動、縮放或關閉 → 平台消失 → 觸發墜落。

### 1.3 物理 / 移動

- 固定步長更新迴圈(`QTimer`,約 60fps)。
- 重力:`vy += g*dt; y += vy*dt`;腳底碰到平台上緣或地板(工作列上緣 / 螢幕底)→ 落地。
- 觸發墜落:在半空被放開、或所站平台消失。
- 拖曳丟擲:放開時依游標速度給初速 → 進入物理。

### 1.4 互動

- 拖曳(抓住 → 跟游標 → 放開帶速度)
- 點擊 / 雙擊 → 反應動畫
- 右鍵 → 選單(餵食 / 狀態 / 設定 / 寵物清單 / 結束)
- 滑過 → 說話泡泡
- 系統匣 icon(常駐、開關、結束)

### 1.5 養成系統(life-sim)

- 數值:飢餓、心情、精力、清潔、親密度、年齡/成長階段。
- **時間衰減**:即使關掉程式,記錄最後更新時間戳,下次啟動依離線時間補算衰減。
- 需求驅動行為:餓 → 找食物 / 難過動畫;睏 → 睡覺;開心 → 玩耍。
- 互動:餵食、摸摸(冒愛心)、命名。
- 成長階段:蛋 → 幼體 → 成體。
- **物種**:可致敬 Buddy —— 用使用者/裝置 ID 決定性生成物種與稀有度。
- 說話泡泡:情境台詞;之後可選接 Claude API 做對話。
- 永久化:`%APPDATA%/pocket_pet/save.json`(或 SQLite)。

### 1.6 Sprite / 動畫

- 每個狀態一組 sprite(idle / walk / fall / drag / sleep / eat / happy)。
- sprite sheet + JSON frame map,或 Shimeji 風格的 PNG 資料夾。
- 依方向水平翻轉。
- 原型階段先用色塊 / 簡單佔位圖,美術後補。

---

## 2. 專案結構

```
pocket_pet/
  pyproject.toml            # deps: PySide6, pywin32, (dev) pyinstaller, pytest
  README.md
  DESIGN.md
  assets/
    sprites/<species>/...
    config/behaviors.json
  src/pocket_pet/
    main.py                 # 進入點:設定 DPI awareness、建立 app、系統匣
    app.py                  # World/orchestrator:多寵物、tick 迴圈
    config.py
    core/
      pet.py                # Pet 實體:狀態 + 數值參照
      state_machine.py      # 行為狀態機
      physics.py            # 重力、碰撞、落地
    platform/               # OS 整合(Windows 專屬,獨立隔離以便日後跨平台)
      windows.py            # EnumWindows / GetWindowRect / DWM bounds / DPI
      screen.py             # 螢幕/多螢幕幾何、工作列位置
    ui/
      pet_window.py         # 透明 per-pet 小視窗
      sprite.py             # sprite sheet 載入 + 動畫器
      speech_bubble.py
      context_menu.py
      tray.py               # 系統匣 icon + 選單
    sim/
      needs.py              # 衰減模型
      interactions.py       # 餵食 / 摸 / 玩
      persistence.py        # 存讀檔
      species.py            # 物種定義 + 決定性生成
  tests/
```

設計原則:**所有 Windows 專屬程式碼集中在 `platform/`**,核心邏輯(物理、數值、狀態機)不依賴 OS,方便測試與日後移植。

---

## 3. 分階段路線圖

### Phase 0 — 骨架 + 技術驗證(先把最難的證明可行)
- 專案建置、相依套件。
- Spike A:透明、置頂、可穿透的小視窗,裡面一個會移動的色塊;確認 DPI / 多螢幕座標正確。
- Spike B:`EnumWindows` + `GetWindowRect` + DWM extended bounds,畫出偵測到的視窗上緣 debug 疊圖。**在往上蓋之前先證明吸附可行。**

### Phase 1 — 移動與物理
- 地板(工作列感知)上的待機/走路、方向翻轉、基本 sprite 動畫(佔位圖)。
- 重力 + 落地。

### Phase 2 — 互動
- 拖曳丟擲、點擊反應、右鍵選單、系統匣、結束/設定。

### Phase 3 — 視窗吸附(最難,已隔離)
- 由視窗清單建立平台、走上視窗上緣、平台消失時墜落、落地偵測。

### Phase 4 — 養成系統
- 數值 + 衰減 + 永久化、需求驅動行為、餵食/摸摸、成長階段、物種、說話泡泡。

### Phase 5 — 打磨與選配
- 多寵物、設定 UI、音效、Claude API 對話(致敬 Buddy)、PyInstaller 打包成 .exe、開機自啟。

---

## 4. 風險與已知坑

1. **DPI 縮放 / 多螢幕**:不設 DPI awareness,座標會錯位、寵物漂移。啟動最早就要 `SetProcessDpiAwareness`,並處理各螢幕不同縮放。
2. **點擊穿透 vs 收到點擊**:用「每隻寵物小視窗」方案解決,不需 per-pixel hit-test。
3. **吸附的 z-order 正確性**:「某點最上層視窗」很瑣碎;靠 EnumWindows z-order 順序 + 過濾 cloaked 視窗。
4. **效能**:每幀列舉視窗很貴;降頻輪詢 + 快取。
5. **全螢幕程式/遊戲**:置頂寵物會蓋住;需偵測全螢幕並自動隱藏。
6. **美術資產**:需要 sprite;先用佔位圖,核心玩法驗證後再補。
