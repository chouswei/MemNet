// MemNet.g4 — Tier A agent surface (NODE | EDGE lines).
// Normative prose: docs/grammar/memnet-grammar-design.md
// ANTLR notes:    docs/grammar/memnet-grammar-antlr.md
// Tooling:        third_party/antlr4/ (4.13.2); Python twin: docs/grammar/tools/tier_a.py
//
// Conceptual kinds from the visitor / twin: Node | Edge only.
// Uppercase kind spellings (TSK, CLM, …) are IDENT data, not extra kinds.
//
// Id mint: KW_NEW ('NEW') on create node id / create edge id; engine allocates real ids.
// Patch / drop require ground IDENT ids (no KW_NEW).
//
// R1 scope: atom values only (optional quotes; escapes in STRING).
// List/map (; inside one value) = R2 — deferred (see design §5.1 / antlr notes).
// Tier B @TAG pipe is NOT in this grammar (separate codec / front-end).
// focus / caps: MCP/CLI envelope only — not in this body grammar.

grammar MemNet;

document
    : (section | line | NEWLINE)* EOF
    ;

section
    : SECTION_HEAD NEWLINE
    ;

line
    : createNode NEWLINE
    | patchNode NEWLINE
    | createEdge NEWLINE
    | patchEdge NEWLINE
    | dropEdge NEWLINE
    | presentNode NEWLINE     // live pin map (MemNet->LLM): bare present, no mutate op
    | presentEdge NEWLINE
    | lawPin NEWLINE          // warm-prepend invariants; still a Node
    ;

// Create node: id slot KW_NEW (mint) when LLM lacks a ground id.
createNode
    : PLUS IDENT LBRACK idAtom RBRACK (SEMI field)*
    ;

// Update/settle: ground id only — KW_NEW illegal (no match / semantic reject).
patchNode
    : TILDE LBRACK IDENT RBRACK (SEMI field)*
    ;

// Edge forms (Write=display):
//   Mutate known eid:  + E77 [from] --(rel)--> [to] ; …
//   Create mint eid:   + NEW [from] --(rel)--> [to] ; …
//   Shorthand create:  + [from] --(rel)--> [to] ; …   (implicit edge-id mint)
createEdge
    : PLUS edgeIdAtom LBRACK idAtom RBRACK ARROW_L IDENT ARROW_R LBRACK idAtom RBRACK (SEMI field)*
    | PLUS LBRACK idAtom RBRACK ARROW_L IDENT ARROW_R LBRACK idAtom RBRACK (SEMI field)*
    ;

edgeIdAtom
    : KW_NEW
    | IDENT
    ;

// Visitor: bare IDENT on patch/drop should match E[0-9A-Za-z_]+ (edge id); no KW_NEW.
patchEdge
    : TILDE LBRACK IDENT RBRACK ARROW_L IDENT ARROW_R LBRACK IDENT RBRACK (SEMI field)*
    | TILDE IDENT (SEMI field)*
    ;

dropEdge
    : MINUS IDENT
    ;


// Live pin map present (display): no PLUS/TILDE/MINUS. Mutate keeps ops.
presentNode
    : IDENT LBRACK IDENT RBRACK (SEMI field)*
    ;

presentEdge
    : IDENT LBRACK IDENT RBRACK ARROW_L IDENT ARROW_R LBRACK IDENT RBRACK (SEMI field)*
    ;

// First field has NO leading ';' — matches warm LAW lines.
// e.g. LAW01 kind=engine ; text=… ; recycle=persistent
lawPin
    : IDENT field (SEMI field)*
    ;

// Id inside [ … ]: mint keyword or ground identifier.
idAtom
    : KW_NEW
    | IDENT
    ;

field
    : IDENT ASSIGN value
    | IDENT PLUS_EQ NUMBER
    | IDENT MINUS_EQ NUMBER
    ;

// R1: atoms only.
value
    : atom
    ;

atom
    : STRING
    | BARE_ATOM
    | NUMBER
    | KW_NEW
    | IDENT
    ;

// --- lexer ---

SECTION_HEAD : '##' [ \t]+ [A-Za-z][A-Za-z0-9_ ]* ;

PLUS         : '+' ;
TILDE        : '~' ;
MINUS        : '-' ;
LBRACK       : '[' ;
RBRACK       : ']' ;
SEMI         : ';' ;
PLUS_EQ      : '+=' ;   // before ASSIGN
MINUS_EQ     : '-=' ;
ASSIGN       : '=' ;
ARROW_L      : '--(' ;
ARROW_R      : ')-->' ;

// Mint token for create (must precede IDENT so 'NEW' is not absorbed as IDENT).
KW_NEW       : 'NEW' ;

// Quoted atoms; \\ \" \n \r \t escapes (paths with spaces / backslashes).
STRING       : '"' ( ESC_SEQ | ~["\\\r\n] )* '"' ;
fragment ESC_SEQ : '\\' [\\"nrt] ;

NUMBER       : [0-9]+ ('.' [0-9]+)? ;

// One word-class token; visitor classifies kind / id / rel / key / LAW* / E*.
IDENT        : [A-Za-z_][A-Za-z0-9_]* ;

// Multi-word or punctuated atoms without quotes (paths with /, requirement ids).
// Prefer STRING for Windows paths with '\' or spaces. Must not contain ';' or newline.
BARE_ATOM    : [A-Za-z0-9_./+-]+ ([ \t]+ [A-Za-z0-9_./+-]+)* ;

NEWLINE      : '\r'? '\n' ;
WS           : [ \t]+ -> skip ;

// Single-# line notes in fixtures; '##' is SECTION_HEAD (longer / earlier rule).
LINE_COMMENT : '#' ~[#\r\n] ~[\r\n]* -> skip ;
