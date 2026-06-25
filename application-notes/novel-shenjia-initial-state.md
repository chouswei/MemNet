# 沈家鐵坊傳 — Custom MemNet initial state (繁體)

`session_open` map + seed. MemNet 固定 `@LAW`/`@EDG` 欄位名為引擎格式；**值與其餘 tag 欄位標籤可用中文**。
`@EDG.relation` 須 ASCII（如 `qiuzhu`）；敘事層顯示為中文（求助）。

## Tag map

```text
@SYS: id|回合|時間|財政赤字|銀入|混亂|匯率
@PLR: id|玩家身份|出生年|財產|淨銀流|核心靈魂能力|身體狀態
@BIZ: id|名稱|類型|地點|現金|負債|收入|支出|回收
@NPC: id|名字|出生年|特徵|腐敗|工藝|技能|物品|資金缺口|狀態|回收
@SKL: id|角色|名稱|品級|回收
@ITM: id|角色|名稱|數量|回收
@TSK: id|目標|時限|狀態|回收
@TEC: id|名稱|領域|狀態|效果
@PRD: id|名稱|類型|成本|售價|狀態
@SCN: id|code|beat|recycle
@OLN: id|回合|情緒錨|情節要點|對白骨架|尾鉤|回收
@TRT: id|維度|累積|回收
@PRS: id|角色|維度|基線|回收
@PTY: id|角色|代碼|標籤|回收
@OPT: id|序|文案|維度|變化|回收
@LOC: id|名稱|區域|回收
@STEP: id|n|focus|recycle
@USR: id|key|value|recycle
```

## Opening seed

