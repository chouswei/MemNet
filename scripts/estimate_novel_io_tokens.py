"""Rough token estimates for llm-novel-writer MemNet wire IO."""

from __future__ import annotations


def est(s: str) -> tuple[int, int, int]:
    c = len(s)
    return c, round(c / 4), round(c / 3.2)


LAW = """@LAW: LAW01|EDG|on_context|hide|settled_edg_unless_anchor
@LAW: LAW02|*|on_add|unique|one_id_add_then_update
@LAW: LAW03|EDG|on_add|validate|src_dist_exist_first
@LAW: LAW04|*|on_add|use_backslash|backslash_pipe_not_bare
@LAW: LAW-ATOM01|*|on_add|no_sentences|break_to_nodes_edges
@LAW: LAW-HP01|CHR|on_turn|stat_cite|cite_chr_attr_step2
@LAW: LAW-PIPE02|STEP|on_turn|obey_n|read_step_row_each_llm_call"""

STEP1 = "@STEP: STEP01|1|SCN01|persistent"

WARM_T1 = LAW + "\n" + """@STEP: STEP01|2|SCN01|persistent
@LORE: LORE01|philosophers_stone|artifact|elixir_source|persistent
@LORE: LORE02|philosophers_stone|artifact|voldemort_power_y1|persistent
@LORE: LORE03|quirrell|threat|possessed|persistent
@LORE: LORE04|quirrell|threat|closing_stone|persistent
@RULE: RULE01|choices_wizard|theme|cite_choices_not_ability|persistent
@RULE: RULE02|magic_toll|risk|low_skill_visible_cost|persistent
@RULE: RULE03|one_change|structure|one_state_delta_per_beat|persistent
@CHR: CHR01|You|protagonist|Courage:3|Wit:4|Charms:2|Stealth:3|firstyear_belong|unhurt|persistent
@CHR: CHR02|Harry|ally|brave|scarred|boy_who_lived|persistent
@CHR: CHR03|Hermione|ally|brilliant|loyal|rules_first_help_wary|persistent
@ITEM: ITM01|wiggenweld|consumable|1|steady_spell|persistent
@QUEST: QST01|stone_y1|1|stop_quirrell|final_door_ward|active|persistent
@SCN: SCN01|final_door|warded|delete_on_settle
@EVT: EVT00|risk|door|charms|bite|persistent
@COST: CST00|CHR01|potential_mark|hand|persistent
@EDG: E01|SCN01|set_in|LORE01||persistent
@EDG: E02|SCN01|features|CHR01||persistent
@EDG: E03|SCN01|features|CHR02||persistent
@EDG: E04|SCN01|features|CHR03||persistent
@EDG: E05|CHR01|governs|RULE01||persistent
@EDG: E06|SCN01|features|ITM01||persistent
@EDG: E07|SCN01|features|EVT00||persistent
@EDG: E08|SCN01|features|CST00||persistent
@EDG: E09|EVT00|applies_to|CHR01||persistent
@EDG: E10|CST00|potential_for|CHR01||persistent
@EDG: ES01|STEP01|focus|SCN01||persistent"""

WARM_POST = LAW + "\n" + """@STEP: STEP01|2|SCN02|persistent
@LORE: LORE02|philosophers_stone|artifact|voldemort_power_y1|persistent
@RULE: RULE02|magic_toll|risk|low_skill_visible_cost|persistent
@CHR: CHR01|You|protagonist|Courage:3|Wit:4|Charms:2|Stealth:3|firstyear_belong|shaken_hand|persistent
@CHR: CHR02|Harry|ally|brave|scarred|boy_who_lived|persistent
@CHR: CHR03|Hermione|ally|brilliant|loyal|rules_first_help_wary|persistent
@QUEST: QST01|stone_y1|1|stop_quirrell|final_door_ward|active|persistent
@SCN: SCN02|threshold|breach|delete_on_settle
@EVT: EVT01|yield|CHR01|door|charms2_self|delete_on_settle
@COST: COST01|CHR01|mark|hand|persistent
@BOND: BOND01|CHR03|CHR01|up|self_risk|persistent
@EDG: E20|SCN02|set_in|LORE02||persistent
@EDG: E21|SCN02|features|CHR01||persistent
@EDG: E23|SCN02|caused|EVT01||persistent
@EDG: ES02|STEP01|focus|SCN02||persistent"""

