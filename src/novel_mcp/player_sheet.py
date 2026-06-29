"""Read player inventory, martial stats, and production nodes from session graph."""

from __future__ import annotations

from typing import Any

from novel_mcp.catalog_schema import (
    ActionTemplate,
    BusinessConfig,
    CatalogSchema,
    ProductionConfig,
    read_catalog_schema,
    resolve_item_actions,
    resolve_item_kind,
    resolve_martial_actions,
)
from novel_mcp.setup_graph import (
    first_plr_id,
    list_tag_data_rows,
    read_usr_by_key,
)


def _usr_int(session: str | None, key: str, default: int = 0) -> int:
    val = read_usr_by_key(session, key)
    if not val:
        return default
    try:
        return int(val.strip())
    except ValueError:
        return default


def _tec_status(parts: list[str], prod: ProductionConfig) -> tuple[str, bool]:
    status_field = parts[3] if len(parts) > 3 else ""
    if "未解鎖" in status_field:
        return "鎖定", False
    for token in prod.status_locked:
        if token in status_field:
            return "鎖定", False
    for token in prod.status_unlocked:
        if token in status_field:
            return "已解鎖", True
    return "鎖定", False


def _fill_template(
    tpl: str,
    *,
    name: str = "",
    product: str = "",
    asset: str = "",
) -> str:
    return tpl.replace("{name}", name).replace("{product}", product).replace("{asset}", asset).strip()


def _action_from_template(
    action_id: str,
    tpl: ActionTemplate | None,
    *,
    name: str = "",
    product: str = "",
    asset: str = "",
    label_override: str | None = None,
    template_override: str | None = None,
) -> dict[str, Any]:
    label = label_override or (tpl.label if tpl else action_id)
    template = template_override or (tpl.template if tpl else action_id)
    return {
        "id": action_id,
        "label": _fill_template(label, name=name, product=product, asset=asset),
        "template": _fill_template(template, name=name, product=product, asset=asset),
        "enabled": True,
    }


def _prd_map(session: str | None, prod: ProductionConfig) -> dict[str, list[str]]:
    return {row[0]: row for row in list_tag_data_rows(session, prod.prd_tag)}


def _edges(session: str | None) -> list[list[str]]:
    return list_tag_data_rows(session, "EDG")


def _asset_mode(
    tec_id: str,
    prod: ProductionConfig,
    edges: list[list[str]],
) -> str:
    if tec_id in prod.asset_mode_by_tec:
        return prod.asset_mode_by_tec[tec_id]
    rel_requires = prod.relations.get("requires", "requires")
    for parts in edges:
        if len(parts) >= 4 and parts[1] == tec_id and parts[2] == rel_requires:
            return "installable"
    return "builtin"


def _lines_for_tec(
    session: str | None,
    tec_id: str,
    prod: ProductionConfig,
    asset_mode: str,
    unlocked: bool,
) -> int:
    if asset_mode == "installable":
        key = prod.installed_usr_key.format(tec_id=tec_id)
    else:
        key = prod.capacity_usr_key.format(tec_id=tec_id)
    val = _usr_int(session, key, -1)
    if val >= 0:
        return val
    if asset_mode == "builtin" and unlocked:
        return 1
    return 0


def _owned_for_prd(
    session: str | None,
    plr_id: str,
    prd_id: str,
    prod: ProductionConfig,
    prd_rows: dict[str, list[str]],
) -> int:
    link = prod.prd_asset_links.get(prd_id)
    if not link:
        return 0
    names = set(link.get("itm_names") or [])
    if not names:
        return 0
    total = 0
    for parts in list_tag_data_rows(session, "ITM"):
        if len(parts) < 4 or parts[1] != plr_id:
            continue
        if parts[2] in names:
            try:
                total += int(parts[3])
            except ValueError:
                total += 1
    return total


