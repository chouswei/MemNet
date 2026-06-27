# 工匠傳奇 — Custom MemNet initial state (繁體)

`session_open` map + seed. MemNet 固定 `@LAW`/`@EDG` 欄位名為引擎格式（`@EDG` 含 **`at`**＝劇情發生時）；**值與其餘 tag 欄位標籤可用中文**。
`@EDG.relation` 須 ASCII（如 `qiuzhu`）；敘事層顯示為中文（求助）。**新增劇情 relation**（如 `speaks`／`unknows`）須寫入 snapshot `# relations` 的 `@REL:` 列，否則 `session_load` 拒絕。

**Thin layer：** 每拍 LLM 只信 `beat_turn_begin` → `warm_stdout`（圖 + 接線 `@LAW`）。**不用** Cursor `.mdc`；機械門檻由 `beat_pipeline.py`／`prose_count.py` 執行。本檔 `Opening seed` = SSOT（分 **Engine**／**World** 兩段 fence，bootstrap 依序合併）；`Integrator notes` 僅供人類維護 seed。

## Tag map

| 層 | Tags | 說明 |
|----|------|------|
| **引擎** | `@LAW` `@CFG` `@STEP` `@USR` `@GLO` | 管線、介面、敘事規則、玩家設定鍵、四維語意軸 |
| **引擎（每拍產物）** | `@OLN` `@SBD` `@SCR` `@OPT` | 大綱→分鏡→腳本→選項；開局不 seed |
| **背景** | `@SYS` `@PLR` `@BIZ` `@NPC` `@SKL` `@WUX` `@ART` `@MWU` `@ITM` `@TSK` `@TEC` `@PRD` `@LOC` `@SCN` `@TRT` `@PRS` `@PTY` `@LIB` | 時代、主角、產業、人物、匠藝／武學／秘笈譜／熟練度、開局場景 |
| **接線** | `@EDG` | `at`＝劇情發生時（`@SYS.時間`，`LAW-EDG01`）；`governs`／`features`＝引擎接線免填 `at`；其餘 relation＝劇情／經濟／人設 |

```text
@SYS: id|回合|時間|財政赤字|銀入|混亂|匯率
@PLR: id|玩家身份|出生年|財產|淨銀流|核心靈魂能力|身體狀態
@BIZ: id|名稱|類型|地點|現金|負債|收入|支出|回收
@NPC: id|名字|出生年|特徵|腐敗|工藝|技能|物品|資金缺口|狀態|回收
@SKL: id|角色|名稱|品級|回收
@WUX: id|角色|門類|品級|熟練|回收
@ART: id|名稱|門類|金庸梯|係數|出處|回收
@MWU: id|角色|武功|品級|熟練|回收
@ITM: id|角色|名稱|數量|回收
@TSK: id|目標|時限|狀態|回收
@TEC: id|名稱|領域|狀態|效果
@PRD: id|名稱|類型|成本|售價|狀態
@SCN: id|code|beat|recycle
@OLN: id|回合|情緒錨|情節要點|對白骨架|尾鉤|回收
@SBD: id|回合|鏡頭|畫面要點|感官細節|動作對白骨架|氛圍轉場|回收
@SCR: id|回合|鏡頭|動作描述|對白|內心旁白|音效氛圍|回收
@TRT: id|維度|累積|回收
@PRS: id|角色|維度|基線|回收
@PTY: id|角色|代碼|標籤|回收
@OPT: id|序|文案|維度|變化|回收
@LIB: id|錨點|主題|短碼|狀態|回收
@LOC: id|名稱|區域|回收
@STEP: id|n|focus|recycle
@USR: id|key|value|recycle
@CFG: id|作品|anchor|版本|備註
@GLO: id|維度|軸|語意|回收
```

**Fixed tag `@EDG`（引擎內建，勿寫入 `--map`）：**

```text
@EDG: id|src|relation|dist|at|attrs|recycle
```

| 欄 | 含義 |
|----|------|
| `at` | 劇情發生時；同 `@SYS.時間`（`YYYY-MM-DDTHH`）。`LAW-EDG01`：非接線 relation 的 `add` 須填；`beat_turn_finish` 可自動補空值 |
| `attrs` | 可選中文標籤（解鎖、待聘、產出…） |
| `recycle` | `persistent`／`delete_on_settle`／`失效刪` 等 |

## Seed layout

| 區塊 | 維護時機 | 內容 |
|------|----------|------|
| **Opening seed — Engine** | 改管線／語風／介面／LAW 時 | `@LAW` `@CFG` `@STEP` `@USR` `@GLO`；`EG*`／`ES*` 接線 |
| **Opening seed — World** | 改開局劇情／人物／產業／科技樹時 | `@SYS`～`@PTY` `@LIB` 實體；劇情 `@EDG`（`E*` `EP*` `EK*` `EI*` `EL*`） |

`scripts/novel_bootstrap.py` 依序合併兩段 fence → `session_open` + `add`。

## Opening seed — Engine

