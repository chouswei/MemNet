"""崇禎＋地支時辰 HUD — 《工匠傳奇》seed 用；非 novel_mcp 核心假設。"""

from __future__ import annotations

from novel_mcp.game_time import GameTime
from novel_mcp.time_display import register_formatter

_SHICHEN = ("子", "丑", "寅", "卯", "辰", "巳", "午", "未", "申", "酉", "戌", "亥")

_MONTH_ZH = (
    "",
    "正月",
    "二月",
    "三月",
    "四月",
    "五月",
    "六月",
    "七月",
    "八月",
    "九月",
    "十月",
    "十一月",
    "十二月",
)

_DIGIT_ZH = "零一二三四五六七八九"


def _reign_year_zh(n: int) -> str:
    if n <= 0:
        return str(n)
    if n < 10:
        return _DIGIT_ZH[n]
    if n < 20:
        return "十" + (_DIGIT_ZH[n - 10] if n > 10 else "")
    tens, ones = divmod(n, 10)
    head = _DIGIT_ZH[tens] + "十"
    return head + (_DIGIT_ZH[ones] if ones else "")


def _shichen(hour: int) -> str:
    if hour == 23 or hour == 0:
        return "子"
    idx = ((hour + 1) // 2) % 12
    return _SHICHEN[idx]


def format_chongzhen_shichen(gt: GameTime, spec: dict[str, str]) -> str:
    era_name = spec.get("era_name", "崇禎")
    try:
        era_base = int(spec.get("era_base", "1628"))
    except ValueError:
        era_base = 1628
    reign = gt.year - era_base + 1
    month = _MONTH_ZH[gt.month]
    return f"{era_name}{_reign_year_zh(reign)}年{month}{gt.day}日・{_shichen(gt.hour)}時"


register_formatter("chongzhen_shichen", format_chongzhen_shichen)