```text
@LAW: LAW-G01|解鎖|1|解除時代科技鎖、技能鎖與劇情人物行為鎖|*
@LAW: LAW-G02|資金計算|1|silver_tael|-
@LAW: LAW-G03|銀本位|1|sys_fx_rate|-
@LAW: LAW-G04|擬真規則|1|verify_facts|-
@LAW: LAW-G05|靈魂圖書館|1|lib_on_query|-
@LAW: LAW-G06|科技圖譜演進1|1|unlock_tec|-
@LAW: LAW-G07|科技圖譜演進2|1|tec_chain|-
@LAW: LAW-G08|科技圖譜演進3|1|tec_prune|-
@LAW: LAW-G09|精確性維持|4|exact_names|*
@LAW: LAW-G10|垃圾回收|1|gc_recycle|-
@LAW: LAW-G11|演算順序|1|db_before_prose|-
@LAW: LAW-G12|時限|1|tsk_timer|-
@LAW: LAW-DATA01|*|on_add|zh_hant_kv|-
@LAW: LAW-NAME01|LAW|on_add|no_plr_name|-
@LAW: LAW06|*|on_context|law_scope|linked_from_anchor
@LAW: LAW-PROSE01|敘事|1|繁體白話口語|-
@LAW: LAW-PROSE02|敘事|1|對白內心>=35pct|-
@LAW: LAW-PROSE03|敘事|1|beat_min650_zh|-
@LAW: LAW-PROSE04|敘事|1|chr_interaction|-
@LAW: LAW-PROSE05|敘事|1|sensory_embed|-
@LAW: LAW-PROSE06|敘事|1|dialogue_flow|-
@LAW: LAW-PROSE07|敘事|1|beat_structure|-
@LAW: LAW-PROSE08|敘事|1|env_serve_plot|-
@LAW: LAW-PROSE09|敘事|1|readable_prose|-
@LAW: LAW-PROSE10|敘事|1|sentence_rhythm|-
@LAW: LAW-PROSE11|敘事|1|metaphor_sparing|-
@LAW: LAW-PROSE12|敘事|1|knowledge_plain|-
@LAW: LAW-PROSE13|敘事|1|zh_idiom_fit|-
@LAW: LAW-OUT05|介面|1|no_graph_echo|-
@LAW: LAW-CHR01|PLR|1|plr_voice|-
@LAW: LAW-CHR02|NPC|1|n01_voice|-
@LAW: LAW-CHR03|NPC|1|n02_voice|-
@LAW: LAW-CHR04|*|1|trait_age_bind|-
@LAW: LAW-HUD01|介面|1|尾欄HUD單行pipe|-
@LAW: LAW-MCP01|編排|1|圖與章節僅經MCP|-
@LAW: LAW-OUT04|介面|1|hide_database_in_chat|-
@LAW: LAW-PIPE20|STEP|on_turn|two_phase|-
@LAW: LAW-PIPE21|STEP|on_turn|beat_turn|begin_finish_only
@LAW: LAW-OLN01|OLN|on_add|outline_fmt|-
@LAW: LAW-OLN02|OLN|on_turn|prose_from_oln|-
@LAW: LAW-OUT06|介面|1|outline_section|-
@LAW: LAW-PERS01|PLR|on_turn|trait_build|-
@LAW: LAW-PERS02|OPT|on_turn|trait_opts|-
@LAW: LAW-PERS03|*|on_pick|trait_delta|-
@LAW: LAW-OUT07|介面|1|trait_opt_tag|-
@LAW: LAW-NPC01|NPC|on_turn|prs_baseline|-
@LAW: LAW-NPC02|NPC|on_turn|skl_cite|-
@LAW: LAW-NPC03|NPC|on_turn|itm_cite|-

@STEP: STEP01|1|SCN01|persistent

@USR: USR01|output|prose_opts_hud_only|persistent
@USR: USR02|hud_pipe|qi_neili_status_age_quest_partner_fin_ind_datetime_lib|persistent
@USR: USR03|pc_name|未定|persistent
@USR: USR05|scene_length|650_950_zh|persistent
@USR: USR06|voice_sheet|chr01_n01_n02_trait_age|persistent
@USR: USR07|state_fmt|繁體鍵值；分隔|persistent
@USR: USR08|outline_visible|brief|persistent
@USR: USR09|opt_trait_tag|hidden|persistent
@USR: USR10|trait_dims|力量;智力;魅力;氣運|persistent
@USR: USR11|npc_persona|prs_pty|persistent
@USR: USR12|npc_skills|skl_rank|persistent
@USR: USR13|npc_items|itm_qty|persistent
@USR: USR14|chapter_out|novel-output/shenjia_caifa/chapters|persistent
@USR: USR04|skills|太玄經登峰、獨孤九劍登峰、六脈神劍略有小成、靈魂圖書館登峰、凌波微步登峰|persistent

@SYS: SYS01|1|崇禎十年(1637)秋|0|0|25|1兩=825文銅
@PLR: P01|流民乞丐|1627|0|0|靈魂圖書館登峰、太玄經登峰、獨孤九劍登峰、六脈神劍略有小成、凌波微步登峰|氣血:7/10；內力:0/10；飽食:略飽；疲勞:0；魂穿:電機工程師
@BIZ: B01|沈家鐵坊|鐵匠鋪|江南河畔|0|2|0|0|常駐
@NPC: N01|沈芯|1625|女、美貌、滿臉炭灰、孤女、聰慧、堅韌、溫柔、慾念|0|土法|打鐵:略有小成；看火:熟能；識鐵:略有小成|鐵鉗:1；護手布:1；木勺:1|0|需小工|常駐
@NPC: N02|沈蘭|1627|女、美貌、滿臉炭灰、孤女、狡黠、大膽、開放|0|土法|打鐵:初学；燒火:初学；跑腿:熟能|油燈:1；布兜:1|0|需小工|常駐
@TSK: T01|升級作坊|-1|進行|完成結算後刪
@TEC: TEC01|焦炭製作|熱力冶金|鎖定|產量+300%
@TEC: TEC02|焦炭煉鐵高爐|熱力冶金|鎖定|產量+300%
@PRD: PRD01|焦炭|物資|0|0|未量產
@PRD: PRD02|工業級生鐵|物資|0|0|未量產
@LOC: SUS01|蘇松|商路|常駐

@EDG: E01|N01|qiuzhu|P01|解鎖|失效刪
@EDG: E02|P01|bangding|T01|任務|失效刪
@EDG: E03|TEC01|produce|PRD01|產出|常駐
@EDG: E04|TEC01|develop|TEC02|條件|常駐
@EDG: E05|TEC02|produce|PRD02|產出|常駐
@EDG: E06|N01|sibling|N02|姊妹|常駐
@EDG: E07|TEC01|belongs|T01|子項目|失效刪
@EDG: E08|TEC02|belongs|T01|子項目|失效刪
@EDG: E09|N01|manages|B01|經營|常駐
@EDG: E10|N02|assists|B01|協助|常駐
@EDG: E11|B01|hiring|P01|待聘|失效刪
@EDG: E12|B01|upgrades|T01|任務|失效刪
@EDG: E13|B01|trade_route|SUS01|商路|常駐

@SCN: SCN01|smithy_gate|awakening|delete_on_settle
@EDG: ES01|STEP01|focus|SCN01||persistent
@EDG: E20|SCN01|features|P01||delete_on_settle
@EDG: E21|SCN01|features|N01||delete_on_settle
@EDG: E22|SCN01|features|N02||delete_on_settle
@EDG: E23|SCN01|features|B01||delete_on_settle
@EDG: E24|SCN01|set_in|SYS01||delete_on_settle
@EDG: E25|SCN01|features|OLN01||delete_on_settle

@TRT: TRT01|力量|0|常駐
@TRT: TRT02|智力|0|常駐
@TRT: TRT03|魅力|0|常駐
@TRT: TRT04|氣運|0|常駐
@EDG: E30|P01|has_trait|TRT01||persistent
@EDG: E31|P01|has_trait|TRT02||persistent
@EDG: E32|P01|has_trait|TRT03||persistent
@EDG: E33|P01|has_trait|TRT04||persistent

@PTY: PTY01|N01|ISFJ|守護者|常駐
@PTY: PTY02|N02|ESFP|表演者|常駐
@PRS: PRS11|N01|力量|3|常駐
@PRS: PRS12|N01|智力|3|常駐
@PRS: PRS13|N01|魅力|4|常駐
@PRS: PRS14|N01|氣運|1|常駐
@PRS: PRS21|N02|力量|2|常駐
@PRS: PRS22|N02|智力|2|常駐
@PRS: PRS23|N02|魅力|3|常駐
@PRS: PRS24|N02|氣運|4|常駐
@EDG: EP01|N01|persona|PTY01||persistent
@EDG: EP02|N02|persona|PTY02||persistent
@EDG: EP11|N01|persona|PRS11||persistent
@EDG: EP12|N01|persona|PRS12||persistent
@EDG: EP13|N01|persona|PRS13||persistent
@EDG: EP14|N01|persona|PRS14||persistent
@EDG: EP21|N02|persona|PRS21||persistent
@EDG: EP22|N02|persona|PRS22||persistent
@EDG: EP23|N02|persona|PRS23||persistent
@EDG: EP24|N02|persona|PRS24||persistent

@SKL: SK01|N01|打鐵|略有小成|常駐
@SKL: SK02|N01|看火|熟能|常駐
@SKL: SK03|N01|識鐵|略有小成|常駐
@SKL: SK04|N02|打鐵|初学|常駐
@SKL: SK05|N02|燒火|初学|常駐
@SKL: SK06|N02|跑腿|熟能|常駐
@EDG: EK01|N01|has_skill|SK01||persistent
@EDG: EK02|N01|has_skill|SK02||persistent
@EDG: EK03|N01|has_skill|SK03||persistent
@EDG: EK04|N02|has_skill|SK04||persistent
@EDG: EK05|N02|has_skill|SK05||persistent
@EDG: EK06|N02|has_skill|SK06||persistent

@ITM: IT01|N01|鐵鉗|1|常駐
@ITM: IT02|N01|護手布|1|常駐
@ITM: IT03|N01|木勺|1|常駐
@ITM: IT04|N02|油燈|1|常駐
@ITM: IT05|N02|布兜|1|常駐
@EDG: EI01|N01|carries|IT01||persistent
@EDG: EI02|N01|carries|IT02||persistent
@EDG: EI03|N01|carries|IT03||persistent
@EDG: EI04|N02|carries|IT04||persistent
@EDG: EI05|N02|carries|IT05||persistent

@EDG: EG01|STEP01|governs|USR01||persistent
@EDG: EG02|STEP01|governs|USR02||persistent
@EDG: EG03|STEP01|governs|USR03||persistent
@EDG: EG04|STEP01|governs|USR04||persistent
@EDG: EG05|STEP01|governs|USR05||persistent
@EDG: EG06|STEP01|governs|USR06||persistent
@EDG: EG07|STEP01|governs|USR07||persistent
@EDG: EG08|STEP01|governs|USR08||persistent
@EDG: EG09|STEP01|governs|USR09||persistent
@EDG: EG10|STEP01|governs|USR10||persistent
@EDG: EG10b|STEP01|governs|USR14||persistent
@EDG: EG54|STEP01|governs|USR11||persistent
@EDG: EG58|STEP01|governs|USR12||persistent
@EDG: EG62|STEP01|governs|USR13||persistent
@EDG: EG11|STEP01|governs|LAW-PIPE20||persistent
@EDG: EG11b|STEP01|governs|LAW-PIPE21||persistent
@EDG: EG12|STEP01|governs|LAW-MCP01||persistent
@EDG: EG13|STEP01|governs|LAW-G11||persistent
@EDG: EG14|STEP01|governs|LAW-HUD01||persistent
@EDG: EG15|STEP01|governs|LAW-NAME01||persistent
@EDG: EG16|STEP01|governs|LAW-G04||persistent
@EDG: EG17|STEP01|governs|LAW-G12||persistent
@EDG: EG18|STEP01|governs|T01||persistent
@EDG: EG19|T01|governs|LAW-G06||persistent
@EDG: EG20|T01|governs|LAW-G07||persistent
@EDG: EG21|T01|governs|LAW-G08||persistent
@EDG: EG22|SYS01|governs|LAW-G02||persistent
@EDG: EG23|SYS01|governs|LAW-G03||persistent
@EDG: EG24|B01|governs|LAW-G10||persistent
@EDG: EG25|P01|governs|LAW-G05||persistent
@EDG: EG26|USR05|governs|LAW-PROSE01||persistent
@EDG: EG27|USR05|governs|LAW-PROSE02||persistent
@EDG: EG28|USR01|governs|LAW-OUT04||persistent
@EDG: EG29|USR05|governs|LAW-PROSE03||persistent
@EDG: EG30|USR06|governs|LAW-CHR04||persistent
@EDG: EG31|P01|features|LAW-CHR01||persistent
@EDG: EG32|N01|features|LAW-CHR02||persistent
@EDG: EG33|N02|features|LAW-CHR03||persistent
@EDG: EG34|USR05|governs|LAW-PROSE04||persistent
@EDG: EG35|USR05|governs|LAW-PROSE05||persistent
@EDG: EG36|USR05|governs|LAW-PROSE06||persistent
@EDG: EG37|USR05|governs|LAW-PROSE07||persistent
@EDG: EG38|USR05|governs|LAW-PROSE08||persistent
@EDG: EG39|USR05|governs|LAW-PROSE09||persistent
@EDG: EG40|USR01|governs|LAW-OUT05||persistent
@EDG: EG41|USR07|governs|LAW-DATA01||persistent
@EDG: EG42|USR05|governs|LAW-PROSE10||persistent
@EDG: EG43|USR05|governs|LAW-PROSE11||persistent
@EDG: EG44|USR05|governs|LAW-PROSE12||persistent
@EDG: EG45|USR04|governs|LAW-PROSE12||persistent
@EDG: EG46|USR08|governs|LAW-OUT06||persistent
@EDG: EG47|USR05|governs|LAW-OLN02||persistent
@EDG: EG48|USR08|governs|LAW-OLN01||persistent
@EDG: EG49|USR05|governs|LAW-PROSE13||persistent
@EDG: EG50|USR09|governs|LAW-OUT07||persistent
@EDG: EG51|USR10|governs|LAW-PERS02||persistent
@EDG: EG52|P01|governs|LAW-PERS01||persistent
@EDG: EG53|USR05|governs|LAW-PERS03||persistent
@EDG: EG55|USR11|governs|LAW-NPC01||persistent
@EDG: EG56|N01|features|LAW-NPC01||persistent
@EDG: EG57|N02|features|LAW-NPC01||persistent
@EDG: EG59|USR12|governs|LAW-NPC02||persistent
@EDG: EG60|N01|features|LAW-NPC02||persistent
@EDG: EG61|N02|features|LAW-NPC02||persistent
@EDG: EG63|USR13|governs|LAW-NPC03||persistent
@EDG: EG64|N01|features|LAW-NPC03||persistent
@EDG: EG65|N02|features|LAW-NPC03||persistent
```

