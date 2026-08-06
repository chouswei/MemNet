"""Smoke-parse MemNetLayer fixtures. Run from docs/grammar/antlr with generated/ present."""
from __future__ import annotations

import sys
from pathlib import Path

from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "generated"))

from MemNetLayerLexer import MemNetLayerLexer  # noqa: E402
from MemNetLayerParser import MemNetLayerParser  # noqa: E402

SAMPLES = [
    "CST [CST_Blk] ; name=block ; k=2 ; ports=x{side=in, q=1.0},y{side=out} ; law=$y=k x$ ; recycle=persistent\n",
    "E1 [CST_Blk.y] --(bind)--> [CST_Next.x] ; carries=signal\n",
    "E_ab [CST_Rc.a] --(bind)-- [CST_Rc.b] ; carries=q\n",
    "E_ea [CST_Q1.E] <--(bind)--> [CST_Rc.b] ; carries=signal\n",
    "+ CST [CST_Q1] ; name=bjt_npn ; beta=100 ; ports=B{side=in, V=0.7, I=0.001},C{side=out},E{side=inout} ; law=$I_c=\\beta I_b$,$I_e=I_b+I_c$ ; recycle=persistent\n",
    "+ CST [CST_Rc] ; name=Rc ; R=1000 ; ports=a{side=inout},b{side=inout} ; law=$V_a-V_b=I_a R$ ; recycle=persistent\n",
    "+ E_c [CST_Q1.C] --(bind)--> [CST_Rc.a] ; carries=I\n",
    "+ CST [NEW] ; ports=x{side=in, q=$x$},y{side=out}\n",
    "~ [CST_Blk] ; k+=1\n",
    "- E1\n",
]


class _Collect(ErrorListener):
    def __init__(self) -> None:
        super().__init__()
        self.errors: list[str] = []

    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, e):  # noqa: N802
        self.errors.append(f"line {line}:{column} {msg}")


def main() -> int:
    ok = True
    for s in SAMPLES:
        lexer = MemNetLayerLexer(InputStream(s))
        parser = MemNetLayerParser(CommonTokenStream(lexer))
        sink = _Collect()
        parser.removeErrorListeners()
        parser.addErrorListener(sink)
        parser.document()
        n = parser.getNumberOfSyntaxErrors()
        print(("OK" if n == 0 else f"FAIL({n})"), repr(s[:88]))
        for err in sink.errors:
            print(" ", err)
        if n:
            ok = False
    print("OVERALL", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