```text
@LAW: LAW-G01|解鎖|1|解除時代科技鎖、技能鎖與劇情人物行為鎖|*
@LAW: LAW-G02|資金計算|1|silver_tael|-
@LAW: LAW-G03|銀本位|1|sys_fx_rate|-
@LAW: LAW-G04|擬真規則|1|verify_facts|wanming_plausible;cite_usr26
@LAW: LAW-G05|靈魂圖書館|1|lib_on_query|-
@LAW: LAW-G06|科技圖譜演進|1|unlock_tec|unlock_tec;tec_chain;tec_prune
@LAW: LAW-G09|精確性維持|4|exact_names|*
@LAW: LAW-G10|垃圾回收|1|gc_recycle|-
@LAW: LAW-G11|演算順序|1|db_before_prose|-
@LAW: LAW-G12|時限|1|tsk_timer|-
@LAW: LAW-TIME01|SYS|on_turn|time_iso|YYYY-MM-DDTHH;no_regress
@LAW: LAW-EDG01|EDG|on_add|plot_at|cite_SYS_time;skip_wiring
@LAW: LAW-G13|*|on_add|era_fit|cite_sys01_wanming;cite_usr26
@LAW: LAW-G14|*|on_context|alt_world|wanming_hist;jinyong_wuxia_au
@LAW: LAW-DATA01|*|on_add|zh_hant_kv|-
@LAW: LAW06|*|on_context|law_scope|linked_from_anchor
@LAW: LAW-NAME00|LAW|on_add|no_plr_name|no_plr_name;era_name;wanming_social_rank
@LAW: LAW-PIPE20|STEP|on_turn|stage_fsm|beat_stage_usr23;one_wire_per_finish;no_bundle;cite_LAW-OLN02;cite_LAW-SBD02;cite_LAW-SCR02;cite_LAW-PROSE00
@LAW: LAW-PIPE21|STEP|on_turn|beat_turn|begin_finish_only
@LAW: LAW-PIPE22|STEP|on_turn|gate_retry|once_per_beat
@LAW: LAW-PIPE23|STEP|on_turn|auto_beat|vit03_no_opts;prose_finish_only
@LAW: LAW-BAN00|*|on_turn|no_loop|no_loop;no_manual;no_prose_before_finish_ok;gate_metrics;chapter_append;before_finish_ok
@LAW: LAW-MCP01|編排|1|圖與章節僅經MCP|-
@LAW: LAW-OLN01|OLN|on_add|outline_fmt|opening_scn;cite_usr70;smithy_gate;ban_orphan_shrine;hire_gate_e11;cite_b01
@LAW: LAW-OLN02|OLN|on_turn|prose_from_oln|-
@LAW: LAW-SBD01|SBD|on_add|sbd_fmt|visual_sensory_beat
@LAW: LAW-SBD02|SBD|on_turn|sbd_from_oln|expand_to_shots
@LAW: LAW-SCR01|SCR|on_add|script_fmt|action_dialogue_parenthetical
@LAW: LAW-SCR02|SCR|on_turn|script_from_sbd|tight_action_lines
@LAW: LAW-PROSE00|敘事|1|warm_prose|cite_usr51;usr19_20;usr24;usr25;prose_from_script;inner_voice_modern;age_fit_narrative;ref_金庸梁羽生;length_advisory;ban_telegraphic;wuxia_pacing;sensory_embed;chr_interaction;dialogue_flow;env_serve_plot;readable_prose;sentence_rhythm;metaphor_sparing;knowledge_plain;zh_idiom_fit
@LAW: LAW-WX00|*|on_turn|wuxia_cite|wuxia_cite;martial_resolve;exchange_resolve;neili_toll;opp_wux_rank;art_coeff;art_toll;mwx_gain;neigong_recover;soul_body_cap;cite_usr27-42;usr46-49
@LAW: LAW-CHR00|*|on_turn|plr_voice|plr_voice;npc_voice;npc_dialogue;trait_age_bind;prs_baseline;skl_cite;itm_cite;cite_usr18_usr19_usr24_usr25;cite_npc_traits_prs_pty;sys_minus_birth;no_tagline_no_clip;age_fit_addr;cite_law_tec01
@LAW: LAW-OUT00|介面|1|hide_database_in_chat|hide_database_in_chat;no_graph_echo;outline_section;trait_opt_tag;hud_pipe_single_line
@LAW: LAW-PERS00|*|on_turn|trait_build|trait_build;trait_opts;trait_delta;trait_check;stat_division;opt_readable_baihua;full_sentence;no_action_chain;cite_usr22;milestone_only;not_per_opt;trt_prs_wux_age_vs_dc;opt_axis_not_delta;mwx_primary_wx;trt_dc_or_margin;cite_usr42
@LAW: LAW-OPT00|*|on_turn|six_options|six_options;ind_ledger;lib_query;opt1_4_trait;opt5_ind;opt6_lib;cite_law_vit01;vit03_suspend;no_time_advance;reoffer_opts;cite_lib_tsk_tec;cite_LAW-LIB00;no_tech_tree_only
@LAW: LAW-LIB00|LIB|on_turn|lib_cite|lib_cite;lib_fmt;lib_context;cite_usr31;cite_glo_vocab_on_overlap;consciousness_frame;plain_route_table;anchor_last_oln;match_LIB
@LAW: LAW-TEC01|NPC|on_turn|npc_tec_vocab|cite_edg_unknows;npc_speaks_glo09
@LAW: LAW-VIT01|PLR|on_turn|body_in_plot|cite_usr45;oln_embed;prose_embed;opt_respect;finish_delta
@LAW: LAW-VIT02|PLR|on_context|vit_cap|cite_usr47_48;primary_art;age_wux;clamp_plr
@LAW: LAW-VIT03|PLR|on_turn|qi_zero|cite_usr50;collapse;auto_beat;no_opts;rescue_wake;no_permadeath

@CFG: CFG01|工匠傳奇|STEP01|1|晚明擬真金庸武俠架空

@STEP: STEP01|1|SCN01|persistent

@USR: USR01|output|prose_opts_hud_only|persistent
@USR: USR02|hud_pipe|qi_neili_wux_age_quest_partner_fin_ind_datetime_lib|persistent
@USR: USR03|pc_name|未定|persistent
@USR: USR04|skills|靈魂圖書館登峰造極|persistent
@USR: USR05|scene_length|no_gate|persistent
@USR: USR06|voice_sheet|chr01_n01_n02_trait_age|persistent
@USR: USR07|state_fmt|繁體鍵值；分隔|persistent
@USR: USR08|outline_visible|brief|persistent
@USR: USR09|opt_trait_tag|hidden|persistent
@USR: USR10|trait_dims|力量;智力;魅力;氣運|persistent
@USR: USR11|npc_persona|prs_pty|persistent
@USR: USR12|npc_skills|skl_rank|persistent
@USR: USR13|npc_items|itm_qty|persistent
@USR: USR14|chapter_out|novel-output/shenjia_caifa/chapters|persistent
@USR: USR15|snapshot|novel-output/shenjia_caifa/session_snap.json|persistent
@USR: USR16|local_gate|prose_count.py|persistent
@USR: USR17|gate_retry|once|persistent
@USR: USR18|narration|第二人稱你|persistent
@USR: USR19|prose_style|優美白話武俠|persistent
@USR: USR20|prose_ref|金庸武俠架空;金庸白描;梁羽生情景;忌網文快剪|persistent
@USR: USR21|prose_target|800_zh_advisory|persistent
@USR: USR22|opt_copy|可讀白話完整句;12-28字;禁動詞串;禁梗概體|persistent
@USR: USR23|beat_stage|oln|persistent
@USR: USR24|inner_voice|modern_taiwanese_baihua|persistent
@USR: USR25|age_calc|sys01_minus_birth_year|persistent
@USR: USR26|world_layer|wanming_hist_jinyong_wuxia_au|persistent
@USR: USR27|wuxia_dims|內功;武學;輕功|persistent
@USR: USR28|wuxia_ranks|未入門;初学乍練;熟能生巧;略有小成;駕輕就熟;登峰造極|persistent
@USR: USR29|wuxia_resolve|effective_min_mwu_wux_age_neili|persistent
@USR: USR30|opt_layout|1-4四維;5產業帳;6圖書館|persistent
@USR: USR31|lib_anchor|last_oln_match_LIB;then_TSK;then_TEC;fallback_LIB01|persistent
@USR: USR31b|lib_match_keys|風箱;皮墊;漏風;聽聲;塊子;炭;帳;武學|persistent
@USR: USR31c|lib_glo_ids|GLO09|persistent
@USR: USR32|lib_opt_copy|閉目入殿查閱|persistent
@USR: USR33|trait_gain|milestone;training;chapter_close|persistent
@USR: USR34|trait_check|trt_vs_situational_dc;opt1_4_axis_only|persistent
@USR: USR35|combat_mode|試招;過招;實戰;追殺;群戰|persistent
@USR: USR36|exchange_outcome|>=3碾勝;1-2小勝;0平手;-1-2小負;<=-3慘敗|persistent
@USR: USR37|exchange_mod|內功;輕功;四維;狀態;兵刃;地形;偷襲;人數|persistent
@USR: USR38|art_tier|三流;二流;一流;超一流;絕頂|persistent
@USR: USR39|art_k_band|0.75-0.85;0.90-1.05;1.05-1.35;1.40-1.85;1.80-2.00|persistent
@USR: USR40|art_special|六脈高內耗;獨孤破招;凌波僅輕功;太玄綜合;太玄調息回氣;cite_usr49_burn|persistent
@USR: USR41|mwx_gain|milestone;training;chapter_close;魂穿開局初学乍練|persistent
@USR: USR42|stat_division|mwx_primary_combat;trt_vs_dc_general;trt_margin_only_wx05;mwx_not_dc;trt_not_eff_idx|persistent
@USR: USR43|game_time|axis=iso;display=chongzhen_shichen;era_base=1628;era_name=崇禎|persistent
@USR: USR44|locked_tec_vocab|TEC01;PRD01;TEC02;PRD02|persistent
@USR: USR45|body_plot|氣血;內力;疲勞;飽食;oln;prose;opt;delta|persistent
@USR: USR46|neigong_recover|未定;未定;WUX01;半時辰一輪|persistent
@USR: USR47|vit_cap|qi=age_wux;neili=primary_art_bands;fmt=cur/max|persistent
@USR: USR48|primary_neigong|未定|persistent
@USR: USR49|art_neili_burn|ART01:1;ART02:1;ART03:2;ART04:1;ART10:1;ART14:1;ART15:1|persistent
@USR: USR50|qi_zero|0=昏厥;no_opts;auto_beat;wake_min=1;wx_ban|persistent
@USR: USR51|prose_warm|你;旁白優美白話武俠;金庸白描梁羽生情景;內心台灣白話;先環境後人物;感官嵌入;起承轉合;禁梗概禁快剪;cite_usr25;body_fit_age|persistent
@USR: USR53|pc_gender|未定|persistent
@USR: USR58|opening_arts|未定;未定;未定|persistent
@USR: USR60|setup_scene_neigong|氣海長廊;內息如河，經卷虛懸|persistent
@USR: USR61|setup_scene_martial|試招石台;幻影過招，一招定路|persistent
@USR: USR62|setup_scene_qinggong|身法雲橋;足尖掠風，避劫一念|persistent
@USR: USR63|setup_tone|god_banter;過勞吐槽;台灣口語;神賤萌;禁肅穆史詩|persistent
@USR: USR64|setup_god_line_open|再熬夜啊～死了齁？|persistent
@USR: USR65|setup_god_line_profile|嘖，又一位。報到：姓名、性別。快點，後面還在排。|persistent
@USR: USR66|setup_god_line_transmigrate|好，穿吧——別又加班死在工位上啊。|persistent
@USR: USR67|martial_catalog_md|application-notes/novel-shenjia-martial-catalog.md|persistent
@USR: USR69|catalog_schema|applications/novel_cursor/catalog_specs/wuxia_jinyong.json|persistent
@USR: USR70|opening_scene|SCN01=smithy_gate；沈家鐵坊B01門前甦醒；沈芯經營沈蘭協助；匠戶孤女繼承鐵坊非破廟流浪；炭灰=做工打扮；E11待聘小工；負債2兩|persistent
@USR: USR52|stage_hint_lib|【靈魂圖書館檢閱】須對準本拍OLN主題；cite匹配LIB；連結GLO09匠話；禁無故全列TEC|persistent
@USR: USR54|stage_hint_oln|【階1·大綱】寫@OLN：情緒錨、情節要點、對白骨架、尾鉤、體征代價；cite_USR70開局；SCN01未結算禁破廟孤女討生活；禁章節正文；finish僅oln_lines|persistent
@USR: USR55|stage_hint_sbd|【階2·分鏡】讀本拍最新@OLN；拆≥2鏡@SBD；禁正文；finish僅sbd_lines|persistent
@USR: USR56|stage_hint_scr|【階3·腳本】讀本拍@SBD；逐鏡寫@SCR；禁章節正文；finish僅scr_lines|persistent
@USR: USR57|stage_hint_prose|【階4·小說】讀本拍@SCR擴寫；~USR21字；finish含prose+OPT+STEP+SYS+PLR；beat_stage→oln|persistent

@GLO: GLO01|力量|S|扛活;忍耐;先動身|persistent
@GLO: GLO02|智力|T|算計;工藝;問條件|persistent
@GLO: GLO03|魅力|F|人情;姊妹;給台階|persistent
@GLO: GLO04|氣運|N+P|賭;試路;武學奇招|persistent
@GLO: GLO05|內功|N|運氣;護體;回氣;太玄調息|persistent
@GLO: GLO06|武學|S+T|拆招;兵刃;近身|persistent
@GLO: GLO07|輕功|N+S|身法;躍避;追趕|persistent
@GLO: GLO08|圖書館|T|查閱;解析;路線|persistent
@GLO: GLO09|匠話|土法炭火|堅炭;燒透;塊子;成料;聽聲;塊煤;悶火;煙色;磚縫|persistent

@EDG: EG01|STEP01|governs|USR01||persistent
@EDG: EG02|STEP01|governs|USR02||persistent
@EDG: EG03|STEP01|governs|USR03||persistent
@EDG: EG04|STEP01|governs|USR04||persistent
@EDG: EG05|STEP01|governs|USR05||persistent
@EDG: EG06|STEP01|governs|USR06||persistent
@EDG: EG07|STEP01|governs|USR07||persistent
@EDG: EG08|STEP01|governs|USR08||persistent
@EDG: EG09|STEP01|governs|USR09||persistent
@EDG: EG100|STEP01|governs|LAW-SBD02||persistent
@EDG: EG101|STEP01|governs|LAW-SCR01||persistent
@EDG: EG102|STEP01|governs|LAW-SCR02||persistent
@EDG: EG104|STEP01|governs|USR24||persistent
@EDG: EG105|USR24|governs|LAW-CHR00||persistent
@EDG: EG107|USR24|governs|LAW-PROSE00||persistent
@EDG: EG108|STEP01|governs|USR25||persistent
@EDG: EG109|USR25|governs|LAW-CHR00||persistent
@EDG: EG110|USR25|governs|LAW-PROSE00||persistent
@EDG: EG112|USR25|governs|LAW-CHR00||persistent
@EDG: EG113|STEP01|governs|USR26||persistent
@EDG: EG114|USR26|governs|LAW-G04||persistent
@EDG: EG115|USR26|governs|LAW-G13||persistent
@EDG: EG116|USR26|governs|LAW-G14||persistent
@EDG: EG117|STEP01|governs|LAW-G14||persistent
@EDG: EG118|STEP01|governs|USR27||persistent
@EDG: EG119|STEP01|governs|USR28||persistent
@EDG: EG120|STEP01|governs|USR29||persistent
@EDG: EG121|USR27|governs|GLO05||persistent
@EDG: EG122|USR27|governs|GLO06||persistent
@EDG: EG123|USR27|governs|GLO07||persistent
@EDG: EG124|USR26|governs|LAW-WX00||persistent
@EDG: EG125|USR26|governs|LAW-WX00||persistent
@EDG: EG126|USR26|governs|LAW-WX00||persistent
@EDG: EG127|USR26|governs|LAW-WX00||persistent
@EDG: EG128|STEP01|governs|LAW-WX00||persistent
@EDG: EG129|USR29|governs|LAW-WX00||persistent
@EDG: EG130|USR29|governs|LAW-WX00||persistent
@EDG: EG131|P01|governs|LAW-WX00||persistent
@EDG: EG132|USR04|governs|LAW-WX00||persistent
@EDG: EG133|USR28|governs|LAW-WX00||persistent
@EDG: EG134|STEP01|governs|USR30||persistent
@EDG: EG135|USR30|governs|LAW-OPT00||persistent
@EDG: EG136|STEP01|governs|LAW-OPT00||persistent
@EDG: EG137|STEP01|governs|LAW-OPT00||persistent
@EDG: EG138|STEP01|governs|LAW-OPT00||persistent
@EDG: EG139|STEP01|governs|LAW-LIB00||persistent
@EDG: EG140|STEP01|governs|LAW-LIB00||persistent
@EDG: EG141|USR31|governs|LAW-LIB00||persistent
@EDG: EG142|USR04|governs|LAW-LIB00||persistent
@EDG: EG143|USR30|governs|GLO08||persistent
@EDG: EG144|LAW-G05|governs|LAW-LIB00||persistent
@EDG: EG145|LAW-G05|governs|LAW-OPT00||persistent
@EDG: EG146|USR32|governs|LAW-PERS00||persistent
@EDG: EG147|USR33|governs|LAW-PERS00||persistent
@EDG: EG148|USR34|governs|LAW-PERS00||persistent
@EDG: EG149|STEP01|governs|LAW-PERS00||persistent
@EDG: EG150|USR34|governs|LAW-WX00||persistent
@EDG: EG151|STEP01|governs|LAW-WX00||persistent
@EDG: EG152|USR26|governs|LAW-WX00||persistent
@EDG: EG153|USR29|governs|LAW-WX00||persistent
@EDG: EG154|USR35|governs|LAW-WX00||persistent
@EDG: EG155|USR36|governs|LAW-WX00||persistent
@EDG: EG156|USR37|governs|LAW-WX00||persistent
@EDG: EG157|USR28|governs|LAW-WX00||persistent
@EDG: EG158|LAW-WX00|governs|LAW-WX00||persistent
@EDG: EG159|STEP01|governs|LAW-WX00||persistent
@EDG: EG160|USR35|governs|LAW-WX00||persistent
@EDG: EG161|USR28|governs|LAW-WX00||persistent
@EDG: EG162|STEP01|governs|LAW-WX00||persistent
@EDG: EG163|LAW-CHR00|governs|LAW-WX00||persistent
@EDG: EG164|USR34|governs|LAW-WX00||persistent
@EDG: EG165|STEP01|governs|LAW-WX00||persistent
@EDG: EG166|USR26|governs|LAW-WX00||persistent
@EDG: EG167|USR38|governs|LAW-WX00||persistent
@EDG: EG168|USR39|governs|LAW-WX00||persistent
@EDG: EG169|LAW-WX00|governs|LAW-WX00||persistent
@EDG: EG170|LAW-WX00|governs|LAW-WX00||persistent
@EDG: EG171|USR40|governs|LAW-WX00||persistent
@EDG: EG172|STEP01|governs|LAW-WX00||persistent
@EDG: EG173|LAW-WX00|governs|LAW-WX00||persistent
@EDG: EG174|USR04|governs|LAW-WX00||persistent
@EDG: EG175|STEP01|governs|LAW-WX00||persistent
@EDG: EG176|USR41|governs|LAW-WX00||persistent
@EDG: EG177|USR41|governs|LAW-WX00||persistent
@EDG: EG178|USR28|governs|LAW-WX00||persistent
@EDG: EG179|LAW-WX00|governs|LAW-PERS00||persistent
@EDG: EG180|STEP01|governs|LAW-PERS00||persistent
@EDG: EG181|USR42|governs|LAW-PERS00||persistent
@EDG: EG182|USR42|governs|LAW-WX00||persistent
@EDG: EG183|USR42|governs|LAW-PERS00||persistent
@EDG: EG184|USR41|governs|LAW-PERS00||persistent
@EDG: EG185|USR33|governs|LAW-PERS00||persistent
@EDG: EG186|STEP01|governs|LAW-TIME01||persistent
@EDG: EG187|USR43|governs|LAW-TIME01||persistent
@EDG: EG188|STEP01|governs|LAW-TEC01||persistent
@EDG: EG189|USR44|governs|LAW-TEC01||persistent
@EDG: EG190|USR44|governs|GLO09||persistent
@EDG: EG191|LAW-TEC01|governs|LAW-CHR00||persistent
@EDG: EG192|GLO09|governs|LAW-CHR00||persistent
@EDG: EG193|STEP01|governs|LAW-VIT01||persistent
@EDG: EG194|USR45|governs|LAW-VIT01||persistent
@EDG: EG195|P01|governs|LAW-VIT01||persistent
@EDG: EG196|LAW-VIT01|governs|LAW-OLN02||persistent
@EDG: EG197|LAW-VIT01|governs|LAW-PERS00||persistent
@EDG: EG198|LAW-VIT01|governs|LAW-WX00||persistent
@EDG: EG199|LAW-VIT01|governs|LAW-WX00||persistent
@EDG: EG200|LAW-VIT01|governs|LAW-OPT00||persistent
@EDG: EG201|LAW-VIT01|governs|LAW-PROSE00||persistent
@EDG: EG202|STEP01|governs|LAW-WX00||persistent
@EDG: EG203|USR46|governs|LAW-WX00||persistent
@EDG: EG206|P01|governs|LAW-WX00||persistent
@EDG: EG207|LAW-WX00|governs|LAW-VIT01||persistent
@EDG: EG208|USR40|governs|LAW-WX00||persistent
@EDG: EG209|STEP01|governs|LAW-VIT02||persistent
@EDG: EG210|USR47|governs|LAW-VIT02||persistent
@EDG: EG211|USR48|governs|LAW-VIT02||persistent
@EDG: EG212|USR49|governs|LAW-WX00||persistent
@EDG: EG213|LAW-VIT02|governs|LAW-VIT01||persistent
@EDG: EG214|LAW-VIT02|governs|LAW-WX00||persistent
@EDG: EG215|STEP01|governs|LAW-VIT03||persistent
@EDG: EG216|USR50|governs|LAW-VIT03||persistent
@EDG: EG217|LAW-VIT03|governs|LAW-VIT01||persistent
@EDG: EG218|LAW-VIT03|governs|LAW-OPT00||persistent
@EDG: EG219|LAW-VIT03|governs|LAW-WX00||persistent
@EDG: EG220|LAW-VIT03|governs|LAW-WX00||persistent
@EDG: EG221|STEP01|governs|LAW-PIPE23||persistent
@EDG: EG222|LAW-VIT03|governs|LAW-PIPE23||persistent
@EDG: EG10b|STEP01|governs|USR14||persistent
@EDG: EG10|STEP01|governs|USR10||persistent
@EDG: EG11b|STEP01|governs|LAW-PIPE21||persistent
@EDG: EG11|STEP01|governs|LAW-PIPE20||persistent
@EDG: EG12|STEP01|governs|LAW-MCP01||persistent
@EDG: EG13|STEP01|governs|LAW-G11||persistent
@EDG: EG14|STEP01|governs|LAW-OUT00||persistent
@EDG: EG15|STEP01|governs|LAW-NAME00||persistent
@EDG: EG16|STEP01|governs|LAW-G04||persistent
@EDG: EG17|STEP01|governs|LAW-G12||persistent
@EDG: EG18|STEP01|governs|T01||persistent
@EDG: EG19|T01|governs|LAW-G06||persistent
@EDG: EG20|T01|governs|LAW-G06||persistent
@EDG: EG21|T01|governs|LAW-G06||persistent
@EDG: EG22|SYS01|governs|LAW-G02||persistent
@EDG: EG23|SYS01|governs|LAW-G03||persistent
@EDG: EG24|B01|governs|LAW-G10||persistent
@EDG: EG25|P01|governs|LAW-G05||persistent
@EDG: EG28|USR01|governs|LAW-OUT00||persistent
@EDG: EG30|USR06|governs|LAW-CHR00||persistent
@EDG: EG31|P01|features|LAW-CHR00||persistent
@EDG: EG32|N01|features|LAW-CHR00||persistent
@EDG: EG33|N02|features|LAW-CHR00||persistent
@EDG: EG40|USR01|governs|LAW-OUT00||persistent
@EDG: EG41|USR07|governs|LAW-DATA01||persistent
@EDG: EG45|USR04|governs|LAW-PROSE00||persistent
@EDG: EG46|USR08|governs|LAW-OUT00||persistent
@EDG: EG48|USR08|governs|LAW-OLN01||persistent
@EDG: EG50|USR09|governs|LAW-OUT00||persistent
@EDG: EG51|USR10|governs|LAW-PERS00||persistent
@EDG: EG52|P01|governs|LAW-PERS00||persistent
@EDG: EG54|STEP01|governs|USR11||persistent
@EDG: EG55|USR11|governs|LAW-CHR00||persistent
@EDG: EG56|N01|features|LAW-CHR00||persistent
@EDG: EG57|N02|features|LAW-CHR00||persistent
@EDG: EG58|STEP01|governs|USR12||persistent
@EDG: EG59|USR12|governs|LAW-CHR00||persistent
@EDG: EG60|N01|features|LAW-CHR00||persistent
@EDG: EG61|N02|features|LAW-CHR00||persistent
@EDG: EG62|STEP01|governs|USR13||persistent
@EDG: EG63|USR13|governs|LAW-CHR00||persistent
@EDG: EG64|N01|features|LAW-CHR00||persistent
@EDG: EG65|N02|features|LAW-CHR00||persistent
@EDG: EG66|STEP01|governs|LAW-BAN00||persistent
@EDG: EG67|STEP01|governs|LAW-BAN00||persistent
@EDG: EG68|STEP01|governs|LAW-BAN00||persistent
@EDG: EG69|STEP01|governs|LAW-PIPE22||persistent
@EDG: EG70|STEP01|governs|USR15||persistent
@EDG: EG71|STEP01|governs|USR16||persistent
@EDG: EG72|STEP01|governs|USR17||persistent
@EDG: EG73|STEP01|governs|CFG01||persistent
@EDG: EG74|USR10|governs|GLO01||persistent
@EDG: EG75|USR10|governs|GLO02||persistent
@EDG: EG76|USR10|governs|GLO03||persistent
@EDG: EG77|USR10|governs|GLO04||persistent
@EDG: EG78|SYS01|governs|LAW-G13||persistent
@EDG: EG79|STEP01|governs|LAW-G13||persistent
@EDG: EG80|SYS01|governs|LAW-NAME00||persistent
@EDG: EG81|STEP01|governs|LAW-NAME00||persistent
@EDG: EG82|STEP01|governs|USR18||persistent
@EDG: EG83|STEP01|governs|USR19||persistent
@EDG: EG84|STEP01|governs|USR20||persistent
@EDG: EG89|STEP01|governs|USR21||persistent
@EDG: EG90|USR21|governs|LAW-PROSE00||persistent
@EDG: EG91|STEP01|governs|USR22||persistent
@EDG: EG92|USR22|governs|LAW-PERS00||persistent
@EDG: EG93|STEP01|governs|USR23||persistent
@EDG: EG94|USR23|governs|LAW-SBD01||persistent
@EDG: EG95|USR23|governs|LAW-SBD02||persistent
@EDG: EG96|USR23|governs|LAW-SCR01||persistent
@EDG: EG97|USR23|governs|LAW-SCR02||persistent
@EDG: EG98|USR23|governs|LAW-PROSE00||persistent
@EDG: EG99|STEP01|governs|LAW-SBD01||persistent
@EDG: EG250|STEP01|governs|USR51||persistent
@EDG: EG251|USR51|governs|LAW-PROSE00||persistent
@EDG: EG252|USR19|governs|LAW-PROSE00||persistent
@EDG: EG253|USR20|governs|LAW-PROSE00||persistent
@EDG: EG254|USR18|governs|LAW-PROSE00||persistent
@EDG: EG255|USR21|governs|LAW-PROSE00||persistent
@EDG: EG256|USR23|governs|LAW-OLN02||persistent
@EDG: EG257|STEP01|governs|LAW-OPT00||persistent
@EDG: EG258|USR31|governs|LAW-OPT00||persistent
@EDG: EG259|USR31b|governs|LAW-OPT00||persistent
@EDG: EG260|LAW-OPT00|governs|LAW-LIB00||persistent
@EDG: EG261|LAW-OPT00|governs|LAW-OPT00||persistent
@EDG: EG262|STEP01|governs|USR52||persistent
@EDG: EG263|USR52|governs|LAW-LIB00||persistent
@EDG: EG264|USR52|governs|LAW-OPT00||persistent
@EDG: EG265|STEP01|governs|USR31b||persistent
@EDG: EG266|USR31c|governs|LAW-LIB00||persistent
@EDG: EG267|STEP01|governs|USR31c||persistent
@EDG: EG268|STEP01|governs|USR54||persistent
@EDG: EG269|STEP01|governs|USR55||persistent
@EDG: EG270|STEP01|governs|USR56||persistent
@EDG: EG271|STEP01|governs|USR57||persistent
@EDG: EG272|STEP01|governs|LAW-EDG01||persistent
@EDG: EG273|LAW-TIME01|governs|LAW-EDG01||persistent
@EDG: EG274|STEP01|governs|USR53||persistent
@EDG: EG275|STEP01|governs|USR58||persistent
@EDG: EG276|STEP01|governs|USR60||persistent
@EDG: EG277|STEP01|governs|USR61||persistent
@EDG: EG278|STEP01|governs|USR62||persistent
@EDG: EG279|STEP01|governs|USR63||persistent
@EDG: EG280|USR63|governs|USR64||persistent
@EDG: EG281|USR63|governs|USR65||persistent
@EDG: EG282|STEP01|governs|USR67||persistent
@EDG: EG283|STEP01|governs|USR69||persistent
@EDG: EG284|STEP01|governs|USR70||persistent
@EDG: EG285|STEP01|governs|LAW-OLN01||persistent
@EDG: EG286|USR70|governs|LAW-OLN01||persistent
@EDG: EG287|B01|features|LAW-OLN01||persistent
@EDG: EG288|B01|features|USR70||persistent
@EDG: EG289|N01|features|LAW-OLN01||persistent
@EDG: EG290|N02|features|LAW-OLN01||persistent
@EDG: EG291|N01|features|USR70||persistent
@EDG: EG292|N02|features|USR70||persistent
@EDG: EG293|SCN01|features|LAW-OLN01||delete_on_settle
@EDG: EG294|SCN01|features|USR70||delete_on_settle
@EDG: ES01|STEP01|focus|SCN01||persistent
```

