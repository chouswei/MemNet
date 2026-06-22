# 晚明財閥傳 — Novel initial state

Edit this file before starting a **new** story. Load once via MCP `session_open`.

## Tag map

```text
@LORE: id|name|kind|code|recycle
@CHR: id|name|role|born|gender|looks|speak|personality|props|attrs|skills|status|recycle
@TRAIT: id|subject|kind|code|recycle
@SKILL: id|subject|name|rank|recycle
@LIB: id|host_skill|domain|tier|status|recycle
@TEC: id|owner|lib_ref|code|status|recycle
@VIT: id|subject|kind|cur|max|recycle
@FIN: id|owner|cash|debt|silver_flow|recycle
@IND: id|owner|code|silver_in|silver_out|status|recycle
@PRD: id|ind_ref|code|kind|silver_in|silver_out|status|recycle
@QUEST: id|code|tier|goal|reward|status|recycle
@PLT: id|code|phase|origin|status|recycle
@SCN: id|code|beat|recycle
@EVT: id|kind|src|dist|code|recycle
@STEP: id|n|focus|recycle
@CHOICE: id|focus|chosen|recycle
@USR: id|key|value|recycle
@RULE: id|domain|topic|code|recycle
@TIME: id|beat|phase|duration|wait|recycle
@CHP: id|chp_num|start_beat|end_beat|char_total|status|recycle
```

（`@EDG` 無獨立 row schema — 見 tag map 慣例。）

## Opening seed