SEED = "\n".join(
    [
        LAW,
        "@STEP: STEP01|1|SCN01|persistent",
        "@LORE: LORE01|philosophers_stone|artifact|elixir_source|persistent",
        "@LORE: LORE02|philosophers_stone|artifact|voldemort_power_y1|persistent",
        "@LORE: LORE03|quirrell|threat|possessed|persistent",
        "@LORE: LORE04|quirrell|threat|closing_stone|persistent",
        "@RULE: RULE01|choices_wizard|theme|cite_choices_not_ability|persistent",
        "@RULE: RULE02|magic_toll|risk|low_skill_visible_cost|persistent",
        "@RULE: RULE03|one_change|structure|one_state_delta_per_beat|persistent",
        "@CHR: CHR01|You|protagonist|Courage:3|Wit:4|Charms:2|Stealth:3|firstyear_belong|unhurt|persistent",
        "@CHR: CHR02|Harry|ally|brave|scarred|boy_who_lived|persistent",
        "@CHR: CHR03|Hermione|ally|brilliant|loyal|rules_first_help_wary|persistent",
        "@ITEM: ITM01|wiggenweld|consumable|1|steady_spell|persistent",
        "@QUEST: QST01|stone_y1|1|stop_quirrell|final_door_ward|active|persistent",
        "@PLT: PLT01|stone_y1|year-1|stone_not_voldemort|active|persistent",
        "@USR: USR01|scene_length|spare|persistent",
        "@USR: USR02|voice|close-second-wonder|persistent",
        "@SCN: SCN01|final_door|warded|delete_on_settle",
        "@EVT: EVT00|risk|door|charms|bite|persistent",
        "@COST: CST00|CHR01|potential_mark|hand|persistent",
        "@EDG: ES01|STEP01|focus|SCN01||persistent",
        "@EDG: E01|SCN01|set_in|LORE01||persistent",
        "@EDG: L01|LORE01|risk_if|LORE02||persistent",
        "@EDG: L02|LORE03|seeks|LORE01||persistent",
        "@EDG: L03|LORE04|targets|LORE01||persistent",
        "@EDG: E02|SCN01|features|CHR01||persistent",
        "@EDG: E03|SCN01|features|CHR02||persistent",
        "@EDG: E04|SCN01|features|CHR03||persistent",
        "@EDG: E05|CHR01|governs|RULE01||persistent",
        "@EDG: E06|SCN01|features|ITM01||persistent",
        "@EDG: E07|SCN01|features|EVT00||persistent",
        "@EDG: E08|SCN01|features|CST00||persistent",
        "@EDG: E09|EVT00|applies_to|CHR01||persistent",
        "@EDG: E10|CST00|potential_for|CHR01||persistent",
    ]
)

STEP5_IN = """@CHOICE: CHOICE01|SCN01|1|self|delete_on_settle
@STEP: STEP01|6|SCN02|persistent
@CHR: CHR01|You|protagonist|Courage:3|Wit:4|Charms:2|Stealth:3|firstyear_belong|shaken_hand|persistent
@SCN: SCN01|final_door|warded|delete_on_settle
@SCN: SCN02|threshold|breach|delete_on_settle
@EVT: EVT01|yield|CHR01|door|charms2_self|delete_on_settle
@COST: COST01|CHR01|mark|hand|persistent
@BOND: BOND01|CHR03|CHR01|up|self_risk|persistent
@EDG: E20|SCN02|set_in|LORE02||persistent
@EDG: E21|SCN02|features|CHR01||persistent
@EDG: E22|SCN02|costs|CHR01||persistent
@EDG: E23|SCN02|caused|EVT01||persistent
@EDG: E24|EVT01|suffered_by|CHR01||persistent
@EDG: E25|SCN02|imposed|COST01||persistent
@EDG: E26|CHR01|carries|COST01||persistent
@EDG: E27|SCN02|changed|BOND01||persistent
@EDG: E28|BOND01|between|CHR03|CHR01
@EDG: E29|EVT01|used|charms2||persistent
@EDG: ES02|STEP01|focus|SCN02||persistent"""