## Opening seed — World

```text
@SYS: SYS01|1|1637-09-01T06|0|0|25|1兩=825文銅

@PLR: P01|流民乞丐|1627|0|0|靈魂圖書館登峰造極|氣血:6/6；內力:0/4；內功:未入門；武學:未入門；輕功:未入門；飽食:略飽；疲勞:0；魂穿:21世紀台灣工程師;過勞死入神域；性別:未定；靈魂圖書館:意識深處知識殿堂

@BIZ: B01|沈家鐵坊|鐵匠鋪|江南河畔|0|2|0|0|常駐

@NPC: N01|沈芯|1625|女、美貌、滿臉炭灰、匠戶孤女、繼承經營沈家鐵坊、聰慧、堅韌、溫柔、慾念、僅土法|0|土法|打鐵:略有小成；看火:熟能生巧；識鐵:略有小成|鐵鉗:1；護手布:1；木勺:1|0|需小工|常駐
@NPC: N02|沈蘭|1627|女、美貌、滿臉炭灰、匠戶孤女、協助鐵坊、狡黠、大膽、開放|0|土法|打鐵:初学乍練；燒火:初学乍練；跑腿:熟能生巧|油燈:1；布兜:1|0|需小工|常駐

@TSK: T01|升級作坊|-1|進行|完成結算後刪

@TEC: TEC01|焦炭製作|熱力冶金|鎖定|產量+300%;解鎖=驗料入庫+沈芯認可
@TEC: TEC02|焦炭煉鐵高爐|熱力冶金|鎖定|產量+300%;前置=TEC01解鎖

@LIB: LIB01|T01|升級作坊|upgrade_route|可查|常駐
@LIB: LIB02|TEC01|焦炭製作|coke_step1|鎖定|常駐
@LIB: LIB03|TEC02|焦炭煉鐵高爐|coke_blast_step2|鎖定|常駐
@LIB: LIB04|smithy_ops|風箱皮墊|bellows_leather|可查|常駐
@LIB: LIB05|smithy_ops|聽聲看火|furnace_listen|可查|常駐
@LIB: LIB06|smithy_ops|炭堆防潮|coal_store|可查|常駐

@PRD: PRD01|焦炭|物資|0|0|未量產;圖內專名
@PRD: PRD02|工業級生鐵|物資|0|0|未量產;圖內專名

@LOC: SUS01|蘇松|商路|常駐

@EDG: E01|N01|qiuzhu|P01|1637-09-01T06|解鎖|失效刪
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

@EDG: EN01|N01|speaks|GLO09|匠话|persistent
@EDG: EN02|N02|speaks|GLO09|匠话|persistent
@EDG: EN10|N01|unknows|TEC01|鎖定|persistent
@EDG: EN11|N01|unknows|PRD01|鎖定|persistent
@EDG: EN12|N02|unknows|TEC01|鎖定|persistent
@EDG: EN20|P01|knows_via|LIB02|圖書館|persistent
@EDG: EN21|P01|drives|T01|試窯|persistent

@EDG: EL01|P01|features|LIB01||persistent
@EDG: EL02|P01|features|LIB02||persistent
@EDG: EL03|P01|features|LIB03||persistent
@EDG: EL04|LIB01|cite|T01||persistent
@EDG: EL05|LIB01|cite|TEC01||persistent
@EDG: EL06|LIB01|cite|TEC02||persistent
@EDG: EL07|T01|features|LIB01||persistent
@EDG: EL08|TEC01|features|LIB02||persistent
@EDG: EL09|TEC02|features|LIB03||persistent
@EDG: EL10|LIB01|cite|LIB04||persistent
@EDG: EL11|LIB01|cite|LIB05||persistent
@EDG: EL12|LIB01|cite|LIB06||persistent
@EDG: EL13|LIB04|cite|GLO09||persistent
@EDG: EL14|P01|features|LIB04||persistent
@EDG: EL15|P01|features|LIB05||persistent

@SCN: SCN01|smithy_gate|awakening|delete_on_settle

@EDG: E20|SCN01|features|P01||delete_on_settle
@EDG: E21|SCN01|features|N01||delete_on_settle
@EDG: E22|SCN01|features|N02||delete_on_settle
@EDG: E23|SCN01|features|B01||delete_on_settle
@EDG: E24|SCN01|set_in|SYS01||delete_on_settle

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
@SKL: SK02|N01|看火|熟能生巧|常駐
@SKL: SK03|N01|識鐵|略有小成|常駐
@SKL: SK04|N02|打鐵|初学乍練|常駐
@SKL: SK05|N02|燒火|初学乍練|常駐
@SKL: SK06|N02|跑腿|熟能生巧|常駐




@EDG: EK01|N01|has_skill|SK01||persistent
@EDG: EK02|N01|has_skill|SK02||persistent
@EDG: EK03|N01|has_skill|SK03||persistent
@EDG: EK04|N02|has_skill|SK04||persistent
@EDG: EK05|N02|has_skill|SK05||persistent
@EDG: EK06|N02|has_skill|SK06||persistent



@EDG: EW01|P01|has_wux|WUX01||persistent
@EDG: EW02|P01|has_wux|WUX02||persistent
@EDG: EW03|P01|has_wux|WUX03||persistent

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
```

