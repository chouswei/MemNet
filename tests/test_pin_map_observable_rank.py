"""MN-REQ-04.11: pin_map order is Shape observables, not hid / nickname / CREATE."""

from __future__ import annotations

import itertools
import re

from memnet.models import Record
from memnet.mutate_gate import MutateGate
from memnet.observable_rank import node_rank_key, ranked
from memnet.pin_map_composer import PinMapComposer, bounded_match_find
from memnet.session import open_session

_MAP = [
    "SCHEMA TSK ; fields=id slug goal status recycle",
    "SCHEMA USR ; fields=id slug topic status recycle",
]

_ID_PROP = re.compile(r"id:\s*'[^']*'\s*,?\s*")
_TRAILING_COMMA = re.compile(r",\s*}")
_LEADING_COMMA = re.compile(r"\{\s*,")


def _canonical_lines(text: str) -> list[str]:
    """Drop nickname id properties so shuffled nicks can match in order."""
    out: list[str] = []
    for raw in text.splitlines():
        if raw.startswith("##"):
            continue
        line = _ID_PROP.sub("", raw)
        line = _LEADING_COMMA.sub("{", line)
        line = _TRAILING_COMMA.sub("}", line)
        line = re.sub(r"\s+", " ", line).strip()
        if line:
            out.append(line)
    return out


def _graph_stmts(nicks: dict[str, str]) -> list[str]:
    hub, leaf_a, leaf_b, note = nicks["hub"], nicks["a"], nicks["b"], nicks["note"]
    nodes = [
        f"CREATE (:TSK {{id: '{hub}', slug: 'alpha', goal: 'mission', status: 'open'}})",
        f"CREATE (:TSK {{id: '{leaf_a}', slug: 'bravo', goal: 'leaf-a', status: 'open'}})",
        f"CREATE (:TSK {{id: '{leaf_b}', slug: 'charlie', goal: 'leaf-b', status: 'open'}})",
        f"CREATE (:USR {{id: '{note}', slug: 'delta', topic: 'note', status: 'open'}})",
    ]
    edges = [
        "MATCH (x {slug: 'bravo'}), (h {slug: 'alpha'})\nCREATE (x)-[:member_of]->(h)",
        "MATCH (x {slug: 'charlie'}), (h {slug: 'alpha'})\nCREATE (x)-[:member_of]->(h)",
        "MATCH (h {slug: 'alpha'}), (n {slug: 'delta'})\nCREATE (h)-[:next]->(n)",
    ]
    return nodes, edges


def _build_session(memnet_temp, nicks: dict[str, str], node_order, edge_order) -> object:
    del memnet_temp
    ss = open_session(map_lines=list(_MAP))
    nodes, edges = _graph_stmts(nicks)
    stmts = [nodes[i] for i in node_order] + [edges[i] for i in edge_order]
    MutateGate(ss).apply(stmts, mode="add", allow_new_relation=True)
    return ss


def _pin_map(ss) -> tuple[str, list[str]]:
    _rows, text = PinMapComposer(ss).compose(
        anchor=None,
        kind="TSK",
        locators=[("slug", "alpha")],
        depth=2,
        max_rows=50,
    )
    return text, _canonical_lines(text)


def test_rank_key_excludes_hid_and_nickname_id():
    a = Record(tag="TSK", fields={"id": "TSK_aaa", "slug": "alpha", "goal": "mission"})
    b = Record(tag="TSK", fields={"id": "TSK_zzz", "slug": "alpha", "goal": "mission"})
    a.hid = "_el99"
    b.hid = "_el1"
    assert node_rank_key(a) == node_rank_key(b)
    assert "id" not in str(node_rank_key(a))
    ordered = ranked([b, a])
    assert node_rank_key(ordered[0]) == node_rank_key(a)


def test_isomorphic_create_shuffle_same_pin_map_sequence(memnet_temp):
    nick_a = {"hub": "TSK_hub_a", "a": "TSK_leaf_a", "b": "TSK_leaf_b", "note": "USR_note_a"}
    nick_b = {"hub": "TSK_H", "a": "TSK_L1", "b": "TSK_L2", "note": "USR_N"}
    sequences: list[list[str]] = []
    raw_texts: list[str] = []
    node_perms = list(itertools.permutations(range(4)))[:6]
    edge_perms = list(itertools.permutations(range(3)))[:4]
    for nicks in (nick_a, nick_b):
        for node_order in node_perms:
            for edge_order in edge_perms:
                ss = _build_session(memnet_temp, nicks, node_order, edge_order)
                text, canon = _pin_map(ss)
                raw_texts.append(text)
                sequences.append(canon)
                assert "_el" not in text
                assert "_memnet_hid" not in text
    assert sequences
    first = sequences[0]
    assert any("slug: 'bravo'" in line or "slug: 'charlie'" in line for line in first)
    for seq in sequences[1:]:
        assert seq == first
    label_sets = [frozenset(seq) for seq in sequences]
    assert len(set(label_sets)) == 1


def test_find_seed_order_follows_observables_not_hid(memnet_temp):
    ss = _build_session(
        memnet_temp,
        {"hub": "Z_hub", "a": "A_leaf", "b": "M_leaf", "note": "N_note"},
        node_order=(3, 0, 2, 1),
        edge_order=(2, 0, 1),
    )
    found = bounded_match_find(
        ss.store,
        kind="TSK",
        locators=[],
        keyword=None,
        limit=10,
    )
    slugs = [r.fields.get("slug") for r in found.seeds]
    expected = [r.fields.get("slug") for r in ranked(found.seeds)]
    assert slugs == expected
    assert slugs == ["bravo", "charlie", "alpha"]
    assert "id" not in str(node_rank_key(found.seeds[0]))