```text
@LAW: LAW01|EDG|on_context|hide|settled_edg_unless_anchor
@LAW: LAW02|*|on_add|unique|one_id_add_then_update
@LAW: LAW03|EDG|on_add|validate|src_dist_exist_first
@LAW: LAW04|*|on_add|use_backslash|backslash_pipe_not_bare
@LAW: LAW-ATOM01|*|on_add|no_sentences|break_to_nodes_edges
@LAW: LAW-PROSE01|*|on_turn|lang_zh_hant|step2_options_zh_tw_only
@LAW: LAW-PROSE02|*|on_turn|register|step2_colloquial_plain_not_pastiche
@LAW: LAW-PROSE03|*|on_turn|immersion|step2_300_600_zh_scene
@LAW: LAW-PROSE04|*|on_turn|length_gate|call_prose_metrics_before_append
@LAW: LAW-PROSE05|*|on_turn|dialogue|step2_min35pct_speech_not_ops_log
@LAW: LAW-PROSE06|*|on_turn|plain|short_sentences_oral_narration
@LAW: LAW-LIB01|LIB|on_turn|lib_gate|cite_only_unlocked_lib_tiers
@LAW: LAW-TEC01|TEC|on_turn|tec_cite|cite_tec_when_in_scene_warm
@LAW: LAW-WX01|CHR|on_turn|skill_cite|cite_skills_or_skill_row_step2
@LAW: LAW-WX02|LIB|on_turn|route_gate|fulltext_only_active_route_in_progress_tier
@LAW: LAW-CHR03|CHR|on_turn|pc_name|use_chr01_name_step2_no_unset
@LAW: LAW-CHR04|CHR|on_turn|heroine_cast|heroine1_heroine2_jinyong_subtle
@LAW: LAW-CHR02|CHR|on_turn|voice_cite|cite_looks_speak_personality_step2
@LAW: LAW-CHR05|CHR|on_turn|voice_sheet|lock_dialogue_to_chr_trait_rule
@LAW: LAW-HUD01|*|on_turn|status_bar|append_hud_after_step2_options
@LAW: LAW-HUD02|IND|on_turn|industry_bar|append_ind_line_after_hud01
@LAW: LAW-IND01|IND|on_turn|biz_cite|cite_ind_prd_when_warm_in_scene
@LAW: LAW-OPT01|*|on_turn|five_options|opts_1_4_story_opt5_ind_ledger
@LAW: LAW-OPT02|CHOICE|on_pick|ind_ledger|no_beat_advance_expand_then_reoffer
@LAW: LAW-OUT01|*|on_turn|chapter_file|append_prose_only_after_step2
@LAW: LAW-OUT02|CHP|on_turn|chapter_merge|close_on_target_or_cap_or_scn
@LAW: LAW-PIPE02|STEP|on_turn|obey_n|read_step_row_each_llm_call
@LAW: LAW-TIME01|*|on_turn|time_escalate|advance_beat_each_persist
@LAW: LAW-TIME02|SCN|on_turn|duration_code|climax_short_else_medium
@LAW: LAW-TIME03|CHOICE|on_turn|skip_wait|offer_when_wait_skippable

@STEP: STEP01|1|SCN01|persistent
@TIME: TIME01|1|calm|medium|required|persistent

@LORE: LORE01|jianghu|world|jinyong_wulin|persistent
@LORE: LORE02|ming|era|wanli_1610|persistent
@LORE: LORE05|smithy|place|crumbling_forge|persistent
@LORE: LORE06|soul|origin|overwork_mee_engineer|persistent
@LORE: LORE07|body|host|beggar_boy_y14|persistent
@LORE: LORE08|isekai|gift|soul_library_all21c|persistent
@LORE: LORE09|tax|reform|yitiao_whip_silver|persistent
@LORE: LORE10|silver|supply|overseas_japan_manila|persistent
@LORE: LORE11|silver|strain|hoarding_tax_squeeze|persistent
@LORE: LORE12|politics|wanli38|kechang_faction_noise|persistent
@LORE: LORE13|region|town|inland_county_silver_tight|persistent
@LORE: LORE14|library|canon|jinyong_14_manuals_fulltext|persistent
@LORE: LORE15|story|title|wanming_caifa_zhuan|persistent
@LORE: LORE16|cast|heroine|fl01_tielan|persistent
@LORE: LORE17|cast|heroine|fl02_tiexin|persistent
@LORE: LORE18|prose|style|colloquial_wanli_smithy|persistent

@RULE: RULE01|jianghu|theme|cite_choices_not_talent|persistent
@RULE: RULE02|qi_toll|risk|low_skill_visible_cost|persistent
@RULE: RULE03|one_change|structure|one_state_delta_per_beat|persistent
@RULE: RULE04|soul_library|progress|implement_to_unlock_next|persistent
@RULE: RULE05|silver|economy|copper_wage_silver_tax_gap|persistent
@RULE: RULE06|wuxia|manual|fulltext_after_route_pick_practice_for_rank|persistent
@RULE: RULE07|wuxia|route|one_in_progress_primary_route|persistent
@RULE: RULE08|prose|tone|colloquial_baseline_not_jinyong_copy|persistent

@CHR: CHR01|unset|protagonist|y1596|male|ragged_thin|terse_instruct|curious_cautious_engineer|isekai_mee_eng jinyong_reader soul_library_gift|Wit:5 Courage:2 Luck:3|neigong:0 jianfa:0 qinggong:0 duanzao:0 soul_library:0|weak_hungry|persistent
@CHR: CHR02|TieLan|heroine1|y1597|female|soot_braids|soft_worried_duty|kind_practical_elder|smithy_heir_elder fl01|Courage:3 Wit:3|duanzao:1 neigong:0|hungry|persistent
@CHR: CHR03|TieXin|heroine2|y1598|female|thin_ponytail|bright_exclaim_young|shy_brave_impulsive|smithy_heir_young fl02|Courage:2 Wit:4|duanzao:0 neigong:0|hungry|persistent

@TRAIT: TR01|CHR01|speak|short_instruct_no_flourish|persistent
@TRAIT: TR02|CHR01|inner|soul_sea_quote_not_xindao|persistent
@TRAIT: TR03|CHR01|drive|engineer_risk_calc|persistent
@TRAIT: TR04|CHR01|taboo|no_he_knew_summary|persistent
@TRAIT: TR05|CHR02|speak|soft_worry_nickname|persistent
@TRAIT: TR06|CHR02|drive|duty_neighbor_livelihood|persistent
@TRAIT: TR07|CHR02|tone|kind_not_shrew|persistent
@TRAIT: TR08|CHR02|fear|fire_theft_silver|persistent
@TRAIT: TR09|CHR03|speak|exclaim_copper_count|persistent
@TRAIT: TR10|CHR03|speak|mimic_adult_wrong|persistent
@TRAIT: TR11|CHR03|drive|shy_then_blurt|persistent
@TRAIT: TR12|CHR03|taboo|no_cynic_no_lecture|persistent
@TRAIT: TR13|CHR01|taboo|no_jingai_si_yiban_metaphor|persistent
@TRAIT: TR14|CHR02|taboo|plain_talk_not_bookish|persistent
@TRAIT: TR15|CHR03|taboo|kid_talk_not_literary|persistent

@QUEST: QST01|smithy_job|1|accept_work_offer|half_food_share|active|persistent
@QUEST: QST02|keep_smithy|1|guard_forge|food_short|active|persistent
@QUEST: QST03|gather_fuel|1|stock_charcoal|door_patch|active|persistent
@PLT: PLT01|wanming_caifa_zhuan|calm|smithy_gate_origin|active|persistent

@VIT: VIT01|CHR01|qi_blood|8|10|persistent
@VIT: VIT02|CHR01|neili|0|0|persistent
@FIN: FIN01|CHR01|0|0|0|persistent

@IND: IND01|LORE05|smithy|0|0|operating|persistent
@PRD: PRD01|IND01|blade_repair|service|0|0|active|persistent
@PRD: PRD02|IND01|horseshoe|goods|0|0|active|persistent
@PRD: PRD03|IND01|nail_batch|goods|0|0|low|persistent

@RULE: RULE09|prose|length|300_to_600_chars_per_beat|persistent
@RULE: RULE10|CHR|name|player_sets_pc_name_once|persistent
@RULE: RULE11|hud|format|cite_stat_fin_quest_warm_only|persistent
@RULE: RULE12|biz|silver|update_ind_prd_fin_on_transaction|persistent
@RULE: RULE13|hud|industry|cite_ind_prd_warm_only|persistent
@RULE: RULE14|opt5|ind_ledger|cite_ind_prd_manager_warm_only|persistent
@RULE: RULE15|hud|partner|show_heroine_rank_in_partner_field|persistent
@RULE: RULE16|money|display|wire_wen_hud_label_wen|persistent
@RULE: RULE17|out|chapter|filename_chp3_prose_only_no_options|persistent
@RULE: RULE18|out|chapter|merge_beats_2400_4200_zh|persistent
@RULE: RULE19|prose|dialogue|min35pct_3lines_end_on_speech|persistent
@RULE: RULE20|prose|voice|cite_warm_chr_trait_rule_per_speaker|persistent
@RULE: RULE21|CHR01|voice|short_instruct_soul_inner_forbid_xindao|persistent
@RULE: RULE22|CHR02|voice|soft_worry_duty_neighbor_fire_fear|persistent
@RULE: RULE23|CHR03|voice|exclaim_money_mimic_shy_blurt|persistent
@RULE: RULE24|prose|register|colloquial_plain_ming_town|persistent
@RULE: RULE25|prose|ban|no_ai_pastiche_ops_poetry|persistent

@USR: USR01|scene_length|300_600_zh|persistent
@USR: USR02|voice|colloquial_plain_zh_tw|persistent
@USR: USR04|pc_name|unset|persistent
@USR: USR05|options|five_fixed_opt5_ledger|persistent
@USR: USR06|chapter_out|novel-output/wanming_caifa_zhuan/chapters|persistent
@USR: USR07|chapter_target|2400_4200_zh|persistent

@CHP: CHP01|1|0|0|0|open|persistent

@SCN: SCN01|smithy_gate|awakening_offer|delete_on_settle
@EVT: EVT00|offer|CHR02|CHR01|half_food_work|persistent

@SKILL: SK01|CHR01|soul_library|0|persistent
@SKILL: SK02|CHR02|duanzao|1|persistent
@LIB: LIB00|SK01|catalog|0|unlocked|persistent
@LIB: LIB01|SK01|smithing|0|locked|persistent
@LIB: LIB02|SK01|mechanics|0|locked|persistent
@LIB: LIB03|SK01|jinyong_canon|0|available|persistent
@LIB: LIB04|SK01|route_catalog|0|available|persistent
@LIB: LIB20|SK01|dugu_jianfa|0|locked|persistent
@LIB: LIB21|SK01|jiuyin_fragment|0|locked|persistent
@LIB: LIB22|SK01|huashan_jianfa|0|locked|persistent
@LIB: LIB23|SK01|yijin_jing|0|locked|persistent

@EDG: ES01|STEP01|focus|SCN01||persistent
@EDG: E_TIME|SCN01|features|TIME01||persistent
@EDG: E01|SCN01|set_in|LORE05||persistent
@EDG: E12|SCN01|set_in|LORE13||persistent
@EDG: E13|LORE05|features|LORE11||persistent
@EDG: L09|LORE09|depends_on|LORE10||persistent
@EDG: L10|LORE11|worsens|LORE09||persistent
@EDG: E02|SCN01|features|CHR01||persistent
@EDG: E03|SCN01|features|CHR02||persistent
@EDG: E04|SCN01|features|CHR03||persistent
@EDG: E05|CHR01|governs|RULE01||persistent
@EDG: E06|SCN01|caused|EVT00||persistent
@EDG: E07|EVT00|applies_to|CHR01||persistent
@EDG: E08|LORE06|applies_to|CHR01||persistent
@EDG: E09|LORE07|applies_to|CHR01||persistent
@EDG: E10|LORE08|applies_to|CHR01||persistent
@EDG: E15|LORE14|applies_to|SK01||persistent
@EDG: E21|LORE15|governs|PLT01||persistent
@EDG: E11|CHR01|governs|RULE04||persistent
@EDG: E16|CHR01|governs|RULE06||persistent
@EDG: E17|CHR01|governs|RULE07||persistent
@EDG: E19|USR02|governs|RULE08||persistent
@EDG: E20|USR01|governs|RULE09||persistent
@EDG: E22|USR04|applies_to|CHR01||persistent
@EDG: E23|CHR01|governs|RULE10||persistent
@EDG: E24|VIT01|applies_to|CHR01||persistent
@EDG: E25|VIT02|applies_to|CHR01||persistent
@EDG: E26|FIN01|applies_to|CHR01||persistent
@EDG: E27|QST01|main_for|PLT01||persistent
@EDG: E28|QST02|assigned_to|CHR02||persistent
@EDG: E29|QST03|assigned_to|CHR03||persistent
@EDG: E30|CHR01|governs|RULE11||persistent
@EDG: E31|LORE05|hosts|IND01||persistent
@EDG: E32|IND01|offers|PRD01||persistent
@EDG: E33|IND01|offers|PRD02||persistent
@EDG: E34|IND01|offers|PRD03||persistent
@EDG: E35|IND01|governs|RULE12||persistent
@EDG: E36|CHR01|governs|RULE13||persistent
@EDG: E37|IND01|managed_by|CHR02||persistent
@EDG: E38|USR05|governs|RULE14||persistent
@EDG: E39|CHR02|cast_as|LORE16||persistent
@EDG: E40|CHR03|cast_as|LORE17||persistent
@EDG: E41|PLT01|features|LORE16||persistent
@EDG: E42|PLT01|features|LORE17||persistent
@EDG: E43|CHR01|governs|RULE15||persistent
@EDG: E44|CHR01|governs|RULE16||persistent
@EDG: E45|USR06|governs|RULE17||persistent
@EDG: E46|CHR01|governs|LAW-OUT01||persistent
@EDG: E49|CHR01|governs|LAW-PROSE04||persistent
@EDG: E60|CHR01|governs|LAW-PROSE05||persistent
@EDG: E61|CHR02|governs|RULE22||persistent
@EDG: E62|CHR03|governs|RULE23||persistent
@EDG: E63|USR01|governs|RULE19||persistent
@EDG: E64|CHR01|governs|RULE21||persistent
@EDG: E68|PLT01|governs|RULE20||persistent
@EDG: E67|CHR01|has_trait|TR01||persistent
@EDG: E69|CHR01|has_trait|TR02||persistent
@EDG: E70|CHR01|has_trait|TR03||persistent
@EDG: E71|CHR01|has_trait|TR04||persistent
@EDG: E72|CHR02|has_trait|TR05||persistent
@EDG: E73|CHR02|has_trait|TR06||persistent
@EDG: E74|CHR02|has_trait|TR07||persistent
@EDG: E75|CHR02|has_trait|TR08||persistent
@EDG: E76|CHR03|has_trait|TR09||persistent
@EDG: E77|CHR03|has_trait|TR10||persistent
@EDG: E78|CHR03|has_trait|TR11||persistent
@EDG: E79|CHR03|has_trait|TR12||persistent
@EDG: E80|CHR01|has_trait|TR13||persistent
@EDG: E81|CHR02|has_trait|TR14||persistent
@EDG: E82|CHR03|has_trait|TR15||persistent
@EDG: E83|LORE18|governs|RULE24||persistent
@EDG: E84|USR02|governs|RULE25||persistent
@EDG: E47|USR07|governs|RULE18||persistent
@EDG: E48|CHP01|tracks|PLT01||persistent
@EDG: E14|CHR02|governs|RULE05||persistent
@EDG: E_SK01|CHR01|has_skill|SK01||persistent
@EDG: E_SK02|CHR02|has_skill|SK02||persistent
@EDG: E_LIB00|SK01|features|LIB00||persistent
@EDG: E_LIB01|SK01|features|LIB01||persistent
@EDG: E_LIB02|SK01|features|LIB02||persistent
@EDG: E_LIB03|SK01|features|LIB03||persistent
@EDG: E_LIB04|SK01|features|LIB04||persistent
@EDG: E_LIB20|SK01|features|LIB20||persistent
@EDG: E_LIB21|SK01|features|LIB21||persistent
@EDG: E_LIB22|SK01|features|LIB22||persistent
@EDG: E_LIB23|SK01|features|LIB23||persistent
```