**Note:** `@EDG.relation` 存 ASCII；**`at` 欄**存劇情發生時的 `@SYS.時間`（`YYYY-MM-DDTHH`，見 `LAW-EDG01`／`LAW-TIME01`）；`attrs` 欄可存中文標籤（解鎖、待聘、產出…）。接線 relation（`governs`／`features`／`set_in`…）免填 `at`。

## Thin layer 契約（每拍進 warm，不用 mdc）

```mermaid
flowchart LR
  A[玩家選擇] --> B["beat_turn_begin → warm_stdout"]
  B --> C["本地撰寫正文 0 MCP"]
  C --> D["beat_turn_finish 1 MCP"]
  D --> E[呈現玩家]
  E --> A
```

| 層 | 職責 | 範例 |
|----|------|------|
| **圖（thin）** | 每拍 `query_warm(STEP01)` 可執行契約 | `@LAW` 短碼、`@USR` 路徑、`@GLO` 四維語意、`@STEP` |
| **程式（thick）** | 機械強制、不可只靠 LLM 記憶 | `beat_pipeline` 2 MCP；`no_gate` 時略過 `prose_count.py` |
| **本 md（integrator）** | 開局 `session_open`、維護 seed | Tag map + Opening seed；下方 Integrator notes |

**每拍編排（全在 seed，經 `STEP01` governs 進 warm）：**