def read_production_nodes(
    session: str | None,
    schema: CatalogSchema,
    *,
    workspace_root_path: str | None = None,
) -> list[dict[str, Any]]:
    prod = schema.production
    if not prod or not session:
        return []

    plr_id = first_plr_id(session) or "P01"
    prd_rows = _prd_map(session, prod)
    edges = _edges(session)
    rel_produce = prod.relations.get("produce", "produce")
    rel_develop = prod.relations.get("develop", "develop")
    rel_requires = prod.relations.get("requires", "requires")

    nodes: list[dict[str, Any]] = []
    for parts in list_tag_data_rows(session, prod.tec_tag):
        if len(parts) < 2:
            continue
        tec_id = parts[0]
        tec_name = parts[1]
        domain = parts[2] if len(parts) > 2 else ""
        status_label, unlocked = _tec_status(parts, prod)
        asset_mode = _asset_mode(tec_id, prod, edges)
        lines = _lines_for_tec(session, tec_id, prod, asset_mode, unlocked)
        override = prod.tec_overrides.get(tec_id) or {}
        asset_label = str(override.get("asset_label") or tec_name)

        outputs: list[dict[str, str]] = []
        for ep in edges:
            if len(ep) < 4 or ep[1] != tec_id or ep[2] != rel_produce:
                continue
            prd_id = ep[3]
            prd_parts = prd_rows.get(prd_id, [prd_id])
            prd_name = prd_parts[1] if len(prd_parts) > 1 else prd_id
            prd_status = prd_parts[5] if len(prd_parts) > 5 else ""
            outputs.append({"id": prd_id, "name": prd_name, "status": prd_status})

        develops: list[str] = []
        for ep in edges:
            if len(ep) >= 4 and ep[1] == tec_id and ep[2] == rel_develop:
                develops.append(ep[3])

        requires: list[dict[str, Any]] = []
        for ep in edges:
            if len(ep) < 4 or ep[1] != tec_id or ep[2] != rel_requires:
                continue
            prd_id = ep[3]
            prd_parts = prd_rows.get(prd_id, [prd_id])
            prd_name = prd_parts[1] if len(prd_parts) > 1 else prd_id
            owned = _owned_for_prd(session, plr_id, prd_id, prod, prd_rows)
            requires.append(
                {
                    "prd_id": prd_id,
                    "name": prd_name,
                    "owned": owned,
                    "installed": lines,
                    "per_line": 1,
                }
            )

        actions: list[dict[str, Any]] = []
        templates = prod.action_templates
        if not unlocked:
            build_ov = (override.get("build") or {}) if override else {}
            build_tpl = templates.get("build")
            actions.append(
                _action_from_template(
                    "build",
                    build_tpl,
                    name=tec_name,
                    asset=asset_label,
                    label_override=build_ov.get("label"),
                    template_override=build_ov.get("template"),
                )
            )
        else:
            for out in outputs:
                produce_tpl = templates.get("produce")
                actions.append(
                    _action_from_template(
                        "produce",
                        produce_tpl,
                        name=tec_name,
                        product=out["name"],
                    )
                )
            if asset_mode == "builtin" and prod.expandable_when_unlocked:
                expand_ov = override.get("expand") or {}
                expand_tpl = templates.get("expand")
                actions.append(
                    _action_from_template(
                        "expand",
                        expand_tpl,
                        name=tec_name,
                        asset=asset_label,
                        label_override=expand_ov.get("label"),
                        template_override=expand_ov.get("template"),
                    )
                )
            if asset_mode == "installable":
                for req in requires:
                    if req["installed"] < req["owned"]:
                        install_tpl = templates.get("install")
                        actions.append(
                            _action_from_template(
                                "install",
                                install_tpl,
                                name=req["name"],
                            )
                        )
                        break
            for dev_id in develops:
                dev_parts = next(
                    (r for r in list_tag_data_rows(session, prod.tec_tag) if r[0] == dev_id),
                    None,
                )
                if not dev_parts:
                    continue
                _, dev_unlocked = _tec_status(dev_parts, prod)
                if not dev_unlocked:
                    dev_name = dev_parts[1] if len(dev_parts) > 1 else dev_id
                    upgrade_tpl = templates.get("upgrade")
                    actions.append(
                        _action_from_template(
                            "upgrade",
                            upgrade_tpl,
                            name=dev_name,
                        )
                    )

        node: dict[str, Any] = {
            "id": tec_id,
            "name": tec_name,
            "status": status_label,
            "asset_mode": asset_mode,
            "asset_label": asset_label,
            "lines": lines,
            "outputs": outputs,
            "develops": develops,
            "actions": actions,
        }
        if domain:
            node["domain"] = domain
        if requires:
            node["requires"] = requires
        nodes.append(node)

    return nodes


def _biz_col(biz: BusinessConfig, name: str, fallback: int) -> int:
    try:
        return biz.wire_columns.index(name)
    except ValueError:
        return fallback


def _plr_biz_affiliations(
    edges: list[list[str]],
    plr_id: str,
    plr_relations: tuple[str, ...],
) -> dict[str, str]:
    """Map biz_id -> relation (owns/manages) for industries the protagonist belongs to."""
    out: dict[str, str] = {}
    allowed = set(plr_relations)
    for ep in edges:
        if len(ep) < 4 or ep[1] != plr_id or ep[2] not in allowed:
            continue
        out[ep[3]] = ep[2]
    return out


def _npc_names(session: str | None, biz: BusinessConfig) -> dict[str, str]:
    return {
        row[0]: row[1]
        for row in list_tag_data_rows(session, biz.npc_tag)
        if len(row) >= 2
    }


