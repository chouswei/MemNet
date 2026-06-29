# Novel Mobile（LAN 手機 UI）

手機瀏覽器專用的 setup + 劇情 play 介面。與 Cursor chat + `cursor_beat.py` **共用** beat 管線。

## 使用者 vs 世界

| 層級 | 識別 | 用途 |
|------|------|------|
| **使用者** | Google 登入 JWT，或 open 模式 `X-Novel-User-Id`（瀏覽器 UUID） | 認證、世界清單、擁有權 |
| **世界** | `X-Novel-World-Id` | MemNet session、編劇／作者 threads、章節、存檔 |

同一使用者可擁有**多個世界**；隔離邊界是**世界**，不是使用者帳號。

每位世界的檔案在 `novel-output/<app>/worlds/<world_id>/`：

- `meta.json`（`owner_id`、`title`）
- `session_id.txt`、`session_snap.json`、`last_beat.json`、`chapters/`
- `threads/script.json`（編劇）、`threads/prose.json`（作者）

**武學 catalog session** 仍依 genre 共用（`novel-output/catalogs/...`）。

- `POST /api/worlds` — 建立新世界並 bootstrap
- `GET /api/worlds` — 列出目前使用者的世界
- `POST /api/session/rebootstrap` — 重開**當前世界**（同一 `world_id`，新 MemNet session）
- 無 world header 時走 **legacy** 單 slot（`novel-output/<app>/session_id.txt`，相容測試／CLI）

## 安裝

```powershell
pip install -e ".[mcp,novel-mcp,novel-mobile]"
```

## 啟動

```powershell
memnet serve
$env:DEEPSEEK_API_KEY = "sk-..."
novel-mobile --app shenjia_caifa --host 0.0.0.0 --port 8765
```

手機（同 Wi‑Fi）：`http://<PC-LAN-IP>:8765`（Windows 用 `ipconfig` 查 IPv4）。

## 認證

| 模式 | 環境變數 | 說明 |
|------|----------|------|
| **open**（預設） | 無 | LAN 開發；瀏覽器 UUID 作 `user_id` |
| **token** | `NOVEL_MOBILE_TOKEN` | 共用 Bearer |
| **google** | `GOOGLE_CLIENT_ID` + `NOVEL_MOBILE_JWT_SECRET` | Google 登入；JWT 只含 `user_id` |

### Google 登入設定

1. [Google Cloud Console](https://console.cloud.google.com/) → OAuth 2.0 Client ID（Web）
2. **Authorized JavaScript origins**：`http://localhost:8765`、`http://<LAN-IP>:8765`
3. 環境變數：

```powershell
$env:GOOGLE_CLIENT_ID = "xxxx.apps.googleusercontent.com"
$env:NOVEL_MOBILE_JWT_SECRET = "long-random-secret"
$env:NOVEL_MOBILE_GOOGLE_ALLOWED_EMAILS = "you@gmail.com"  # 可選
```

登入後 UI 會列出你的世界，可「新開世界」或「重開世界」。

可選 Bearer（token 模式）：

```javascript
localStorage.setItem("novel_mobile_token", "secret");
```

## 除錯分工

| 通道 | 用途 |
|------|------|
| **Cursor chat + MCP** | setup、劇情、seed／steering、產線邏輯 |
| **本 UI** | HTTP job、SPA、觸控版面 |

## 限制（v1）

- 單一世界同時僅一個 beat job；不同世界可並行
- 無 HTTPS／公網
- SPA 不內建世界選單以外的 genre 切換（用 CLI `--app`）