| 短碼 | 含義 |
|------|------|
| `LAW-PIPE20` | **USR23 狀態機**：oln→sbd→scr→prose；`no_bundle`＝每 finish 僅一種 wire |
| `LAW-PIPE21` | begin/finish；嚴格模式下每劇情拍 4 輪 begin/finish（僅 prose 階對玩家呈現） |
| `LAW-PIPE22` | gate 失敗（僅最終 prose）整段重寫 |
| `LAW-PIPE23` + `LAW-VIT03` | **昏厥自動拍**：氣血 **0**／`昏厥:是` 時禁六選項，直接敘事 → finish |
| `LAW-PROSE00` | length_advisory（已取消硬性字數確認） |
| `USR05` | scene_length|no_gate （不再強制 min/max gate） |
| `USR21` | prose_target 僅供參考，無 gate |
| `USR23` + `USR54–57` | **beat_stage FSM** + 各階 `stage_hint_*`；僅 prose 階寫章節／六選項／推 `STEP.n` |
| `LAW-BAN00–03` | 禁 loop gate／手寫章節／finish 前當作已落盤 |
| `LAW-G13` + `cite_sys01_wanming` | **新增** NPC／物／技／地須依 `@SYS01` 晚明背景；禁跳時代 |
| `USR26` + `LAW-G14` | **世界觀**：晚明史實擬真後架空於金庸武俠宇宙（行政經濟遵晚明；武學江湖遵金庸式規則） |
| `USR27–29` + `LAW-WX00–10` | **武學判定**：三維＋**`@MWU` 各招熟練度**；`@ART` 金庸梯係數；過招＝cap×k vs 對手 |
| `USR41` + `@MWU` + `LAW-WX00` | **熟練度**：魂穿開局皆**初学乍練**；僅里程碑升級；靈魂圖書館不算武功 |
| `USR38–40` + `@ART` | **秘笈譜**：各武功強弱係數參照金庸；六脈高內耗、獨孤破招、凌波僅輕功等特例 |
| `USR35–37` + `LAW-WX00–07` | **交手模式**；margin 輸贏帶；對手品級；氣血內力疲勞代價 |
| `USR33–34` + `LAW-PERS00–05` | **四維不每拍+1**；選1–4＝敘事軸；一般＝TRT vs DC；**禁 TRT 進 eff_idx** |
| `USR42` + `LAW-PERS00` | **熟練度 vs 四維分工**：MWU 主戰力／過招；TRT 一般 DC 或交手 margin±1；MWU 不進 DC |
| `USR30–32` + `LAW-OPT00/03` + `LAW-LIB00–03` | **六選項**：槽6圖書館查閱；不推進時間；**對準最新 @OLN** |
| `USR31` + `USR31b` + `USR31c` + `LAW-OPT00` | **圖書館錨定**：`last_oln_match_LIB`；`USR31c` 指定匹配的 GLO 列 |
| `USR52` + `LAW-LIB00–03` | **圖書館 stage hint**；`beat_turn_begin(lib_query=true)` → `presentation.library_contracts` |
| `@GLO05–07` | 武學三維語意軸（經 `USR27` governs 進 warm） |
| `@GLO08` | 圖書館槽語意（經 `USR30` governs 進 warm） |
| `LAW-G04` + `USR26` | 史事人物先擬真考據，再允許劇情架空偏離 |
| `LAW-NAME00` + `wanming_social_rank` | **新增 NPC 人名**須合晚明身分階層（姓名字排行稱謂宜江南崇禎） |
| `USR15`/`USR16` | snapshot 路徑、本地 gate 腳本名 |
| `USR18`/`USR19`/`USR20` | 敘事視角、語體、參照（`STEP01`→`USR51`→`LAW-PROSE00`；`USR19`→`LAW-PROSE00`） |
| `USR51` + `LAW-PROSE00` | **warm 敘事契約**（語風、節奏、感官、禁梗概；匯總原 PROSE04–15） |
| `USR24` | 主角內心語風（modern_taiwanese_baihua，21世紀台灣白話口語） |
| `USR25` | 歲數計算（`@SYS01` 年 − `@PLR`/`@NPC` 出生年；進 warm） |
| `USR43` + `LAW-TIME01` | **遊戲時間軸**：`@SYS.時間` 存種子約定的 **機械欄**（本作 `YYYY-MM-DDTHH`）；HUD 顯示由 `USR43` 註冊的曆法 formatter 衍生 |
| `LAW-EDG01` | **劇情 `@EDG.at`**：非接線 relation 的 `add` 須填當拍 `@SYS.時間`；`beat_turn_finish` 可自動補空 `at` |
| `USR44` + `LAW-TEC01` + `GLO09` + `EN*` | **科技詞彙邊界**：`unknows`／`speaks` 劇情 `@EDG` + LAW；鎖定時 NPC 僅 `GLO09` 匠話 |
| `USR45` + `LAW-VIT01` | **身體狀態入劇**：每拍讀 `@PLR.身體狀態`；OLN／正文／選項／finish 須連動氣血內力疲勞飽食 |
| `USR46` + `LAW-WX00` + `ART01` | **太玄調息**：專拍修內功可回氣血／內力／略降疲勞；初学乍練有上限與走火風險 |
| `USR47–49` + `LAW-VIT02` | **氣血／內力上限**：`cur/max` 由主修內功池表＋歲數＋`WUX01`；功法**消耗**見 `USR49`／`@ART.burn` |
| `USR50` + `LAW-VIT03` + `LAW-PIPE23` | **氣血歸零**：昏厥失能；**禁六選項、自動敘事跳拍**；醒復後回 **≥1** 再恢復選項；**禁**即死結局 |
| `USR22` + `LAW-PERS00` | **選項文案可讀白話**；禁梗概式連環動詞 |
| `LAW-PROSE00` + `LAW-PROSE00` | **優美白話武俠**；禁縮略梗概體；起承轉合白描鋪陳 |
| `LAW-SBD01/02` + `LAW-SCR01/02` + `LAW-PROSE00` | **四階段**：大綱→分鏡→腳本→小說正文 |
| `LAW-CHR00` + `LAW-PROSE00` | **年齡綁定**：身形、稱謂、對白、力氣描寫須對齊歲數；禁預設成人 |
| `LAW-CHR00–03` | 主角／NPC 語氣機制（含年齡；內心含USR24；人設見 `@NPC`＋`features`） |
| `@GLO01–04` | 四維語意（經 `USR10` governs 進 warm） |

**LAW 撰寫原則：** `mechanism`＋`constraint` 只寫短碼；**禁寫死主角姓名**（LAW-NAME00）——存 `@USR03`。**禁在 `@LAW` 內綁定特定角色 id 或姓名**；角色語氣由 `@NPC.特徵`／`@PRS`／`@PTY` 與 `features` 接線落實。

**EDG + LAW06：** `query_warm` 只帶錨點子圖 `governs`／`features` 相連的 `@LAW`，外加 `LAW01–05` 與 `constraint=*` 全域列。`@STEP01` governs 全部 `@USR`、管線 `@LAW`、`@CFG`；`@USR10` governs `@GLO`。

**中文欄位：** Tag map 欄位名不出現在 warm；欄位值用繁體短碼；正文不得逐字複誦圖（LAW-OUT00）。

**開局（一次性，非每拍）：** 讀本檔 Tag map + Opening seed → `session_open`；`@USR03=未定` 時只收 2–4 字姓名再進 beat。

## Integrator notes（人類維護 seed 用，LLM 不依賴）

**維護對照：** 改管線／語風／LAW／USR → **Opening seed — Engine**；改開局人物／產業／科技／場景 → **Opening seed — World**。`USR04`（主角技能清單）在 Engine 區但屬本作背景值，換題材時一併改。

### 引擎（Engine）