**CHR notes:** 開局 `LIB20+` locked；**首個 step 5** 依 CHOICE 設一條 `in_progress`。`LIB03`/`LIB04` available。鐵匠 `LIB01` 可與立路同 beat 並行。

**Voice sheet (warm SSOT — step 2 LLM must match):**

| CHR | `@CHR.speak` / `personality` | `@RULE` | `@TRAIT` (via `has_trait` EDG) |
|-----|------------------------------|---------|--------------------------------|
| CHR01 主角 | `terse_instruct` / `curious_cautious_engineer` | RULE21 | TR01 短句務實不花巧；TR02 識海引句禁「心道」；TR03 工程風險估算；TR04 禁「他知道」式總結 |
| CHR02 鐵蘭 | `soft_worried_duty` / `kind_practical_elder` | RULE22 | TR05 柔聲擔心帶稱呼；TR06 責任鄰里生計；TR07 溫厚非潑辣；TR08 怕走火失竊缺銀 |
| CHR03 鐵心 | `bright_exclaim_young` / `shy_brave_impulsive` | RULE23 | TR09 驚嘆數銅板；TR10 學大人說錯；TR11 羞怯後脫口；TR12 禁老成譏諷長篇說教 |

**LAW-CHR02/05:** 有對白時 warm 須含該 CHR 列 + 其 TRAIT + RULE21–23；台詞語氣不得偏離上表。