**Note:** `@EDG.relation` 存 ASCII；`attrs` 欄可存中文標籤（解鎖、待聘、產出…）。

## 雙階段 Pipeline（大綱 → 正文）

每個玩家選擇 = 一個 story beat，編排器**同一回合內**依 `@STEP.n` 執行：

| `STEP.n` | 階段 | MCP | 產出 |
|----------|------|-----|------|
| 1 | 讀圖 | `query_warm(STEP01)` | 狀態 + LAW |
| 2 | **寫大綱** | `add`/`update` `@OLN` | 落盤本拍大綱（禁文學修辭） |
| 3 | 讀大綱 | `query_warm(OLNxx)` | 大綱 + 相連 SCN/NPC |
| 4 | **寫正文** | 本地 `prose_count.py` → **`beat_turn_finish`**（一章節內 process 完成 gate+落盤） | 僅擴寫 OLN；適用 LAW-PROSE* |
| 5 | 呈現 | — | 【大綱】+【劇情】+【選項】+ HUD |
| 6 | 落盤 | （已併入 `beat_turn_finish`） | 圖更新；舊 OLN `delete_on_settle` |

```mermaid
flowchart LR
  A[玩家選擇] --> B["beat_turn_begin (1 MCP)"]
  B --> C["本地 prose_count 調稿 (0 MCP)"]
  C --> D["beat_turn_finish (1 MCP)"]
  D --> E[呈現玩家]
  E --> A
```