- **LAW-G13 `era_fit`：** 新增 `@NPC`／`@ITM`／`@TEC`／`@PRD`／`@LOC`／`@SKL`／`@BIZ` 時對照 `@SYS01`（崇禎十年江南晚明）。人：身分稱謂衣飾武裝宜晚明；物：禁現代器具名入圖（主角現代知識須經 `@TEC` 解鎖鏈）；地：行政商路工坊水平宜晚明；與 **LAW-G01**／**G06–08**／**G04**／**USR26** 連用
- **世界觀雙層（USR26 + LAW-G14 + LAW-G04）：** 本作**時代底層為晚明**，重大**歷史事件與歷史人物須先擬真**（年號、官制、賦役、物價、江南社會情勢宜 plausible），再允許劇情**架空偏離**史書細節；**武學與江湖規則**則架空於**金庸武俠宇宙**（內力、門派生態、武學品級、奇遇邏輯可取金庸譜系，如太玄經、獨孤九劍等，見 `@USR04`／`@PLR`）。**分層原則：** 官府、戶籍、商路、工藝、戰爭大事→晚明擬真；武功、幫會、江湖規矩→金庸式；**禁**無故混入其他 IP 或現代梗入旁白。與 **LAW-PROSE00**／**USR20** 語體參照一致。
- **武學判定（USR27–29 + LAW-WX00–10 + `@WUX` + `@ART` + `@MWU`）：** 金庸架空面須有**內功、武學、輕功**與**各招熟練度**等機械判定；**各武功強弱不同**（`@ART` 係數），**同一武功亦看熟練度**（`@MWU`）。
  - **三欄分工：**
    - **`@WUX`**：肉身**門類**總筐（內功／武學／輕功），走 `USR28` 品級階梯。
    - **`@MWU`（武學熟練度）：** 角色對**每一門** `@ART` 的熟練度；`武功`＝`@ART` id；`熟練度`／`當值`走 `USR28`（0–5）。**魂穿開局**：所攜武功 MWU **皆初学乍練（當值 1）**——「記得招意／要訣」，**施展仍生疏**（`USR41`）。**靈魂圖書館不是武功**，不進 `@MWU`。
    - **`@ART`**：武功譜（金庸梯＋強弱係數 k）；不存角色熟練度。
  - **`soul_knows` vs `has_mwu`：** `soul_knows`＝意識裡知道這門武功存在、可查圖書館；`has_mwu`＝實際熟練度條。開局兩者並存，但 MWU 一律初学乍練。
  - **`@ART`（武功譜）：** `名稱`＝金庸式武功；`門類`＝內功／武學／輕功／綜合；`金庸梯`＝三流→絕頂（`USR38`）；`係數`＝同品級下**武功強弱倍率 k**（`USR39`）。
  - **金庸梯與 k 帶（USR38–39，維護新武功時對表）：**

    | 金庸梯 | k 帶 | 金庸參照（例） |
    |--------|------|----------------|
    | **絕頂** | 1.80–2.00 | 九陽神功、九陰真經、易筋經、六脈神劍（大成） |
    | **超一流** | 1.40–1.85 | 獨孤九劍、降龍十八掌、太玄經、乾坤大挪移、北冥神功 |
    | **一流** | 1.05–1.35 | 凌波微步、全真劍法、黯然銷魂掌 |
    | **二流** | 0.90–1.05 | 少林長拳、江南把式 |
    | **三流** | 0.75–0.85 | 五虎斷門刀、尋常鏢局把式 |

    開局 `@ART`／`@MWU` 種子見 World 區；主角 `ART01–04` 皆 **MWU 初学乍練**。
  - **熟練度成長（USR41 + LAW-WX00）：** 與四維相同，**僅里程碑**（長時修練結算、實戰突破、章節收束等）可讓指定 `@MWU` **+1 當值**（最多升至登峰造極 5）；**禁**每拍選項自動升熟練度。同一里程碑同一門武功最多 +1。
  - **有效戰力（LAW-WX00 + LAW-WX00）：** **cap_idx**＝min(**本拍 `@MWU` 當值**, 對應 `@WUX` 門類當值, 歲數上限, 內力是否支撐)；**eff_idx**＝round(cap_idx × **art_k**)，上限 5。`@OLN` 須標**本拍武功**（`@ART` id／名）。
  - **`@WUX`（肉身門類）：** 開局硝：內功未入門、武學／輕功初学乍練。
  - **`@USR04`（技能清單摘要）：** 武功皆标**初学乍練**；靈魂圖書館仍**登峰造極**（知識庫，非 MWU）。
  - **武功特例（USR40 + LAW-WX00）：**
    - **六脈神劍（ART03）：** k＝1.90；內力 &lt;7 時 k 降至 **1.10**（指力難續）；內力代價 **×2**（LAW-WX00→WX06）
    - **獨孤九劍（ART02）：** 拆招／料敵場面；`@TRT` 智力 ≥2 時 margin **+1**（破招加成，每場一次）
    - **凌波微步（ART04）：** **僅**在輕功／躍避／脫身主導時乘 k；純兵刃對拆**不**用此 k，改算 WUX03
    - **太玄經（ART01）：** **綜合**；運內時乘 WUX01、拆招時乘 WUX02，皆用 k＝1.75；**內功功效**見 **LAW-WX00**（調息回氣血／內力）
  - **一般成敗（LAW-WX00 + LAW-PERS00）：** 非交手場面用情境 DC + 修正；若涉及武功（躍牆等），eff_idx 仍可乘對應 `@ART` 的 k。
  - **過招／輸贏（USR35–37 + LAW-WX00–07 + LAW-WX00）：** 拆招、比武、實戰等須分勝負時走交手判定。
    1. **`@OLN` 先標：** `交手模式`（`USR35`）、`本拍武功`（`@ART` 名或 id）、`對手武功`（`@ART` 或 `@NPC.技能`）、`對手品級`（`USR28` 名或索引）。
    2. **對手戰力（LAW-WX00 + LAW-WX00）：** 對手 **opp_idx**＝round(對手品級索引 × 對手 **art_k**)；無名把式 k＝1.00；三流鏢師用 ART21 k＝0.80 等。
    3. **己方戰力：** **eff_idx**＝round(cap_idx × 本拍 art_k)，cap_idx 來自 LAW-WX00；門類須與 `@ART.門類` 或本拍寫法一致（綜合可擇一維）。
    4. **差距 margin**（正文不報數）：
       - **基底**＝eff_idx − opp_idx
       - **修正（`USR37`）：** 內功／輕功／四維／狀態／兵刃／地形／偷襲／人數（同前）；**獨孤破招**另 +1（見上）
         - 內功有效索引 ≥2 且內力 ≥3：**+1**（運氣護招）；內力 &lt;3：**−1**（LAW-WX00 走形）
         - 輕功有效 ≥ 對手且選擇身法決勝：**+1**（躍避搶位）；僅撤退不加分
         - `@TRT` 力量 ≥2：**+1**（近身硬接）；智力 ≥2：**+1**（料敵先機）；氣運 ≥2：**至多 +1／場**（須寫僥倖，不可連用）
         - 疲勞 ≥2、氣血 ≤4、十歲肉身：**各 −1**（歲數修正上限 −2）
         - 兵刃／地形／人數／偷襲不備：**各 ±1**（群戰劣勢 **−1**；偷襲方 **+1**、被襲 **−1**）
    5. **結果帶（`USR36`）：**

       | margin | 結果 | 敘事要點 |
       |--------|------|----------|
       | ≥ +3 | **碾勝** | 一招制敵或完封；對手難以再戰 |
       | +1～+2 | **小勝** | 佔上風收招；對手認輸、退讓或留手 |
       | 0 | **平手** | 互試深淺；各自收勢 |
       | −1～−2 | **小負** | 被逼退、失守一招；須寫可見代價 |
       | ≤ −3 | **慘敗** | 受制、負傷、兵器脫手；重大代價 |

    6. **模式差（`USR35` + LAW-WX00）：**
       - **試招／過招：** 代價 **半額**；禁致命一擊；慘敗多為淤傷、兵器脫手、當眾難堪
       - **實戰／追殺：** 全額代價；可傷氣血、內力大耗
       - **群戰：** margin 再 **−1**；須寫顧此失彼
    7. **代價表（LAW-WX00，落盤 `@PLR` 身體狀態）：**

       | 結果 | 氣血 | 內力 | 疲勞 |
       |------|------|------|------|
       | 碾勝 | — | −1 | +0 |
       | 小勝 | — | −1 | +1 |
       | 平手 | — | −1 | +1 |
       | 小負 | −1 | −1 | +1 |
       | 慘敗 | −2～−3 | −2 | +2 |

       試招／過招：上表數值 **÷2 無條件進位**（至少內力 −1 若曾運氣）。**禁**無代價滿級發招。
    8. **與四維分工：** 交手主軸＝**eff_idx vs opp_idx**（含 `@ART` 係數）；`@TRT` 只做修正。
  - **例（十歲硝，獨孤九劍 MWU＝1）：** cap_idx＝min(1,1,歲數)＝1；eff＝round(1×1.85)＝2；對手鏢師略有小成(3)×五虎(0.80)＝2；基底平手，疊歲數 −1、內力 −1 → **小負**；正文須寫**記得劍意、手腳跟不上**（初学乍練），非大宗師發招。
  - **內力消耗（LAW-WX00）：** 內力不足時禁寫滿血大招；宜寫氣短、招式走形或改以匠藝／智力選項應對。
  - **匠藝 vs 武學：** `@SKL` 仍管打鐵等生產技能；`@WUX` 只管江湖武學三維，勿混欄位。
  - **HUD（USR02）：** 尾欄可帶氣血、內力、武學三維摘要（不報型號、不逐字複誦圖）。
- **LAW-NAME00 `era_name`：** 新增 `@NPC.名字` 須合晚明社會背景——流民／匠戶／商賈／士绅／胥吏等宜不同取名習慣；可用排行、小名、字號慣例；禁現代人名、日韓音譯名、網路暱稱；落盤後 **LAW-G09** `exact_names` 維持一致。主角名仍只經 `@USR03`（LAW-NAME00）
- **多階段流程**（`USR23|beat_stage` 驅動，**LAW-PIPE20 `no_bundle`**）：
  1. **大綱 (@OLN)**：`USR23=oln` → finish **僅** `oln_lines` → `beat_stage=sbd`
  2. **分鏡 (@SBD)**：finish **僅** `sbd_lines` → `scr`
  3. **腳本 (@SCR)**：finish **僅** `scr_lines` → `prose`
  4. **小說正文**：finish `prose` + `@OPT` + `STEP`/`SYS`/`@PLR` → `beat_stage=oln`，`STEP.n+1`
  - **禁** 同一次 finish 交多種 wire（bundle）；agent 在單一玩家訊息內連跑四輪 begin/finish，僅第 4 輪對玩家呈現劇情。
