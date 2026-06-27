"""Frozen v1 constants for god-realm player setup (novel-agnostic)."""

from __future__ import annotations

import re

FORMAT_GOD_REALM = "【神域】"
FORMAT_PLAY_BEAT = "【劇情】"
SLOT_ORDER = ("neigong", "martial", "qinggong")
SENTINEL = "未定"
PROFILE_NAME_RE = re.compile(r"^[\u4e00-\u9fff]{2,4}$")
PROFILE_GENDERS = frozenset({"男", "女"})

SLOT_SCENE_USR: dict[str, str] = {
    "neigong": "USR60",
    "martial": "USR61",
    "qinggong": "USR62",
}

SLOT_LABELS: dict[str, str] = {
    "neigong": "內功",
    "martial": "武學",
    "qinggong": "身法",
}

WUX_RANK_NEIGONG = "未入門"
WUX_RANK_MARTIAL = "初学乍練"
WUX_RANK_QINGGONG = "初学乍練"
MWU_RANK = "初学乍練"