**分工：** `@OLN` = 劇情骨架（策劃層）；正文 = 文學層。正文不得偏離已落盤 OLN（LAW-OLN02）。`@OLN` 欄位用繁體中文短語，不用英文碼。

**LAW 撰寫原則：** `constraint` 欄只寫**通用原則與短碼**（或 `-`）；長說明僅留本 md。**禁寫死主角姓名**（LAW-NAME01）——姓名由開局玩家輸入，存 `@USR03` 與 `@PLR.玩家身份`。

**EDG + LAW 圖像化（LAW06，省 TOKEN）：**

- 種子含 `@LAW: LAW06|…|law_scope|linked_from_anchor` 時，`query_warm` **只帶入**與錨點子圖以 `governs`／`features` 相連的 `@LAW`，外加引擎列 `LAW01–05` 與 `constraint=*` 的全域列（如 `LAW-G01`、`LAW-G09`）。
- **分工：** `@USR`／`@NPC`／`@PLR` 存設定值；`@LAW` 存短碼（`mechanism`）；`@EDG governs`／`features` 宣告「誰受哪條規則管」——圖即索引，不重複長文。
- **接線：** `@STEP01` `governs` 全部 `@USR` 與管線／全域 `@LAW`；各 `@USR` 再 `governs` 對應 `LAW-PROSE*`／`LAW-OUT*`；場景內 `@P01`／`@N01` `features` 聲線 `@LAW`；`@SYS01`／`@B01`／`@T01` `governs` 各 `@LAW-G*`。
- 語意細節見下方 Runtime；**不在** `@LAW.constraint` 重複列舉。