- 正文最終以 LAW-PROSE00 為主（從腳本擴寫），而非直接從 @OLN 跳 prose。
- 16 型（`@PTY`）僅編排；正文／HUD 不報型號
- 沈芯對白偏魅力／智力基線；沈蘭偏氣運／魅力（見 `@PRS`）
- `LAW-PROSE00`：間白承載情緒；連續對話可不加動作標籤；禁每句必附神情（併入 warm_prose 契約）
- **正文長度**：已取消硬性字數 gate（`USR05=no_gate`，`LAW-PROSE00=length_advisory`）。`beat_turn_finish` 與 `prose_count.py` 不再阻擋。**USR21（800_zh_advisory）** 仍須每拍可見：`beat_turn_begin` 補查 `USR21` → `draft_note`／`prose_advisory_zh`；`beat_turn_finish` 回報 `short_advisory` 與 `prose_advisory_hint`（不擋關，提醒擴寫）。
- **語風（USR51 + USR18–20 + USR24 + LAW-PROSE00/01/17）：** 第二人稱「你」；**旁白與敘事**為優美白話武俠（金庸白描、梁羽生情景）。**主角內心**走現代台灣白話（詳見下方「魂穿者語音分層」）。**禁**縮略語句、梗概體、網文式快剪（旁白層）。場面先立環境，再入人物與動作；句式長短交錯。
- **角色對白與內心（LAW-CHR00–03 + USR24 + `@NPC`／`@PRS`）：** 沈芯偏沉穩簡約；沈蘭偏潑辣帶笑（寫在 NPC 圖與 persona）。主角內心走現代台灣白話；對外說話以時代為主，偶有現代思維露餡。
- **身體狀態與劇情（USR45 + LAW-VIT01 + `@PLR.身體狀態`）：** HUD 尾欄與圖上 `@PLR` 第 7 欄（`氣血`／`內力`／`內功`／`武學`／`輕功`／`飽食`／`疲勞` 等）**不是裝飾**，每拍必納入編排與正文。
  - **warm 必讀：** `beat_turn_begin` 後先對照 `@PLR.身體狀態`；與 **LAW-WX00／WX06**（交手）、**LAW-PERS00**（DC）連用，但**即使本拍無打鬥**仍須遵守下列敘事規則。
  - **`@OLN`（oln_embed）：** `情節要點` 須寫本拍**體征約束或代價**（例：「過勞只砌半槽」「飢餓須先墊粥」「氣血瀕危禁遠行」）。**禁** OLN 與當前狀態矛盾（疲勞 10 仍寫「精神百倍連夜趕工」）。
  - **正文（prose_embed）：** 須有可感知體征（腿軟、眼黑、腹中空鳴、掌心磨破、氣短）；**禁**十歲肉身無限續航。魂穿者**心智可硬撐、肉身須露餡**。
  - **六選項（opt_respect，`LAW-OPT00` cite）：** 選項須**可信**於當前狀態——過勞（疲勞 ≥8）或氣血 ≤3 時，**禁**六項全是高強度體力／通宵；宜含歇息、進食、請姊妹代勞、改日再辦等路線，或由 NPC 當場勸阻。圖書館（6）與產業帳（5）不受體力門檻限制，但正文仍可寫「蹲著查閱、眼皮打架」。**氣血＝0 或 `昏厥:是` 時 `LAW-VIT03` 覆寫 `LAW-OPT00`（`vit03_suspend`）——見下方，禁呈現六選項。**
  - **落盤（finish_delta）：** 體力消耗拍 `beat_turn_finish` **須** `update @PLR` 身體狀態。參考代價（可疊加，Integrator 心算）：

    | 活動強度 | 疲勞 | 氣血 | 飽食 | 內力 |
    |----------|------|------|------|------|
    | 輕（閒聊、心算、短距） | +0～+1 | — | — | — |
    | 中（搬磚、守窯數時辰） | +1～+2 | −0～−1 | 略餓→飢餓 | — |
    | 重（通宵砌窯、連日苦力） | +2～+3 | −1～−2 | 飢餓→極餓 | −0～−1 |
    | 交手 | 見 **LAW-WX00** | 見 **LAW-WX00** | — | 見 **LAW-WX00** |

  - **區間語義（正文與 NPC 反應）：**

    | 欄位 | 區間 | 劇情含義 |
    |------|------|----------|
    | 氣血 | ≤3 虛弱；≤1 瀕危；**=0 昏厥** | 易失手、暈眩、需人扶；沈芯等可強制歇息；**歸零見 LAW-VIT03** |
    | 內力 | &lt;3 | 禁滿血運氣大招（**LAW-WX00**）；宜氣短走形 |
    | 疲勞 | ≥8 過勞；10 極限 | 禁再排通宵重活；宜睡眠里程碑 |
    | 飽食 | 略餓→飢餓→極餓 | 宜進食拍；極餓時力量 DC 再 −1 |

  - **氣血歸零（USR50 + LAW-VIT03，每拍 warm）：** `氣血:0`＝**肉身昏厥／失能**，魂穿意識可殘留模糊感知，**禁**當作「還能正常幹活」。
    - **觸發：** 本拍 `finish_delta` 或交手代價（**LAW-WX00**）使氣血降至 **0**；`@PLR.身體狀態` 宜加 **`昏厥:是`**（醒復後刪或改 `否`）。
    - **正文（collapse）：** 須寫倒地、視界发黑、耳鳴、四肢不聽使喚；內心可短句斷片（**禁**長篇正常行動）。若當場有人（沈芯、沈蘭等），須寫其驚扶、呼喊、搬抬。
    - **自動敘事拍（`auto_beat`，`LAW-PIPE23` + `USR50.no_opts`）：** 昏厥中**玩家無法選項**——`LAW-OPT00` 整條 **suspend**（禁列 1–6、禁產業帳、禁圖書館）。流程改為：
      1. **歸零當拍** `finish` 落盤 `氣血:0`、`昏厥:是` 後，**不呈現六選項**；
      2. 下一動 **`beat_turn_begin`** 偵測昏厥 → `pipeline.auto_beat=true`；
      3. **直接寫正文**（救助、搬抬、灌湯、昏沉斷片、時間流逝），**`beat_turn_finish`** 落盤；
      4. 仍 **0** 可再自動一拍（病情惡化／姊妹哭求），**至多連續 2 自動拍**後須醒復；
      5. **醒復拍** 結束、`昏厥:否` 且 **氣血≥1** 後，**恢復**常規六選項。
      - **禁**把昏厥寫成「請選 1 呼救／選 2 賭醒」——那是清醒人的選項體，與失能矛盾。
    - **交手（`LAW-WX00`）：** 氣血已 **0** 或本拍將歸零 → **自動敗北／被制**；不得再發招反勝；對手可補刀敘事但**本作禁寫主角當場身死**（`no_permadeath`）。
    - **調息（`LAW-WX00`）：** **禁**——昏厥中無法盤膝運氣；須先醒復至 **氣血≥1**。
    - **醒復（rescue_wake，寫在自動敘事拍內）：** 須明寫 **照料／睡眠／灌湯／簡易包紮／沈芯施救** 等，可推進 `@SYS` 時間（常 **1～4 時辰** 或一夜）。醒後：
      - `氣血` **至少 1**（通常 **1～2**，不得超 **LAW-VIT02** 上限）；
      - `疲勞` 常 **+1** 或維持高位；
      - `昏厥:否`；飽食若仍 **飢餓** 須續寫進食。
    - **連續昏厥：** 第二個自動拍宜寫病情惡化（高熱、說胡話、姊妹哭求），**仍禁即死**；同拍或緊接醒復。
    - **落盤：** 歸零當拍 `finish` **須** `update @PLR`（氣血 **0**、`昏厥:是`）；自動敘事拍 **不寫 `@OPT`**；醒復拍 **須** 回升至 **≥1** 並清昏厥標記。
  - **恢復（禁無代價回滿）：** 僅**明確歇息拍**（睡眠數時辰）、**進食拍**、**太玄調息專拍**（**LAW-WX00**）、療傷里程碑 可回升。恢復**不得超過當前上限**（**LAW-VIT02**）。參考：熟睡一夜 疲勞 −3～−5、氣血 +1～+2；飽餐一頓 飽食升一檔。**昏厥中**僅 **照料醒復拍**（見 **LAW-VIT03**）可脫離 **0**，調息與圖書館不算。
  - **氣血／內力上限（USR47–49 + LAW-VIT02，每拍 warm）：**
    - **分兩層：** **當前值**（池裡剩多少）≠ **上限**（池子多大）。`@PLR.身體狀態` 宜寫 **`氣血:cur/max；內力:cur/max`**（禁寫死 `/10`）。
    - **設計原則（消耗定上限）：** 內力上限須能通過 **「本拍武功」的交手消耗**（**LAW-WX00** × **LAW-WX00**／`USR49`）反推合理性：
      - **续航公式（Integrator 心算）：** `sustain ≈ floor(neili_max ÷ burn_per_exchange)`（實戰全額；試招半額）。
      - **例：** 太玄主修 `burn=1`，`neili_max=6` → 約 **6 回**運氣／平手或 **3 回**實戰全額後見底；六脈 `burn=2` 同池僅 **3 發**，且 `comfort≥7` 才不失常（**USR40**）。
    - **主修定池（`USR48`）：** 主角**只有一個內力池**；**上限由主修內功系**決定（硝＝`ART01` 太玄）。副修武學（獨孤、六脈、凌波）改**消耗倍率**與**起招門檻**，不另開第二池。
    - **氣血上限（肉身）：** `qi_max = min(12, 4 + (歲數−8) + WUX01_idx)`。十歲、內功初学乍練 → **7**；歲數與內功升檔里程碑可擴池；**與功法 burn 無直接表**（氣血吃外傷／苦力／飢餓）。
    - **歲數加成（內力池）：** `age_bonus = max(0, (歲數−10)//2)`，疊加至主修表，**絕對頂 12**。
    - **主修內力上限表（`WUX01` 品級索引 0–5）：**

      | 主修 `@ART` | pool | idx0 | idx1 | idx2 | idx3 | idx4 | idx5 | burn | sustain@idx1 |
      |-------------|------|------|------|------|------|------|------|------|--------------|
      | **ART01** 太玄 | 厚 | 4 | **6** | 8 | 10 | 11 | 12 | 1 | ~6 |
      | **ART10** 九陽 | 厚 | 5 | 7 | 9 | 11 | 12 | 12 | 1 | ~7 |
      | **ART11** 九陰 | 厚 | 4 | 6 | 8 | 10 | 11 | 12 | 1 | ~6 |
      | **ART14** 易筋 | 厚 | 4 | 6 | 9 | 11 | 12 | 12 | 1 | ~6 |
      | **ART15** 北冥 | 中 | 4 | 5 | 7 | 9 | 10 | 11 | 1 | ~5；吸內可敘事暫超池 |

    - **副修武學消耗（本拍武功＝該 `ART` 時，`USR49`／`@ART.burn`）：**

      | `@ART` | burn／交手 | 舒適起招 | 與池互動 |
      |--------|------------|----------|----------|
      | ART01 太玄（運內） | 1 | ≥3 | 厚池；調息回補（WX11） |
      | ART02 獨孤 | 1 | ≥3 | 中耗；重悟性 |
      | ART03 六脈 | **2** | **≥7** | 薄续航；滿池亦難連發 |
      | ART04 凌波 | 1 | ≥2 | 輕功躍避鏈；實戰少連招 |

    - **升上限（里程碑，禁每拍）：** `WUX01`（內功門類）升一檔 → 查主修表跳一列；歲數每 +2 年 → `age_bonus+1`。`MWU` 熟練度**不直接**漲池，但高 MWU 降有效 burn（敘事／margin），與 **LAW-WX00** 一致。
    - **落盤：** `beat_turn_finish` 更新 `@PLR` 時，當前值**不得超 max**；若里程碑升檔，可同拍調高 max 並可選補至新 max 的敘事（非無條件回滿）。
    - **與 WX02：** `內力 < comfort` 或 `< max×0.5` 時走形；六脈另遵 `comfort7`。
  - **太玄經調息（USR46 + LAW-WX00 + ART01／MWU01／WUX01，每拍 warm）：**
    - **可以回氣血**，但屬**內功調息**，不是睡覺或吃飯的替代；睡眠主降疲勞，進食主升飽食，太玄主補**內力**並**輔助**氣血。
    - **觸發：** 須為**專拍**（選項或劇情明寫盤膝太玄、守隙調息）；**禁**重體力拍順帶全額收益；**禁**圖書館槽（6）自動調息。
    - **時長：** 一輪＝**半時辰～一時辰**（`@OLN` 標明；推進 `@SYS` 時間）。
    - **收益（`MWU01` 初学乍練，單輪上限）：**

      | 結果 | 內力 | 氣血 | 疲勞 | 敘事 |
      |------|------|------|------|------|
      | 調息順 | +1 | +1 | −1 | 腹內溫意一絲，氣息漸穩 |
      | 勉強收功 | +1 | — | — | 一絲溫意即散，略補內力 |
      | 走火／岔氣 | −1 | −1 | +1 | 疲勞≥9、氣血≤2、極餓時易發；宜寫心慌、咳逆 |

    - **熟練度升檔後**（`MWU01`≥2）：單輪氣血可 +1～+2、內力 +1～+2、疲勞 −1～−2（仍禁單拍回滿）。
    - **十歲肉身：** 單日有效調息**至多兩輪**；第三輪起收益半額或僅敘事無落盤。
    - **`@WUX01`（內功門類）：** 首次**順調**里程碑可自「未入門」升至「初学乍練」（同 **LAW-WX00** 節奏，一生一次）。
    - **finish：** 調息專拍須 `update @PLR`；與 **LAW-VIT01** `finish_delta` 連動。
  - **與武學分工：** 交手 margin／代價仍走 **LAW-WX00–07**；`LAW-VIT01` 管**日常劇情與匠活**亦須付體征代價，並要求選項／OLN 不脫節。