**Prose register (warm SSOT — 白話，非仿金庸套句):**

| Row | code | Step-2 LLM 要旨 |
|-----|------|-----------------|
| **LAW-PROSE02** | `step2_colloquial_plain_not_pastiche` | 晚明小鐵匠巷口口語；**不要**刻意仿金庸文白夾雜 |
| **LAW-PROSE06** | `short_sentences_oral_narration` | 短句、白描、能念出聲；旁白也像**說書人口語** |
| **RULE08** | `colloquial_baseline_not_jinyong_copy` | 金庸只作**節奏參考**（快慢、懸念），**禁止**套句、成語堆砌 |
| **RULE24** | `colloquial_plain_ming_town` | 用詞：說/看/怕/成不成；少用「竟」「似…一般」「驚…之氣」 |
| **RULE25** | `no_ai_pastiche_ops_poetry` | 禁 AI 味：流水帳旁白、武俚+工業術語硬拼、结尾升华句 |
| **LORE18** | `colloquial_wanli_smithy` | 場景錨：萬曆小縣鐵匠巷，**白話**寫生計與窯火 |
| **TR13–15** | taboo | 禁「竟未」「若合符節」「搶同一口氣」類假文青句 |

Inventory (`@ITEM`) for later beats (e.g. tools, pills) — not in opening seed.