**中文欄位與文風：** Tag map 用中文欄位名（名稱、身體狀態…）**不會**出現在 `query_warm` 輸出裡。可變欄位值用**繁體中文短碼**（例：`疲勞:1；黏土:三筐；主線:焦炭`），禁英文機器碼；正文仍須改寫成場景，不得逐字複誦（LAW-OUT05）。

**Runtime（敘事編排，非 wire 列）：**

- **雙階段（LAW-PIPE20）：** 每拍先 `@OLN` 大綱落盤，再依大綱寫正文；玩家可見【第一段本拍大綱】（USR08）
- **正文長度（LAW-PROSE03 / USR05）：** `beat_turn_begin` 取 band → 本地 `scripts/prose_count.py`（**0 MCP**）→ **一次** `beat_turn_finish`（gate+章節+圖+save 同 process）；**禁**迴圈 `prose_metrics`／`chapter_prose_gate`
- **管線（LAW-PIPE21）：** 每拍 **2 次 memnet MCP**（`beat_turn_begin` + `beat_turn_finish`）；**0 次 novel-writer MCP**
- **禁湊門檻（LAW-PROSE03 編排）：** 字數不足時**禁止**逐句補景（蟲鳴、河風、燈影、反覆內心獨白）硬湊下限。須回到 `@OLN` **加一個劇情單元**（多一輪對白、一個動作、NPC 反應、具體物件互動）後**整段重寫**，再量一次；合格後才 gate
- **語感（LAW-PROSE13 等）：** 寫前先自問「母語者會這樣說嗎」；人物聲線以 warm 中 `@NPC.特徵` 為準，LAW 不重複列舉台詞範例
- **個性（LAW-PERS01–03）：** `@TRT` 記主角四維累積（**力量／智力／魅力／氣運**）；正文與**選項文案**均不貼維度標籤（USR09 `hidden`）；`@OPT.維度` 僅落盤用，選後 `+1` 對應 `@TRT`；選項 5 產業帳不變
- **四維與 16 型（設計參考，非 wire 列）：** 維度借 MBTI 四二分法改寫為遊戲可讀特質——**力量**（S／扛活、忍耐、先動身）、**智力**（T／算計、工藝、問條件）、**魅力**（F／人情、姊妹、給台階）、**氣運**（N+P／賭、試路、武學奇招）。累積高者組合可隱含 16 型傾向（如智力+內斂→分析師型），**正文與 HUD 不報型號**，僅供編排自洽
- **開局命名：** `@USR03` 為 `未定` 時僅收玩家 2–4 字姓名，更新 `@PLR` 與 `@USR03` 後再進入正文；**不**在 `@LAW` 寫死姓名
- **NPC 物品（LAW-NPC03）：** `@NPC.物品` 存 `名稱:數量` 摘要；`@ITM`＋`carries` 原子列，得失須 `update`／`add` 同步。敘事用到道具時須對 warm 中 `@ITM`，禁無圖新增
- **NPC 技能（LAW-NPC02）：** `@NPC.技能` 存鍵值摘要（`名稱:品級` 以；分隔）；`@SKL` 原子列＋`has_skill` 接線，品級可獨立 `update`。寫到工活時依 warm 中 `@SKL`／技能欄，禁憑空拔高
- **NPC 人格（LAW-NPC01）：** `@PTY` 存 16 型代碼與短標籤（編排用，正文不報）；`@PRS` 存與主角同軸四維**基線**（0–5，非選項累積）；`N01|persona|…` 接線。對白依 warm 中 `@PRS`＋`@NPC.特徵`＋年齡，高基線軸主導口吻（沈芯偏魅力／智力；沈蘭偏氣運／魅力）
- **角色聲線（LAW-CHR01–04）：** 主角對白合 `@PLR` 年齡與魂穿；NPC 合 `@PRS`／`@PTY` 與特徵欄
- **對白節奏（LAW-PROSE06）：** 參考現代文學——間白承載場景與情緒；連續對話可不加動作標籤；僅在轉折、停頓、情緒變化處點綴神情或動作；禁「每句必附」式寫法
- 每回合：先演算並 **MCP 更新** DATABASE → 輸出【第二段劇情】→【第三段選項】+ HUD；**不在對話框顯示【核心數據引擎】全文**（LAW-OUT04）