def _related_libs(
    edges: list[list[str]],
    biz_id: str,
    *,
    rel_upgrade: str,
    rel_cite: str,
    lib_prefix: str = "LIB",
) -> set[str]:
    upgrade_targets: set[str] = set()
    for ep in edges:
        if len(ep) >= 4 and ep[1] == biz_id and ep[2] == rel_upgrade:
            upgrade_targets.add(ep[3])
        if len(ep) >= 4 and ep[1] == biz_id and ep[2] == "features" and ep[3].startswith(lib_prefix):
            upgrade_targets.add(ep[3])

    libs: set[str] = {t for t in upgrade_targets if t.startswith(lib_prefix)}
    for ep in edges:
        if len(ep) < 4:
            continue
        if ep[2] == rel_cite and ep[3] in upgrade_targets and ep[1].startswith(lib_prefix):
            libs.add(ep[1])
        if ep[1] in upgrade_targets and ep[2] == "features" and ep[3].startswith(lib_prefix):
            libs.add(ep[3])

    changed = True
    while changed:
        changed = False
        for ep in edges:
            if len(ep) < 4 or ep[1] not in libs or ep[2] != rel_cite:
                continue
            cited = ep[3]
            if cited.startswith(lib_prefix) and cited not in libs:
                libs.add(cited)
                changed = True
    return libs


def _products_for_biz(
    edges: list[list[str]],
    libs: set[str],
    prd_rows: dict[str, list[str]],
    *,
    rel_cite: str,
    rel_produce: str,
) -> list[dict[str, str]]:
    tecs: set[str] = set()
    for ep in edges:
        if len(ep) >= 4 and ep[1] in libs and ep[2] == rel_cite and ep[3].startswith("TEC"):
            tecs.add(ep[3])
    products: list[dict[str, str]] = []
    seen: set[str] = set()
    for ep in edges:
        if len(ep) < 4 or ep[1] not in tecs or ep[2] != rel_produce:
            continue
        prd_id = ep[3]
        if prd_id in seen:
            continue
        seen.add(prd_id)
        parts = prd_rows.get(prd_id, [prd_id])
        products.append(
            {
                "id": prd_id,
                "name": parts[1] if len(parts) > 1 else prd_id,
                "status": parts[5] if len(parts) > 5 else "",
            }
        )
    return products


def read_business_industries(
    session: str | None,
    plr_id: str,
    schema: CatalogSchema | None,
) -> list[dict[str, Any]]:
    """Industries (@BIZ) linked to the protagonist — not TEC production lines."""
    biz_cfg = schema.business if schema else None
    if not session or not biz_cfg:
        return []

    rel = biz_cfg.relations
    edges = _edges(session)
    affiliations = _plr_biz_affiliations(edges, plr_id, biz_cfg.plr_relations)
    if not affiliations:
        return []

    npc_map = _npc_names(session, biz_cfg)
    prd_rows = _prd_map(session, schema.production) if schema and schema.production else {}
    biz_rows = {row[0]: row for row in list_tag_data_rows(session, biz_cfg.tag)}

    ix_name = _biz_col(biz_cfg, "名稱", 1)
    ix_kind = _biz_col(biz_cfg, "類型", 2)
    ix_loc = _biz_col(biz_cfg, "地點", 3)
    ix_cash = _biz_col(biz_cfg, "現金", 4)
    ix_debt = _biz_col(biz_cfg, "負債", 5)
    ix_in = _biz_col(biz_cfg, "收入", 6)
    ix_out = _biz_col(biz_cfg, "支出", 7)

    rel_mgr = rel.get("manager", "manages")
    rel_ast = rel.get("assists", "assists")
    rel_up = rel.get("upgrade", "upgrades")
    rel_cite = rel.get("cite", "cite")
    rel_prod = rel.get("produce", "produce")

    industries: list[dict[str, Any]] = []
    for biz_id in sorted(affiliations):
        parts = biz_rows.get(biz_id)
        if not parts:
            continue

        manager = ""
        assistants: list[str] = []
        for ep in edges:
            if len(ep) < 4:
                continue
            if ep[2] == rel_mgr and ep[3] == biz_id:
                if ep[1] == plr_id:
                    continue
                if ep[1] in npc_map:
                    manager = npc_map[ep[1]]
                elif not manager:
                    manager = ep[1]
            if ep[2] == rel_ast and ep[3] == biz_id:
                assistants.append(npc_map.get(ep[1], ep[1]))

        libs = _related_libs(edges, biz_id, rel_upgrade=rel_up, rel_cite=rel_cite)
        products = _products_for_biz(
            edges, libs, prd_rows, rel_cite=rel_cite, rel_produce=rel_prod
        )

        def _num(idx: int) -> int:
            if len(parts) <= idx:
                return 0
            try:
                return int(str(parts[idx]).strip())
            except ValueError:
                return 0

        industries.append(
            {
                "id": biz_id,
                "name": parts[ix_name] if len(parts) > ix_name else biz_id,
                "kind": parts[ix_kind] if len(parts) > ix_kind else "",
                "location": parts[ix_loc] if len(parts) > ix_loc else "",
                "cash": _num(ix_cash),
                "debt": _num(ix_debt),
                "income": _num(ix_in),
                "expense": _num(ix_out),
                "plr_role": affiliations[biz_id],
                "manager": manager,
                "assistants": assistants,
                "products": products,
                "actions": [],
            }
        )
    return industries