WARM_CHR_D1 = LAW + "\n@CHR: CHR01|You|protagonist|Courage:3|Wit:4|Charms:2|Stealth:3|firstyear_belong|shaken_hand|persistent\n@COST: COST01|CHR01|mark|hand|persistent"
WARM_RULE_D1 = LAW + "\n@RULE: RULE02|magic_toll|risk|low_skill_visible_cost|persistent"
WARM_SCN_D1 = LAW + "\n@SCN: SCN02|threshold|breach|delete_on_settle\n@EVT: EVT01|yield|CHR01|door|charms2_self|delete_on_settle"

# Hypothetical pre-refactor fat SCN row (sentence in graph)
FAT_SCN = "@SCN: SCN01|final_door|warded|You stand with Harry and Hermione before the warded door. The silver tracery pulses. Quirrell is close. Your Charms is 2. Hermione is wary. Harry nods at the vial.|delete_on_settle"


def main() -> None:
    rows = [
        ("LAW block (every warm prepends)", LAW, "stdout"),
        ("update @STEP (orchestrator to memnet)", STEP1, "stdin"),
        ("add seed once (Part B)", SEED, "stdin"),
        ("query warm STEP01 depth=2 — door beat", WARM_T1, "stdout"),
        ("query warm STEP01 depth=2 — post-breach", WARM_POST, "stdout"),
        ("query warm CHR01 depth=1", WARM_CHR_D1, "stdout"),
        ("query warm RULE02 depth=1", WARM_RULE_D1, "stdout"),
        ("query warm SCN02 depth=1", WARM_SCN_D1, "stdout"),
        ("add/update step 5 batch", STEP5_IN, "stdin"),
        ("read get --id (single row)", "@CHR: CHR01|You|protagonist|...", "stdout"),
    ]

    print("MemNet wire IO — llm-novel-writer atomic pattern")
    print("Token estimate: chars/3.2 (pipe-heavy wire); ±15% by model tokenizer\n")
    print(f"{'Operation':<44} {'dir':>5} {'chars':>6} {'~tok':>6} {'#rows':>6}")
    print("-" * 72)
    for name, body, direction in rows:
        c, _t4, t32 = est(body)
        n = body.count("\n") + 1
        print(f"{name:<44} {direction:>5} {c:>6} {t32:>6} {n:>6}")

    _, _, law_t = est(LAW)
    _, _, t1_t = est(WARM_T1)
    _, _, post_t = est(WARM_POST)
    d1_t = sum(est(x)[2] for x in (WARM_CHR_D1, WARM_RULE_D1, WARM_SCN_D1, WARM_CHR_D1))
    _, _, s5_t = est(STEP5_IN)
    _, _, seed_t = est(SEED)
    _, _, fat_t = est(LAW + "\n" + FAT_SCN + "\n" + WARM_T1.split("@LORE:")[0].split("@STEP:")[0])

    print("\n--- Per pipeline step (Turn 1 door beat) ---")
    steps = [
        ("1 Read: update STEP in", STEP1, "in"),
        ("1 Read: warm stdout to LLM", WARM_T1, "out-LLM"),
        ("2 Write: warm in LLM prompt again", WARM_T1, "out-LLM"),
        ("4 Analyse: 4x depth-1 warm", str(d1_t) + " (sum)", "out-LLM"),
        ("5 Persist: add/update stdin", STEP5_IN, "in (orchestrator)"),
    ]
    for label, val, note in steps:
        if val.isdigit() or val[0].isdigit():
            print(f"  {label:<36} ~{val} tok  [{note}]")
        else:
            print(f"  {label:<36} ~{est(val)[2]:>4} tok  [{note}]")

    turn_llm = t1_t * 2 + d1_t
    law_dup = law_t * 6  # ~6 warm calls that prepend LAW
    print(f"\n  LLM context from MemNet wire (Turn 1): ~{turn_llm} tok")
    print(f"  Of which LAW repeated:              ~{law_dup} tok ({law_t} × 6 reads)")
    print(f"  Slice without LAW (if deduped):       ~{turn_llm - law_dup + law_t} tok")

    print("\n--- Comparison ---")
    print(f"  Atomic warm (door):     ~{t1_t} tok")
    print(f"  Post-breach warm:       ~{post_t} tok  (smaller — settled SCN01 gone)")
    print(f"  One fat SCN in warm:    +~{est(FAT_SCN)[2]} tok per read vs minimal SCN")
    print(f"  Seed (once, not in LLM loop): ~{seed_t} tok")


if __name__ == "__main__":
    main()
