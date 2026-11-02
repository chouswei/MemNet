"""MN-VER-14-D02 defect repro: relationship WHERE + SET is refused as DELETE.

DEFECT D02 (not a fix). On today's engine a single GQL statement that puts a
WHERE on a relationship pattern and then SETs a relationship property is
refused unsupported_predicate with a message about relationship DELETE, though
the statement has no DELETE. MN-REQ-03.4 asks for honour-or-refuse with an
accurate code. This test documents the misleading refusal and passes on
today's engine; the planned fix (WhereSetRefusalFix) flips it.

Node WHERE + SET (MATCH (n:X) WHERE n.k = 'a' SET n.v = 'b') is honoured today
(tests/test_engine_roundtrip_where_acl.py), so it is not the defect.
"""

from __future__ import annotations

import pytest

from memnet.exceptions import MemNetError
from memnet.mutate_gate import MutateGate
from memnet.session import open_session

D02_STATEMENTS = [
    "MATCH ()-[r:links]-() WHERE r.kind = 'a' SET r.kind = 'b'",
    "MATCH (a)-[r:links]->(b) WHERE r.kind = 'a' SET r.kind = 'b'",
    "MATCH ()-[r {id: 'E1'}]-() WHERE r.kind = 'a' SET r.kind = 'b'",
]


@pytest.mark.parametrize("statement", D02_STATEMENTS)
def test_d02_relationship_where_set_refused_with_delete_message(
    memnet_temp, schema_file, statement
):
    """D02 defect repro: WHERE + SET on a relationship is refused naming DELETE."""
    ss = open_session(map_file=str(schema_file))
    with pytest.raises(MemNetError) as ei:
        MutateGate(ss).apply([statement], mode="mutate")
    assert ei.value.code == "unsupported_predicate"
    msg = str(ei.value)
    assert "DELETE" in msg, f"D02 repro: refusal no longer names DELETE: {msg!r}"
    assert "SET" not in msg
    assert "DELETE" not in statement.upper()
