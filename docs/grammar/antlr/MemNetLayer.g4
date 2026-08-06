// MemNetLayer.g4 — proposed MemNet 1.x slim multi-layer dialect (design).
// Source prose: docs/grammar/memnet-multi-layer.md
// Sibling R1 stub: docs/grammar/MemNet.g4 (0.3.x directed-only shared dialect).
//
// Scope: NODE | EDGE line shapes with ports=, law=$...$ (NODE only — semantic),
// dual EDGE (bind vs relation), three wire forms, mutate prefixes + / ~ / -.
// No teachable law= on EDGE (fields stay generic; reject in validation).
// Not an evaluator for LaTeX; law is opaque $...$.
//
// Dual EDGE (semantic — same arrow syntax):
//   port ↔ port  → bind / pipe  (label bind|pipe; sense on carries=)
//   node ↔ node  → relation     (label = sense; bare [NodeId] both ends)
//   MUSTNOT: mixed [Node.port] ↔ [Node]; law= on EDGE; bind-as-relation
//
// --- Review notes (ANTLR4 vs human dialect) ---
// 1. Wire disambiguation: tokenise '-->' before '--' (longest match). Left:
//    '<--' vs '--'. Directed and non-directed share ARROW_DASH; right token
//    decides (ARROW_R_DIR vs second ARROW_DASH).
// 2. law= list commas vs LaTeX commas: commas inside LAW_SEG are opaque; only
//    COMMA between closed $...$ segments is the field list joiner. Nested '$'
//    inside maths is out of unquoted form — quote the whole field (STRING).
// 3. Prefer quote when unquoted law would need ';' or a list-joining ',' that is
//    not a segment boundary (locked in multi-layer.md delimiters).
// 4. ports= entry: name: { attr=val, ... } — labelled record bag (TS/YAML-style).
//    COLON joins name to bag; LBRACE/RBRACE hold attrs. Prefer one space after
//    ':' (WS skips it). Demote bare name{...} and name(...).
// 5. COMMA dual role: between port entries vs between attrs inside {…} —
//    parser nesting resolves (portList vs attrList); no lexer mode needed.
// 6. fieldValue: portList before atom — LL(*) needs COLON (then LBRACE) after
//    IDENT to pick portList; single-atom values use the final atom alt.
// 7. Recommended dialect tweak: forbid bare '|' in unquoted values (already
//    prose MUST prefer \lvert/\rvert); keep STRING escape for awkward maths.
// 8. Create-edge optional eid: '+ [A] --bind--> [B]' vs '+ Eid [A] ...' —
//    distinguished by whether token after '+' is LBRACK or IDENT/KW_NEW.
// 9. EDGE endpoints: [Node.port] via IDENT DOT IDENT (bind); plain IDENT
//    (relation / NEW / rare first-class PORT). Soft-validate same grain both
//    ends. Reject mixed; reject from=/to= on EDGE.
// 10. Dialect stays domain-generic; electronics V/I are instance attr keys only.
// 11. BARE_ATOM must not start with +/-/~ or include '+'/'-' (longest-match
//     would steal mutate ops and k+=N). '#' = LINE_COMMENT. Free punct
//     (() & * ^ ! ? ` @ …) held — see memnet-multi-layer.md delimiter inventory.
// 12. Arrow label = bare IDENT (--label--> / --label-- / <--label-->).
//     {} is ports only — demote braced --{label}-->.
//     Bind teach: bind (pipe synonym). Relation: any other IDENT as sense.
//
// Generate (optional): antlr4 -Dlanguage=Python3 -visitor -no-listener MemNetLayer.g4
// British English in this header.

grammar MemNetLayer;

// ---------------------------------------------------------------------------
// Parser
// ---------------------------------------------------------------------------

document
    : (line | NEWLINE)* EOF
    ;

line
    : createNode NEWLINE       # CreateNodeLine
    | patchNode NEWLINE        # PatchNodeLine
    | createEdge NEWLINE       # CreateEdgeLine
    | patchEdge NEWLINE        # PatchEdgeLine
    | dropEdge NEWLINE         # DropEdgeLine
    | presentNode NEWLINE      # PresentNodeLine
    | presentEdge NEWLINE      # PresentEdgeLine
    ;

// Bare present (pin map): KIND [Id] ; key=value ; …
presentNode
    : IDENT LBRACK IDENT RBRACK (SEMI field)*
    ;

// Create: + KIND [NEW|Id] ; …
createNode
    : PLUS IDENT LBRACK idAtom RBRACK (SEMI field)*
    ;

// Update: ~ [Id] ; …   (+= / -= only meaningful here — semantic gate)
patchNode
    : TILDE LBRACK IDENT RBRACK (SEMI field)*
    ;

// Dual EDGE: same three wire forms; grain from endpoints (semantic).
// Bind: [Node.port] --bind--> [Node.port]  (pipe ≡ bind; carries= sense)
// Relation: [NodeA] --knows--> [NodeB]     (label = sense; bare ids)
// No law= on EDGE (semantic). {} ports only — not on arrows.
presentEdge
    : IDENT endpoint edgeWire endpoint (SEMI field)*
    ;

