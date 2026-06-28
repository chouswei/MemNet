# Novel Mobile（LAN 手機 UI）

手機瀏覽器專用的 setup + 劇情 play 介面。與 Cursor chat + `cursor_beat.py` **共用**同一 `session_id.txt` 與 beat 管線。

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

可選 Bearer：`$env:NOVEL_MOBILE_TOKEN = "secret"`；瀏覽器 console：

```javascript
localStorage.setItem("novel_mobile_token", "secret");
```

## 除錯分工

| 通道 | 用途 |
|------|------|
| **Cursor chat + MCP** | setup、劇情、seed／steering、產線邏輯 |
| **本 UI** | HTTP job、SPA、觸控版面 |

## 換故事（不動程式）

1. 新 `application-notes/novel-<id>-initial-state.md`
2. 新或沿用 `catalog_specs/<genre>.json`；instance 指向該 json
3. 新 `applications/novel_cursor/instances/<id>.json`
4. `novel_bootstrap.py --app <id>`
5. `novel-mobile --app <id>`

## 限制（v1）

- 單 session；第二個 beat job → HTTP 409
- 無 HTTPS／公網
- SPA 不內建世界選單（用 CLI `--app` 換實例）