def read_player_sheet(
    session: str | None,
    *,
    workspace_root_path: str | None = None,
) -> dict[str, Any]:
    if not session:
        return {"exit_code": 2, "errors": ["missing session"], "items": [], "arts": [], "body_stats": []}

    schema = read_catalog_schema(session, workspace_root_path=workspace_root_path)
    plr_id = first_plr_id(session)
    if not plr_id:
        return {"exit_code": 2, "errors": ["no PLR row"], "items": [], "arts": [], "body_stats": []}

    prd_rows = _prd_map(session, schema.production) if schema and schema.production else {}
    prod_links = schema.production.prd_asset_links if schema and schema.production else {}

    items: list[dict[str, Any]] = []
    for parts in list_tag_data_rows(session, "ITM"):
        if len(parts) < 4 or parts[1] != plr_id:
            continue
        item_id, name, qty = parts[0], parts[2], parts[3]
        kind = resolve_item_kind(schema, item_name=name, prd_rows=prd_rows) if schema else "default"
        actions = resolve_item_actions(schema, name=name, kind=kind) if schema else []
        entry: dict[str, Any] = {
            "id": item_id,
            "name": name,
            "qty": qty,
            "kind": kind,
            "actions": actions,
        }
        for prd_id, link in prod_links.items():
            if name in (link.get("itm_names") or []):
                tec_id = link.get("tec_id")
                if tec_id and schema and schema.production:
                    prod = schema.production
                    asset_mode = prod.asset_mode_by_tec.get(tec_id, "installable")
                    if asset_mode != "installable":
                        break
                    key = prod.installed_usr_key.format(tec_id=tec_id)
                    installed = _usr_int(session, key, 0)
                    entry["prd_id"] = prd_id
                    entry["linked_tec"] = tec_id
                    entry["installed"] = installed
                    try:
                        qty_int = int(qty)
                    except ValueError:
                        qty_int = 0
                    if installed < qty_int:
                        install_tpl = schema.production.action_templates.get("install")
                        if install_tpl:
                            actions = list(actions)
                            actions.append(
                                _action_from_template("install", install_tpl, name=name)
                            )
                            entry["actions"] = actions
                break
        items.append(entry)

    art_rows = {row[0]: row for row in list_tag_data_rows(session, "ART")}
    arts: list[dict[str, Any]] = []
    sep = schema.loadout.skills_separator if schema else "、"
    skill_names: list[str] = []
    for parts in list_tag_data_rows(session, "MWU"):
        if len(parts) < 4 or parts[1] != plr_id:
            continue
        mwu_id = parts[0]
        art_id = parts[2]
        rank = parts[3] if len(parts) > 3 else ""
        mastery = parts[4] if len(parts) > 4 else ""
        art_parts = art_rows.get(art_id)
        art_name = art_parts[1] if art_parts and len(art_parts) > 1 else art_id
        martial_actions = (
            resolve_martial_actions(schema, name=art_name) if schema else []
        )
        arts.append(
            {
                "id": mwu_id,
                "art_id": art_id,
                "name": art_name,
                "rank": rank,
                "mastery": mastery,
                "actions": martial_actions,
            }
        )
        skill_names.append(f"{art_name}{rank}")

    body_stats: list[dict[str, Any]] = []
    labels = schema.body_stat_labels if schema else {}
    for parts in list_tag_data_rows(session, "WUX"):
        if len(parts) < 4 or parts[1] != plr_id:
            continue
        slot = parts[2]
        kind = labels.get(slot, slot)
        martial_actions = (
            resolve_martial_actions(schema, name=kind) if schema else []
        )
        body_stats.append(
            {
                "id": parts[0],
                "kind": kind,
                "rank": parts[3] if len(parts) > 3 else "",
                "mastery": parts[4] if len(parts) > 4 else "",
                "actions": martial_actions,
            }
        )

    production_nodes = read_production_nodes(session, schema, workspace_root_path=workspace_root_path) if schema else []
    industries = read_business_industries(session, plr_id, schema)

    return {
        "exit_code": 0,
        "plr_id": plr_id,
        "skills_summary": sep.join(skill_names),
        "items": items,
        "arts": arts,
        "body_stats": body_stats,
        "production": {"industries": industries, "nodes": production_nodes},
        "errors": [],
    }
