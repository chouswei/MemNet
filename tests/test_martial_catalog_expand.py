"""Tests for LLM martial catalog expansion (mocked LLM)."""

from __future__ import annotations

from novel_mcp.catalog_schema import CatalogSchema
from novel_mcp.martial_catalog_expand import (
    merge_arts,
    parse_llm_catalog_text,
    validate_art_dict,
)


def _sample_art(
    n: int,
    schema: CatalogSchema,
    *,
    kind: str = "武學",
    tier: str = "一流",
    k: str = "1.20",
) -> dict:
    name_key = schema.wire_columns[1]
    return {
        "id": f"ART{n:02d}",
        name_key: f"測試武功{n}",
        schema.kind_field: kind,
        schema.tier_field: tier,
        schema.coeff_field: k,
    }


def test_validate_art_dict_ok(wuxia_schema: CatalogSchema) -> None:
    assert validate_art_dict(_sample_art(25, wuxia_schema), wuxia_schema) == []


def test_validate_art_dict_bad_coeff(wuxia_schema: CatalogSchema) -> None:
    art = _sample_art(25, wuxia_schema, tier="三流", k="1.50")
    assert any(wuxia_schema.coeff_field in e for e in validate_art_dict(art, wuxia_schema))


def test_parse_llm_catalog_text(wuxia_schema: CatalogSchema) -> None:
    text = """
@ART: ART25|葵花寶典|武學|絕頂|1.95|笑傲;詭異|常駐
@ART: ART26|神照經|內功|一流|1.25|連城|常駐
"""
    arts = parse_llm_catalog_text(text, wuxia_schema)
    assert len(arts) == 2
    assert arts[0]["id"] == "ART25"


def test_merge_arts_rejects_duplicate_name(wuxia_schema: CatalogSchema) -> None:
    base = [_sample_art(1, wuxia_schema, kind="綜合", tier="超一流", k="1.75")]
    add = [_sample_art(2, wuxia_schema), _sample_art(3, wuxia_schema)]
    name_key = wuxia_schema.wire_columns[1]
    add[1][name_key] = base[0][name_key]
    merged, errs = merge_arts(base, add, wuxia_schema)
    assert len(merged) == 2
    assert any("duplicate name" in e for e in errs)


def test_default_burn_from_tag(wuxia_schema: CatalogSchema) -> None:
    from novel_mcp.catalog_schema import default_burn_for_art

    art = {
        "id": "ART99",
        "名稱": "測試功",
        "門類": "武學",
        "金庸梯": "一流",
        "係數": "1.2",
        "出處": "作品;pool薄;burn2;sustain3",
    }
    assert default_burn_for_art(art, wuxia_schema) == "2"


def test_expand_martial_catalog_mock_llm(wuxia_schema: CatalogSchema) -> None:
    from unittest.mock import patch

    from novel_mcp.martial_catalog_expand import expand_martial_catalog

    base = [_sample_art(i, wuxia_schema, kind="武學") for i in range(1, 16)]
    llm_block = "\n".join(
        f"@ART: ART{i:02d}|測試武功{i}|武學|二流|0.95|金庸|常駐"
        for i in range(16, 25)
    )

    def fake_llm(_sys: str, _user: str) -> str:
        return llm_block

    with patch(
        "novel_mcp.martial_catalog_expand.arts_from_session",
        side_effect=[base, base + parse_llm_catalog_text(llm_block, wuxia_schema)],
    ), patch(
        "novel_mcp.martial_catalog_expand.ingest_lines",
        return_value={"exit_code": 0, "lines": 9},
    ), patch("novel_mcp.martial_catalog_expand.graph_update", return_value=(0, [])):
        out = expand_martial_catalog(
            "mn_x",
            wuxia_schema,
            target_count=25,
            llm_complete=fake_llm,
            seed=42,
        )
    assert out["exit_code"] == 0
    assert out["added"] == 9