- **四維與判定（USR33–34 + LAW-PERS00–04 + `@TRT` + `@GLO01–04`）：**
  - **選 1–4 ≠ 每拍 +1 屬性。** 槽位只標**本拍敘事軸**（走力量／智力／魅力／氣運的寫法與後果傾向），`@OPT.變化` 欄寫 `軸` 或 `—`，**禁**機械 `+1` 累加。
  - **`@TRT` 累積**僅在**里程碑**增加（`USR33`）：長時訓練結算、重大抉擇落盤、章節收束、修為／匠藝突破等；**同里程碑最多 +1** 單維。日常幫工、閒聊、清灰**不**漲四維。
  - **判定有用處：** 需要成敗時，用 **有效四維**（`@TRT` 該維累積）對 **情境難度 DC**（1–10，由任務／對手／物件／環境定，寫在 `@OLN` 或 Integrator 心算）。再疊修正：**歲數**（`USR25`）、**氣血／內力／疲勞**（`@PLR`，見 **LAW-VIT01**）、**武學三維**（`@WUX`＋`LAW-WX`）、魂知身不能。例：搬重柴 DC5，十歲 −1，疲勞 −1，力量 TRT3 → 淨 1，勉強可為但須寫吃力；TRT0 則易失敗。
  - **禁**「選過力量選項就自動成功」；**禁**無 DC 的無限膨脹四維。與 **LAW-WX00** 一般判定並用；**過招／比武／實戰**則必走 **LAW-WX00–07** 輸贏帶，近身拆招看武學維＋力量修正；談判看魅力＋智力；賭運氣看氣運。
  - **熟練度 vs 四維分工（USR42 + LAW-PERS00，每拍 warm）：** `@MWU`→過招／發招 **eff_idx 主軸**；`@TRT`→一般場面 **vs DC**，過招僅 **margin ±1**；**禁** MWU 進 DC、**禁** TRT 進 eff_idx；選項軸不自動加任一邊。
- **選項文案（USR22 + USR32 + LAW-PERS00）：** `@OPT.文案` 須**可讀白話完整句**（約 12–28 字），與正文語體一致；**禁**策劃梗概體、連環動詞串。槽位 **1–4** 扣 `@GLO01–04` 四維**語意軸**（非數值加成）；槽位 **5** 產業帳；槽位 **6** 靈魂圖書館（`@GLO08`／`USR32`）。**六選項佈局見 `USR30` + `LAW-OPT00`。**
- **產業帳（LAW-OPT00）：** 選 **5** → 只展開帳目，**不推進時間**，再呈現 1–6。
- **圖書館查閱（LAW-OPT00 + LAW-LIB00–03 + LAW-G05）：** 選 **6** → 意識入「知識殿堂」短景＋**【靈魂圖書館檢閱】**；cite 與**最新 `@OLN` 主題匹配**的 `@LIB`／相關 `@TSK`／`@TEC`。**不推進時間**；**不**因查閱自動 +1 智力。
- **靈魂圖書館（LAW-G05 + LAW-LIB00–03 + `@LIB` + PLR 核心能力 + USR04）**：`@LIB` 索引：`LIB01` 總路線（`T01`）；`LIB02`／`LIB03` 焦炭科技樹；**`LIB04–06` 匠坊維運**（風箱皮墊、聽聲看火、炭堆防潮）。查閱須**先讀 warm 最新 `@OLN`**，用 `USR31b` 關鍵詞匹配 `@LIB` 主題欄；**禁**無 OLN 依據時只列 `TEC01/02`（`no_tech_tree_only`）。
- **圖書館對題範例（OLN05「風箱漏風」）：** 必 cite `LIB04`（風箱皮墊）、`LIB01→T01` 支線「供風穩定」、連結 `GLO09`（聽聲、塊子）；可註 `LIB02` 前置「供風穩」；**禁**跳過風箱主題改講焦炭全流程。
- **魂穿者語音分層（USR18/19 + USR24 + LAW-CHR00 + LAW-PROSE00）**：主角本質是21世紀台灣現代人，語風需分層處理：
  - 旁白與整體敘事（USR19）：維持**優美白話武俠**，第二人稱「你」，參照金庸白描、梁羽生情景。
  - 主角內心獨白、自我吐槽、自言自語（USR24 + LAW-PROSE00）：使用**台灣日常白話口語**（我勒、靠北、這什麼鬼、真的假的、拜託啦、幹、超級、這也太...、有夠...等），可帶強烈時代落差感、現代常識吐槽、黑人問號。內心可直白思考「這在現代根本小case」「靠，現在的鐵不會這樣啊」。
  - 對NPC說話：以晚明語境為主（稱謂、用詞盡量貼合身分），但主角偶爾會不小心冒出現代思維或詞彙，被NPC視為「怪人」「神神叨叨」或「異鄉口音」，這是特色而非bug。
  - 對白與內心合計比例仍受 LAW-PROSE00 約束。
- **LAW-CHR00 現在同時參照 USR24／USR25**：內心語風＋歲數綁定；外部表現仍受時代與對象約束。
- **年齡綁定（USR25 + LAW-CHR00 + LAW-PROSE00 + `@SYS01`／出生年）：** 每拍正文、對白、@OLN／@SBD／@SCR 須先算歲數＝`@SYS01` 西元年 − `@PLR`／`@NPC` 出生年。身形、力氣、稱謂、能承擔的工種須對齊；**禁**預設成年壯漢／「大哥」式成人稱呼（除非對象確實年長）。魂穿者：**心智可成年、肉身須年幼**——內心吐槽可成熟，手腳身高氣力描寫仍依歲數。
- **遊戲時間（USR43 + LAW-TIME01 + `novel_mcp.game_time`）：**
  - **機械軸（圖／`@SYS` 第 3 欄）：** 種子在 `LAW-TIME01`／`USR43` 約定可比較格式；本作採 `YYYY-MM-DDTHH`（24 時整點）。**novel_mcp 只強制軸格式與單調遞進**，不內建任何年號曆法。
  - **顯示欄（HUD）：** 由 `USR43` 的 `display=` 選 formatter（本作 `chongzhen_shichen`＋`era_base`／`era_name`）；換種子可改曆法或僅顯示 ISO。
  - **推進規則：** 一般劇情拍依 `@OLN` 跨度更新軸小時；**選 5／6** 不推進；圖書館查閱不推進。
  - **歲數（USR25）：** 取機械軸 **年份** 減出生年（與 HUD 年號無關）。
  - **遷移：** 舊自由文本可暫讀；新拍起寫入種子約定的機械欄。開局 `1637-09-01T06`。

### 背景（World）

- **時代與架空（USR26／SYS01／CFG01）：** 崇禎十年（1637）江南為**晚明史實面**；江湖武學為**金庸武俠架空面**。史有名人物若出場，宜先依史實身分與行事邏輯推演，再因主角介入而偏離；虛構人物仍須貼晚明社會。武林事件、內力修為、門派設定不與正史對表，但不得與晚明行政經濟常識硬衝（如崇禎朝無電報卻有幫會火並可）。打鬥、身法、運氣須走 **LAW-WX** 判定；**過招須走 LAW-WX00 輸贏帶**，不得無成本滿級發招。
- **開局歲數（崇禎十年＝1637，算法見 USR25）：** 北見硝 **10**（1627）、沈芯 **12**（1625）、沈蘭 **10**（1627）。兩姊妹是**孩童匠戶孤女**經營鐵坊，不是成年掌櫃帶丫鬟。對硝宜用「你」「小子」「這位小兄弟」等，禁當作二十歲壯漢；搬鐵可寫吃力、袖管卷起的手臂仍細，武學底子僅略超常。沈芯對白可早熟穩重但仍帶童音；沈蘭可潑辣稚氣。
- **開局場景 SCN01 `smithy_gate`：** 沈家鐵坊門前甦醒；姊妹求聘小工；`E11` 待聘、`E01` 求助待解鎖。編劇須 cite **`USR70|opening_scene`**；禁寫破廟流浪孤女討生活（`LAW-OLN01` opening_scn）。**接線：** `E20–E23` SCN01 features 全場；`E09/E10` 姊妹經營／協助 `B01`；`EG287–EG292` B01／N01／N02 features `LAW-OLN01`／`USR70`；`EG293–EG294` SCN01 features。
- **產業帳：** 鐵坊負債 2 兩；焦炭／高爐科技樹鎖定，綁 `T01` 升級作坊任務。
- **科技詞彙邊界（USR44 + LAW-TEC01 + GLO09 + `EN*` 接線，每拍 warm）：**
  - **圖內專名**（`@TEC`／`@PRD` 列名）＝玩家／圖書館／已解鎖科技可用；**鎖定時 NPC 對白禁用**。
  - **劇情 `@EDG`：** `N01|speaks|GLO09`（匠話）；`N01|unknows|TEC01`／`PRD01`（不知煉焦專名）；`P01|knows_via|LIB02`（對照）。
  - **NPC 匠話**（`GLO09`）：堅炭、燒透、塊子、成料、聽聲……**不等於**懂煉焦工藝。
  - **TEC01 解鎖：** 刪 `EN10`／`EN11`，改 `@TEC` 為已解鎖，可加 `N01|knows|TEC01|沈芯認可`。
- **沈芯／沈蘭：** 人設與 `@PRS`／`@PTY`／`@SKL`／`@ITM` 見 World 區；對白基線見下方角色對白條目。
