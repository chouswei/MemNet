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
    "CST [CST_Blk] ; name=block ; k=2 ; ports=x: {side=in, q=1.0},y: {side=out} ; law=$y=k x$ ; recycle=persistent\n",
    "E1 [CST_Blk.y] --bind--> [CST_Next.x] ; carries=signal\n",
    "E_ab [CST_Rc.a] --bind-- [CST_Rc.b] ; carries=q\n",
    "E_ea [CST_Q1.E] <--bind--> [CST_Rc.b] ; carries=signal\n",
    "+ CST [CST_Q1] ; name=bjt_npn ; beta=100 ; ports=B: {side=in, V=0.7, I=0.001},C: {side=out},E: {side=inout} ; law=$I_C=\\beta I_B$,$I_E=I_B+I_C$ ; recycle=persistent\n",
    "+ CST [CST_Rc] ; name=Rc ; R=1000 ; ports=a: {side=inout},b: {side=inout} ; law=$V_a-V_b=I_a R$,$I_a=-I_b$ ; recycle=persistent\n",
    "+ E_c [CST_Q1.C] --bind--> [CST_Rc.a] ; carries=I\n",
    "+ CST [CST_K1] ; name=relay_spdt ; state=deenergised ; I_th=0.01 ; ports=A1: {side=in, domain=coil, V=0, I=0},A2: {side=in, domain=coil},COM: {side=inout, domain=contact},NO: {side=inout, domain=contact},NC: {side=inout, domain=contact} ; law=$I_{A1}=-I_{A2}$,$s=\\mathbf{1}(\\lvert I_{A1}\\rvert>I_{th})$,$s=1\\Rightarrow V_{\\mathrm{COM}}=V_{\\mathrm{NO}}\\land I_{\\mathrm{COM}}+I_{\\mathrm{NO}}=0\\land I_{\\mathrm{NC}}=0$,$s=0\\Rightarrow V_{\\mathrm{COM}}=V_{\\mathrm{NC}}\\land I_{\\mathrm{COM}}+I_{\\mathrm{NC}}=0\\land I_{\\mathrm{NO}}=0$ ; recycle=persistent\n",
    "+ E_path [CST_K1.COM] --bind-- [CST_K1.NC] ; carries=I\n",
    "+ CST [NEW] ; ports=x: {side=in, q=$x$},y: {side=out}\n",
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
