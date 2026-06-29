"""Frozen v1 keys for god-realm player setup (novel-agnostic machinery)."""

from __future__ import annotations

import re

FORMAT_GOD_REALM = "【神域】"
FORMAT_PLAY_BEAT = "【劇情】"
SENTINEL = "未定"
PROFILE_NAME_RE = re.compile(r"^[\u4e00-\u9fff]{2,4}$")
PROFILE_GENDERS = frozenset({"男", "女"})

# USR keys — story copy lives in seed rows; these are lookup names only.
SETUP_FORMAT_GOD_KEY = "setup_format_god"
SETUP_FORMAT_PLAY_KEY = "setup_format_play"
SETUP_TONE_KEY = "setup_tone"
SETUP_GOD_LINE_OPEN = "setup_god_line_open"
SETUP_GOD_LINE_ASK_NAME = "setup_god_line_ask_name"
SETUP_GOD_LINE_ASK_GENDER = "setup_god_line_ask_gender"
SETUP_GOD_LINE_PROFILE = "setup_god_line_profile"  # legacy combined prompt
SETUP_GOD_LINE_TRANSMIGRATE = "setup_god_line_transmigrate"
SETUP_PROFILE_NAME_RULE_KEY = "setup_profile_name_rule"
SETUP_PROFILE_GENDERS_KEY = "setup_profile_genders"
SETUP_PICK_OFFER_COUNT_KEY = "setup_pick_offer_count"
SETUP_PICK_OFFER_SEED_KEY = "setup_pick_offer_seed"
# Prefer skill_catalog_* in new seeds; martial_catalog_* = legacy 武俠 instances (沈家).
SKILL_CATALOG_MD_KEY = "skill_catalog_md"
SKILL_CATALOG_SESSION_KEY = "skill_catalog_session"
OPENING_CATALOG_MD_KEY = "martial_catalog_md"  # legacy alias
MARTIAL_CATALOG_SESSION_KEY = "martial_catalog_session"  # legacy alias
OPENING_OFFER_EMPTY = "_"
DEFAULT_PICK_OFFER_MIN = 5
DEFAULT_PICK_OFFER_MAX = 9

# Party panel — author/script sets via beat_turn_finish USR updates.
PARTY_ROSTER_KEY = "party_roster"
PARTY_UI_KEY = "party_ui"
PARTY_UI_NOTE_KEY = "party_ui_note"

# Directed affinity: `@EDG` with relation `aff_to`; scores in `attrs` (not a separate node tag).
AFF_EDG_RELATION = "aff_to"
AFF_DIMENSION_LABELS = ("親密度", "信任度", "敬重")
AFF_SCORE_MIN = -100
AFF_SCORE_MAX = 100