createEdge
    : PLUS edgeIdAtom endpoint edgeWire endpoint (SEMI field)*
    | PLUS endpoint edgeWire endpoint (SEMI field)*
    ;

patchEdge
    : TILDE endpoint edgeWire endpoint (SEMI field)*
    | TILDE IDENT (SEMI field)*
    ;

dropEdge
    : MINUS IDENT
    ;

edgeWire
    : directedEdge      # WireDirected
    | nonDirectedEdge   # WireNonDirected
    | biDirectedEdge    # WireBiDirected
    ;

// IDENT required — rejects -- -->, --a b-->, --k=v-->
directedEdge
    : ARROW_DASH IDENT ARROW_R_DIR
    ;

nonDirectedEdge
    : ARROW_DASH IDENT ARROW_DASH
    ;

biDirectedEdge
    : ARROW_BI_L IDENT ARROW_R_DIR
    ;

endpoint
    : LBRACK endpointAtom RBRACK
    ;

// Bind teach: NodeId.PortName. Plain IDENT = relation / NEW / rare PORT id.
endpointAtom
    : KW_NEW
    | IDENT DOT IDENT
    | IDENT
    ;

idAtom
    : KW_NEW
    | IDENT
    ;

edgeIdAtom
    : KW_NEW
    | IDENT
    ;

field
    : IDENT ASSIGN fieldValue
    | IDENT PLUS_EQ NUMBER
    | IDENT MINUS_EQ NUMBER
    ;

// Structured overlays first; STRING for awkward / quoted whole-field values.
fieldValue
    : STRING                         # ValueString
    | lawList                        # ValueLawList
    | portList                       # ValuePortList
    | atom (COMMA atom)+             # ValueAtomList
    | atom                           # ValueAtom
    ;

lawList
    : LAW_SEG (COMMA LAW_SEG)*
    ;

portList
    : portToken (COMMA portToken)*
    ;

// Teach always name: {…}. Bare name / name{…} / name(…) are not portList entries.
portToken
    : IDENT COLON LBRACE attrList? RBRACE
    ;

attrList
    : attr (COMMA attr)*
    ;

attr
    : IDENT ASSIGN attrValue
    ;

attrValue
    : NUMBER
    | IDENT
    | LAW_SEG
    | STRING
    | BARE_ATOM
    ;

atom
    : STRING
    | NUMBER
    | KW_NEW
    | IDENT
    | BARE_ATOM
    ;

// ---------------------------------------------------------------------------
// Lexer — specific before general; longest match for arrow closers
// ---------------------------------------------------------------------------

PLUS_EQ      : '+=' ;
MINUS_EQ     : '-=' ;
PLUS         : '+' ;
TILDE        : '~' ;
MINUS        : '-' ;

LBRACK       : '[' ;
RBRACK       : ']' ;
LBRACE       : '{' ;   // port bag after name: only (not arrow labels)
RBRACE       : '}' ;
SEMI         : ';' ;
ASSIGN       : '=' ;
COLON        : ':' ;   // port name-to-bag join; also id:label elsewhere
DOT          : '.' ;
COMMA        : ',' ;

// EDGE wire fragments (order: bi-left before dash; dir-right before dash).
// Bare IDENT between dashes. () fully free. <-- / --> = direction marks only
// (not Dirac; Dirac in LAW_SEG). Demote braced --{label}-->.
ARROW_BI_L   : '<--' ;
ARROW_R_DIR  : '-->' ;   // must precede ARROW_DASH
ARROW_DASH   : '--' ;

KW_NEW       : 'NEW' ;

// Inline LaTeX math segment: $…$ (opaque; may hold ',', '=', ':', spaces, Greek macros)
// Unquoted form MUST NOT contain '$', ';', or newline. Nested '$' → use STRING field.
LAW_SEG      : '$' (~[$\r\n;])* '$' ;

STRING       : '"' ( ESC_SEQ | ~["\\\r\n] )* '"' ;
fragment ESC_SEQ : '\\' [\\"nrt] ;

NUMBER       : [0-9]+ ('.' [0-9]+)? ;

IDENT        : [A-Za-z_][A-Za-z0-9_]* ;

// Paths / punctuated atoms without quotes. Must NOT start with + - ~ or absorb
// '+='/'-=' tails (longest-match would steal mutate ops / PLUS_EQ). Dot reserved
// for [Node.port] (DOT). Quote awkward paths (spaces, '.', '+', '-').
BARE_ATOM    : [A-Za-z0-9_/]+ ([ \t]+ [A-Za-z0-9_/]+)* ;

NEWLINE      : '\r'? '\n' ;
WS           : [ \t]+ -> skip ;

LINE_COMMENT : '#' ~[\r\n]* -> skip ;
