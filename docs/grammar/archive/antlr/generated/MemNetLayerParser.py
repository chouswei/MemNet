# Generated from MemNetLayer.g4 by ANTLR 4.13.2
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,27,320,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,2,4,7,4,2,5,7,5,2,6,7,
        6,2,7,7,7,2,8,7,8,2,9,7,9,2,10,7,10,2,11,7,11,2,12,7,12,2,13,7,13,
        2,14,7,14,2,15,7,15,2,16,7,16,2,17,7,17,2,18,7,18,2,19,7,19,2,20,
        7,20,2,21,7,21,2,22,7,22,2,23,7,23,2,24,7,24,2,25,7,25,2,26,7,26,
        2,27,7,27,2,28,7,28,2,29,7,29,2,30,7,30,1,0,1,0,5,0,65,8,0,10,0,
        12,0,68,9,0,1,0,1,0,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,
        1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,1,93,8,1,1,2,1,2,1,2,1,
        2,1,2,1,2,5,2,101,8,2,10,2,12,2,104,9,2,1,3,1,3,1,3,1,3,1,3,1,3,
        1,3,5,3,113,8,3,10,3,12,3,116,9,3,1,4,1,4,1,4,1,4,1,4,1,4,5,4,124,
        8,4,10,4,12,4,127,9,4,1,5,1,5,1,5,1,5,1,5,1,5,5,5,135,8,5,10,5,12,
        5,138,9,5,1,6,1,6,1,6,1,6,1,6,1,6,1,6,5,6,147,8,6,10,6,12,6,150,
        9,6,1,6,1,6,1,6,1,6,1,6,1,6,5,6,158,8,6,10,6,12,6,161,9,6,3,6,163,
        8,6,1,7,1,7,1,7,1,7,1,7,1,7,5,7,171,8,7,10,7,12,7,174,9,7,1,7,1,
        7,1,7,1,7,5,7,180,8,7,10,7,12,7,183,9,7,3,7,185,8,7,1,8,1,8,1,8,
        1,9,1,9,1,9,3,9,193,8,9,1,10,1,10,1,10,1,10,1,11,1,11,1,11,1,11,
        1,12,1,12,1,12,1,12,1,13,1,13,1,13,1,13,1,14,1,14,1,14,1,14,1,14,
        3,14,216,8,14,1,15,1,15,1,16,1,16,1,17,1,17,1,17,1,17,1,17,1,17,
        1,17,1,17,1,17,3,17,231,8,17,1,18,1,18,1,18,1,18,1,18,1,18,1,18,
        4,18,240,8,18,11,18,12,18,241,1,18,3,18,245,8,18,1,19,1,19,1,19,
        5,19,250,8,19,10,19,12,19,253,9,19,1,20,1,20,1,20,5,20,258,8,20,
        10,20,12,20,261,9,20,1,21,1,21,1,21,1,21,3,21,267,8,21,1,21,1,21,
        1,22,1,22,3,22,273,8,22,1,22,1,22,1,23,1,23,1,23,5,23,280,8,23,10,
        23,12,23,283,9,23,1,24,1,24,1,24,1,24,1,25,1,25,1,25,1,25,1,25,1,
        25,1,25,3,25,296,8,25,1,26,1,26,3,26,300,8,26,1,26,1,26,1,27,1,27,
        1,27,5,27,307,8,27,10,27,12,27,310,9,27,1,28,1,28,1,28,1,28,1,29,
        1,29,1,30,1,30,1,30,0,0,31,0,2,4,6,8,10,12,14,16,18,20,22,24,26,
        28,30,32,34,36,38,40,42,44,46,48,50,52,54,56,58,60,0,3,2,0,18,18,
        23,23,1,0,19,24,2,0,18,18,21,24,331,0,66,1,0,0,0,2,92,1,0,0,0,4,
        94,1,0,0,0,6,105,1,0,0,0,8,117,1,0,0,0,10,128,1,0,0,0,12,162,1,0,
        0,0,14,184,1,0,0,0,16,186,1,0,0,0,18,192,1,0,0,0,20,194,1,0,0,0,
        22,198,1,0,0,0,24,202,1,0,0,0,26,206,1,0,0,0,28,215,1,0,0,0,30,217,
        1,0,0,0,32,219,1,0,0,0,34,230,1,0,0,0,36,244,1,0,0,0,38,246,1,0,
        0,0,40,254,1,0,0,0,42,262,1,0,0,0,44,270,1,0,0,0,46,276,1,0,0,0,
        48,284,1,0,0,0,50,295,1,0,0,0,52,297,1,0,0,0,54,303,1,0,0,0,56,311,
        1,0,0,0,58,315,1,0,0,0,60,317,1,0,0,0,62,65,3,2,1,0,63,65,5,25,0,
        0,64,62,1,0,0,0,64,63,1,0,0,0,65,68,1,0,0,0,66,64,1,0,0,0,66,67,
        1,0,0,0,67,69,1,0,0,0,68,66,1,0,0,0,69,70,5,0,0,1,70,1,1,0,0,0,71,
        72,3,6,3,0,72,73,5,25,0,0,73,93,1,0,0,0,74,75,3,8,4,0,75,76,5,25,
        0,0,76,93,1,0,0,0,77,78,3,12,6,0,78,79,5,25,0,0,79,93,1,0,0,0,80,
        81,3,14,7,0,81,82,5,25,0,0,82,93,1,0,0,0,83,84,3,16,8,0,84,85,5,
        25,0,0,85,93,1,0,0,0,86,87,3,4,2,0,87,88,5,25,0,0,88,93,1,0,0,0,
        89,90,3,10,5,0,90,91,5,25,0,0,91,93,1,0,0,0,92,71,1,0,0,0,92,74,
        1,0,0,0,92,77,1,0,0,0,92,80,1,0,0,0,92,83,1,0,0,0,92,86,1,0,0,0,
        92,89,1,0,0,0,93,3,1,0,0,0,94,95,5,23,0,0,95,96,5,6,0,0,96,97,5,
        23,0,0,97,102,5,7,0,0,98,99,5,10,0,0,99,101,3,34,17,0,100,98,1,0,
        0,0,101,104,1,0,0,0,102,100,1,0,0,0,102,103,1,0,0,0,103,5,1,0,0,
        0,104,102,1,0,0,0,105,106,5,3,0,0,106,107,5,23,0,0,107,108,5,6,0,
        0,108,109,3,30,15,0,109,114,5,7,0,0,110,111,5,10,0,0,111,113,3,34,
        17,0,112,110,1,0,0,0,113,116,1,0,0,0,114,112,1,0,0,0,114,115,1,0,
        0,0,115,7,1,0,0,0,116,114,1,0,0,0,117,118,5,4,0,0,118,119,5,6,0,
        0,119,120,5,23,0,0,120,125,5,7,0,0,121,122,5,10,0,0,122,124,3,34,
        17,0,123,121,1,0,0,0,124,127,1,0,0,0,125,123,1,0,0,0,125,126,1,0,
        0,0,126,9,1,0,0,0,127,125,1,0,0,0,128,129,5,23,0,0,129,130,3,26,
        13,0,130,131,3,18,9,0,131,136,3,26,13,0,132,133,5,10,0,0,133,135,
        3,34,17,0,134,132,1,0,0,0,135,138,1,0,0,0,136,134,1,0,0,0,136,137,
        1,0,0,0,137,11,1,0,0,0,138,136,1,0,0,0,139,140,5,3,0,0,140,141,3,
        32,16,0,141,142,3,26,13,0,142,143,3,18,9,0,143,148,3,26,13,0,144,
        145,5,10,0,0,145,147,3,34,17,0,146,144,1,0,0,0,147,150,1,0,0,0,148,
        146,1,0,0,0,148,149,1,0,0,0,149,163,1,0,0,0,150,148,1,0,0,0,151,
        152,5,3,0,0,152,153,3,26,13,0,153,154,3,18,9,0,154,159,3,26,13,0,
        155,156,5,10,0,0,156,158,3,34,17,0,157,155,1,0,0,0,158,161,1,0,0,
        0,159,157,1,0,0,0,159,160,1,0,0,0,160,163,1,0,0,0,161,159,1,0,0,
        0,162,139,1,0,0,0,162,151,1,0,0,0,163,13,1,0,0,0,164,165,5,4,0,0,
        165,166,3,26,13,0,166,167,3,18,9,0,167,172,3,26,13,0,168,169,5,10,
        0,0,169,171,3,34,17,0,170,168,1,0,0,0,171,174,1,0,0,0,172,170,1,
        0,0,0,172,173,1,0,0,0,173,185,1,0,0,0,174,172,1,0,0,0,175,176,5,
        4,0,0,176,181,5,23,0,0,177,178,5,10,0,0,178,180,3,34,17,0,179,177,
        1,0,0,0,180,183,1,0,0,0,181,179,1,0,0,0,181,182,1,0,0,0,182,185,
        1,0,0,0,183,181,1,0,0,0,184,164,1,0,0,0,184,175,1,0,0,0,185,15,1,
        0,0,0,186,187,5,5,0,0,187,188,5,23,0,0,188,17,1,0,0,0,189,193,3,
        20,10,0,190,193,3,22,11,0,191,193,3,24,12,0,192,189,1,0,0,0,192,
        190,1,0,0,0,192,191,1,0,0,0,193,19,1,0,0,0,194,195,5,17,0,0,195,
        196,5,23,0,0,196,197,5,16,0,0,197,21,1,0,0,0,198,199,5,17,0,0,199,
        200,5,23,0,0,200,201,5,17,0,0,201,23,1,0,0,0,202,203,5,15,0,0,203,
        204,5,23,0,0,204,205,5,16,0,0,205,25,1,0,0,0,206,207,5,6,0,0,207,
        208,3,28,14,0,208,209,5,7,0,0,209,27,1,0,0,0,210,216,5,18,0,0,211,
        212,5,23,0,0,212,213,5,13,0,0,213,216,5,23,0,0,214,216,5,23,0,0,
        215,210,1,0,0,0,215,211,1,0,0,0,215,214,1,0,0,0,216,29,1,0,0,0,217,
        218,7,0,0,0,218,31,1,0,0,0,219,220,7,0,0,0,220,33,1,0,0,0,221,222,
        5,23,0,0,222,223,5,11,0,0,223,231,3,36,18,0,224,225,5,23,0,0,225,
        226,5,1,0,0,226,231,5,22,0,0,227,228,5,23,0,0,228,229,5,2,0,0,229,
        231,5,22,0,0,230,221,1,0,0,0,230,224,1,0,0,0,230,227,1,0,0,0,231,
        35,1,0,0,0,232,245,5,21,0,0,233,245,3,38,19,0,234,245,3,40,20,0,
        235,245,3,44,22,0,236,239,3,60,30,0,237,238,5,14,0,0,238,240,3,60,
        30,0,239,237,1,0,0,0,240,241,1,0,0,0,241,239,1,0,0,0,241,242,1,0,
        0,0,242,245,1,0,0,0,243,245,3,60,30,0,244,232,1,0,0,0,244,233,1,
        0,0,0,244,234,1,0,0,0,244,235,1,0,0,0,244,236,1,0,0,0,244,243,1,
        0,0,0,245,37,1,0,0,0,246,251,5,20,0,0,247,248,5,14,0,0,248,250,5,
        20,0,0,249,247,1,0,0,0,250,253,1,0,0,0,251,249,1,0,0,0,251,252,1,
        0,0,0,252,39,1,0,0,0,253,251,1,0,0,0,254,259,3,42,21,0,255,256,5,
        14,0,0,256,258,3,42,21,0,257,255,1,0,0,0,258,261,1,0,0,0,259,257,
        1,0,0,0,259,260,1,0,0,0,260,41,1,0,0,0,261,259,1,0,0,0,262,263,5,
        23,0,0,263,264,5,12,0,0,264,266,5,8,0,0,265,267,3,46,23,0,266,265,
        1,0,0,0,266,267,1,0,0,0,267,268,1,0,0,0,268,269,5,9,0,0,269,43,1,
        0,0,0,270,272,5,8,0,0,271,273,3,46,23,0,272,271,1,0,0,0,272,273,
        1,0,0,0,273,274,1,0,0,0,274,275,5,9,0,0,275,45,1,0,0,0,276,281,3,
        48,24,0,277,278,5,14,0,0,278,280,3,48,24,0,279,277,1,0,0,0,280,283,
        1,0,0,0,281,279,1,0,0,0,281,282,1,0,0,0,282,47,1,0,0,0,283,281,1,
        0,0,0,284,285,5,23,0,0,285,286,5,11,0,0,286,287,3,50,25,0,287,49,
        1,0,0,0,288,296,5,22,0,0,289,296,5,23,0,0,290,296,5,19,0,0,291,296,
        5,20,0,0,292,296,5,21,0,0,293,296,5,24,0,0,294,296,3,52,26,0,295,
        288,1,0,0,0,295,289,1,0,0,0,295,290,1,0,0,0,295,291,1,0,0,0,295,
        292,1,0,0,0,295,293,1,0,0,0,295,294,1,0,0,0,296,51,1,0,0,0,297,299,
        5,8,0,0,298,300,3,54,27,0,299,298,1,0,0,0,299,300,1,0,0,0,300,301,
        1,0,0,0,301,302,5,9,0,0,302,53,1,0,0,0,303,308,3,56,28,0,304,305,
        5,14,0,0,305,307,3,56,28,0,306,304,1,0,0,0,307,310,1,0,0,0,308,306,
        1,0,0,0,308,309,1,0,0,0,309,55,1,0,0,0,310,308,1,0,0,0,311,312,5,
        23,0,0,312,313,5,11,0,0,313,314,3,58,29,0,314,57,1,0,0,0,315,316,
        7,1,0,0,316,59,1,0,0,0,317,318,7,2,0,0,318,61,1,0,0,0,26,64,66,92,
        102,114,125,136,148,159,162,172,181,184,192,215,230,241,244,251,
        259,266,272,281,295,299,308
    ]

class MemNetLayerParser ( Parser ):

    grammarFileName = "MemNetLayer.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "'+='", "'-='", "'+'", "'~'", "'-'", "'['", 
                     "']'", "'{'", "'}'", "';'", "'='", "':'", "'.'", "','", 
                     "'<--'", "'-->'", "'--'", "'NEW'" ]

    symbolicNames = [ "<INVALID>", "PLUS_EQ", "MINUS_EQ", "PLUS", "TILDE", 
                      "MINUS", "LBRACK", "RBRACK", "LBRACE", "RBRACE", "SEMI", 
                      "ASSIGN", "COLON", "DOT", "COMMA", "ARROW_BI_L", "ARROW_R_DIR", 
                      "ARROW_DASH", "KW_NEW", "ALIAS_REF", "LAW_SEG", "STRING", 
                      "NUMBER", "IDENT", "BARE_ATOM", "NEWLINE", "WS", "LINE_COMMENT" ]

    RULE_document = 0
    RULE_line = 1
    RULE_presentNode = 2
    RULE_createNode = 3
    RULE_patchNode = 4
    RULE_presentEdge = 5
    RULE_createEdge = 6
    RULE_patchEdge = 7
    RULE_dropEdge = 8
    RULE_edgeWire = 9
    RULE_directedEdge = 10
    RULE_nonDirectedEdge = 11
    RULE_biDirectedEdge = 12
    RULE_endpoint = 13
    RULE_endpointAtom = 14
    RULE_idAtom = 15
    RULE_edgeIdAtom = 16
    RULE_field = 17
    RULE_fieldValue = 18
    RULE_lawList = 19
    RULE_portList = 20
    RULE_portToken = 21
    RULE_recordBag = 22
    RULE_attrList = 23
    RULE_attr = 24
    RULE_attrValue = 25
    RULE_nestedRecord = 26
    RULE_flatAttrList = 27
    RULE_flatAttr = 28
    RULE_flatAttrValue = 29
    RULE_atom = 30

    ruleNames =  [ "document", "line", "presentNode", "createNode", "patchNode", 
                   "presentEdge", "createEdge", "patchEdge", "dropEdge", 
                   "edgeWire", "directedEdge", "nonDirectedEdge", "biDirectedEdge", 
                   "endpoint", "endpointAtom", "idAtom", "edgeIdAtom", "field", 
                   "fieldValue", "lawList", "portList", "portToken", "recordBag", 
                   "attrList", "attr", "attrValue", "nestedRecord", "flatAttrList", 
                   "flatAttr", "flatAttrValue", "atom" ]

    EOF = Token.EOF
    PLUS_EQ=1
    MINUS_EQ=2
    PLUS=3
    TILDE=4
    MINUS=5
    LBRACK=6
    RBRACK=7
    LBRACE=8
    RBRACE=9
    SEMI=10
    ASSIGN=11
    COLON=12
    DOT=13
    COMMA=14
    ARROW_BI_L=15
    ARROW_R_DIR=16
    ARROW_DASH=17
    KW_NEW=18
    ALIAS_REF=19
    LAW_SEG=20
    STRING=21
    NUMBER=22
    IDENT=23
    BARE_ATOM=24
    NEWLINE=25
    WS=26
    LINE_COMMENT=27

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.13.2")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class DocumentContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def EOF(self):
            return self.getToken(MemNetLayerParser.EOF, 0)

        def line(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(MemNetLayerParser.LineContext)
            else:
                return self.getTypedRuleContext(MemNetLayerParser.LineContext,i)


        def NEWLINE(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.NEWLINE)
            else:
                return self.getToken(MemNetLayerParser.NEWLINE, i)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_document

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDocument" ):
                return visitor.visitDocument(self)
            else:
                return visitor.visitChildren(self)




    def document(self):

        localctx = MemNetLayerParser.DocumentContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_document)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 66
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while (((_la) & ~0x3f) == 0 and ((1 << _la) & 41943096) != 0):
                self.state = 64
                self._errHandler.sync(self)
                token = self._input.LA(1)
                if token in [3, 4, 5, 23]:
                    self.state = 62
                    self.line()
                    pass
                elif token in [25]:
                    self.state = 63
                    self.match(MemNetLayerParser.NEWLINE)
                    pass
                else:
                    raise NoViableAltException(self)

                self.state = 68
                self._errHandler.sync(self)
                _la = self._input.LA(1)

            self.state = 69
            self.match(MemNetLayerParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LineContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return MemNetLayerParser.RULE_line

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class CreateNodeLineContext(LineContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.LineContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def createNode(self):
            return self.getTypedRuleContext(MemNetLayerParser.CreateNodeContext,0)

        def NEWLINE(self):
            return self.getToken(MemNetLayerParser.NEWLINE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCreateNodeLine" ):
                return visitor.visitCreateNodeLine(self)
            else:
                return visitor.visitChildren(self)


    class PatchNodeLineContext(LineContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.LineContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def patchNode(self):
            return self.getTypedRuleContext(MemNetLayerParser.PatchNodeContext,0)

        def NEWLINE(self):
            return self.getToken(MemNetLayerParser.NEWLINE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPatchNodeLine" ):
                return visitor.visitPatchNodeLine(self)
            else:
                return visitor.visitChildren(self)


    class PatchEdgeLineContext(LineContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.LineContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def patchEdge(self):
            return self.getTypedRuleContext(MemNetLayerParser.PatchEdgeContext,0)

        def NEWLINE(self):
            return self.getToken(MemNetLayerParser.NEWLINE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPatchEdgeLine" ):
                return visitor.visitPatchEdgeLine(self)
            else:
                return visitor.visitChildren(self)


    class DropEdgeLineContext(LineContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.LineContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def dropEdge(self):
            return self.getTypedRuleContext(MemNetLayerParser.DropEdgeContext,0)

        def NEWLINE(self):
            return self.getToken(MemNetLayerParser.NEWLINE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDropEdgeLine" ):
                return visitor.visitDropEdgeLine(self)
            else:
                return visitor.visitChildren(self)


    class PresentNodeLineContext(LineContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.LineContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def presentNode(self):
            return self.getTypedRuleContext(MemNetLayerParser.PresentNodeContext,0)

        def NEWLINE(self):
            return self.getToken(MemNetLayerParser.NEWLINE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPresentNodeLine" ):
                return visitor.visitPresentNodeLine(self)
            else:
                return visitor.visitChildren(self)


    class PresentEdgeLineContext(LineContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.LineContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def presentEdge(self):
            return self.getTypedRuleContext(MemNetLayerParser.PresentEdgeContext,0)

        def NEWLINE(self):
            return self.getToken(MemNetLayerParser.NEWLINE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPresentEdgeLine" ):
                return visitor.visitPresentEdgeLine(self)
            else:
                return visitor.visitChildren(self)


    class CreateEdgeLineContext(LineContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.LineContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def createEdge(self):
            return self.getTypedRuleContext(MemNetLayerParser.CreateEdgeContext,0)

        def NEWLINE(self):
            return self.getToken(MemNetLayerParser.NEWLINE, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCreateEdgeLine" ):
                return visitor.visitCreateEdgeLine(self)
            else:
                return visitor.visitChildren(self)



    def line(self):

        localctx = MemNetLayerParser.LineContext(self, self._ctx, self.state)
        self.enterRule(localctx, 2, self.RULE_line)
        try:
            self.state = 92
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,2,self._ctx)
            if la_ == 1:
                localctx = MemNetLayerParser.CreateNodeLineContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 71
                self.createNode()
                self.state = 72
                self.match(MemNetLayerParser.NEWLINE)
                pass

            elif la_ == 2:
                localctx = MemNetLayerParser.PatchNodeLineContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 74
                self.patchNode()
                self.state = 75
                self.match(MemNetLayerParser.NEWLINE)
                pass

            elif la_ == 3:
                localctx = MemNetLayerParser.CreateEdgeLineContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 77
                self.createEdge()
                self.state = 78
                self.match(MemNetLayerParser.NEWLINE)
                pass

            elif la_ == 4:
                localctx = MemNetLayerParser.PatchEdgeLineContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 80
                self.patchEdge()
                self.state = 81
                self.match(MemNetLayerParser.NEWLINE)
                pass

            elif la_ == 5:
                localctx = MemNetLayerParser.DropEdgeLineContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 83
                self.dropEdge()
                self.state = 84
                self.match(MemNetLayerParser.NEWLINE)
                pass

            elif la_ == 6:
                localctx = MemNetLayerParser.PresentNodeLineContext(self, localctx)
                self.enterOuterAlt(localctx, 6)
                self.state = 86
                self.presentNode()
                self.state = 87
                self.match(MemNetLayerParser.NEWLINE)
                pass

            elif la_ == 7:
                localctx = MemNetLayerParser.PresentEdgeLineContext(self, localctx)
                self.enterOuterAlt(localctx, 7)
                self.state = 89
                self.presentEdge()
                self.state = 90
                self.match(MemNetLayerParser.NEWLINE)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PresentNodeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENT(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.IDENT)
            else:
                return self.getToken(MemNetLayerParser.IDENT, i)

        def LBRACK(self):
            return self.getToken(MemNetLayerParser.LBRACK, 0)

        def RBRACK(self):
            return self.getToken(MemNetLayerParser.RBRACK, 0)

        def SEMI(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.SEMI)
            else:
                return self.getToken(MemNetLayerParser.SEMI, i)

        def field(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(MemNetLayerParser.FieldContext)
            else:
                return self.getTypedRuleContext(MemNetLayerParser.FieldContext,i)


        def getRuleIndex(self):
            return MemNetLayerParser.RULE_presentNode

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPresentNode" ):
                return visitor.visitPresentNode(self)
            else:
                return visitor.visitChildren(self)




    def presentNode(self):

        localctx = MemNetLayerParser.PresentNodeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 4, self.RULE_presentNode)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 94
            self.match(MemNetLayerParser.IDENT)
            self.state = 95
            self.match(MemNetLayerParser.LBRACK)
            self.state = 96
            self.match(MemNetLayerParser.IDENT)
            self.state = 97
            self.match(MemNetLayerParser.RBRACK)
            self.state = 102
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==10:
                self.state = 98
                self.match(MemNetLayerParser.SEMI)
                self.state = 99
                self.field()
                self.state = 104
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CreateNodeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def PLUS(self):
            return self.getToken(MemNetLayerParser.PLUS, 0)

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def LBRACK(self):
            return self.getToken(MemNetLayerParser.LBRACK, 0)

        def idAtom(self):
            return self.getTypedRuleContext(MemNetLayerParser.IdAtomContext,0)


        def RBRACK(self):
            return self.getToken(MemNetLayerParser.RBRACK, 0)

        def SEMI(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.SEMI)
            else:
                return self.getToken(MemNetLayerParser.SEMI, i)

        def field(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(MemNetLayerParser.FieldContext)
            else:
                return self.getTypedRuleContext(MemNetLayerParser.FieldContext,i)


        def getRuleIndex(self):
            return MemNetLayerParser.RULE_createNode

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCreateNode" ):
                return visitor.visitCreateNode(self)
            else:
                return visitor.visitChildren(self)




    def createNode(self):

        localctx = MemNetLayerParser.CreateNodeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 6, self.RULE_createNode)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 105
            self.match(MemNetLayerParser.PLUS)
            self.state = 106
            self.match(MemNetLayerParser.IDENT)
            self.state = 107
            self.match(MemNetLayerParser.LBRACK)
            self.state = 108
            self.idAtom()
            self.state = 109
            self.match(MemNetLayerParser.RBRACK)
            self.state = 114
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==10:
                self.state = 110
                self.match(MemNetLayerParser.SEMI)
                self.state = 111
                self.field()
                self.state = 116
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PatchNodeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def TILDE(self):
            return self.getToken(MemNetLayerParser.TILDE, 0)

        def LBRACK(self):
            return self.getToken(MemNetLayerParser.LBRACK, 0)

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def RBRACK(self):
            return self.getToken(MemNetLayerParser.RBRACK, 0)

        def SEMI(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.SEMI)
            else:
                return self.getToken(MemNetLayerParser.SEMI, i)

        def field(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(MemNetLayerParser.FieldContext)
            else:
                return self.getTypedRuleContext(MemNetLayerParser.FieldContext,i)


        def getRuleIndex(self):
            return MemNetLayerParser.RULE_patchNode

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPatchNode" ):
                return visitor.visitPatchNode(self)
            else:
                return visitor.visitChildren(self)




    def patchNode(self):

        localctx = MemNetLayerParser.PatchNodeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 8, self.RULE_patchNode)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 117
            self.match(MemNetLayerParser.TILDE)
            self.state = 118
            self.match(MemNetLayerParser.LBRACK)
            self.state = 119
            self.match(MemNetLayerParser.IDENT)
            self.state = 120
            self.match(MemNetLayerParser.RBRACK)
            self.state = 125
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==10:
                self.state = 121
                self.match(MemNetLayerParser.SEMI)
                self.state = 122
                self.field()
                self.state = 127
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PresentEdgeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def endpoint(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(MemNetLayerParser.EndpointContext)
            else:
                return self.getTypedRuleContext(MemNetLayerParser.EndpointContext,i)


        def edgeWire(self):
            return self.getTypedRuleContext(MemNetLayerParser.EdgeWireContext,0)


        def SEMI(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.SEMI)
            else:
                return self.getToken(MemNetLayerParser.SEMI, i)

        def field(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(MemNetLayerParser.FieldContext)
            else:
                return self.getTypedRuleContext(MemNetLayerParser.FieldContext,i)


        def getRuleIndex(self):
            return MemNetLayerParser.RULE_presentEdge

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPresentEdge" ):
                return visitor.visitPresentEdge(self)
            else:
                return visitor.visitChildren(self)




    def presentEdge(self):

        localctx = MemNetLayerParser.PresentEdgeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 10, self.RULE_presentEdge)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 128
            self.match(MemNetLayerParser.IDENT)
            self.state = 129
            self.endpoint()
            self.state = 130
            self.edgeWire()
            self.state = 131
            self.endpoint()
            self.state = 136
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==10:
                self.state = 132
                self.match(MemNetLayerParser.SEMI)
                self.state = 133
                self.field()
                self.state = 138
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class CreateEdgeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def PLUS(self):
            return self.getToken(MemNetLayerParser.PLUS, 0)

        def edgeIdAtom(self):
            return self.getTypedRuleContext(MemNetLayerParser.EdgeIdAtomContext,0)


        def endpoint(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(MemNetLayerParser.EndpointContext)
            else:
                return self.getTypedRuleContext(MemNetLayerParser.EndpointContext,i)


        def edgeWire(self):
            return self.getTypedRuleContext(MemNetLayerParser.EdgeWireContext,0)


        def SEMI(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.SEMI)
            else:
                return self.getToken(MemNetLayerParser.SEMI, i)

        def field(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(MemNetLayerParser.FieldContext)
            else:
                return self.getTypedRuleContext(MemNetLayerParser.FieldContext,i)


        def getRuleIndex(self):
            return MemNetLayerParser.RULE_createEdge

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitCreateEdge" ):
                return visitor.visitCreateEdge(self)
            else:
                return visitor.visitChildren(self)




    def createEdge(self):

        localctx = MemNetLayerParser.CreateEdgeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 12, self.RULE_createEdge)
        self._la = 0 # Token type
        try:
            self.state = 162
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,9,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 139
                self.match(MemNetLayerParser.PLUS)
                self.state = 140
                self.edgeIdAtom()
                self.state = 141
                self.endpoint()
                self.state = 142
                self.edgeWire()
                self.state = 143
                self.endpoint()
                self.state = 148
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==10:
                    self.state = 144
                    self.match(MemNetLayerParser.SEMI)
                    self.state = 145
                    self.field()
                    self.state = 150
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 151
                self.match(MemNetLayerParser.PLUS)
                self.state = 152
                self.endpoint()
                self.state = 153
                self.edgeWire()
                self.state = 154
                self.endpoint()
                self.state = 159
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==10:
                    self.state = 155
                    self.match(MemNetLayerParser.SEMI)
                    self.state = 156
                    self.field()
                    self.state = 161
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PatchEdgeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def TILDE(self):
            return self.getToken(MemNetLayerParser.TILDE, 0)

        def endpoint(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(MemNetLayerParser.EndpointContext)
            else:
                return self.getTypedRuleContext(MemNetLayerParser.EndpointContext,i)


        def edgeWire(self):
            return self.getTypedRuleContext(MemNetLayerParser.EdgeWireContext,0)


        def SEMI(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.SEMI)
            else:
                return self.getToken(MemNetLayerParser.SEMI, i)

        def field(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(MemNetLayerParser.FieldContext)
            else:
                return self.getTypedRuleContext(MemNetLayerParser.FieldContext,i)


        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_patchEdge

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPatchEdge" ):
                return visitor.visitPatchEdge(self)
            else:
                return visitor.visitChildren(self)




    def patchEdge(self):

        localctx = MemNetLayerParser.PatchEdgeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 14, self.RULE_patchEdge)
        self._la = 0 # Token type
        try:
            self.state = 184
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,12,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 164
                self.match(MemNetLayerParser.TILDE)
                self.state = 165
                self.endpoint()
                self.state = 166
                self.edgeWire()
                self.state = 167
                self.endpoint()
                self.state = 172
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==10:
                    self.state = 168
                    self.match(MemNetLayerParser.SEMI)
                    self.state = 169
                    self.field()
                    self.state = 174
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 175
                self.match(MemNetLayerParser.TILDE)
                self.state = 176
                self.match(MemNetLayerParser.IDENT)
                self.state = 181
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while _la==10:
                    self.state = 177
                    self.match(MemNetLayerParser.SEMI)
                    self.state = 178
                    self.field()
                    self.state = 183
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)

                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DropEdgeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def MINUS(self):
            return self.getToken(MemNetLayerParser.MINUS, 0)

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_dropEdge

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDropEdge" ):
                return visitor.visitDropEdge(self)
            else:
                return visitor.visitChildren(self)




    def dropEdge(self):

        localctx = MemNetLayerParser.DropEdgeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 16, self.RULE_dropEdge)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 186
            self.match(MemNetLayerParser.MINUS)
            self.state = 187
            self.match(MemNetLayerParser.IDENT)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class EdgeWireContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return MemNetLayerParser.RULE_edgeWire

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class WireDirectedContext(EdgeWireContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.EdgeWireContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def directedEdge(self):
            return self.getTypedRuleContext(MemNetLayerParser.DirectedEdgeContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitWireDirected" ):
                return visitor.visitWireDirected(self)
            else:
                return visitor.visitChildren(self)


    class WireNonDirectedContext(EdgeWireContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.EdgeWireContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def nonDirectedEdge(self):
            return self.getTypedRuleContext(MemNetLayerParser.NonDirectedEdgeContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitWireNonDirected" ):
                return visitor.visitWireNonDirected(self)
            else:
                return visitor.visitChildren(self)


    class WireBiDirectedContext(EdgeWireContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.EdgeWireContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def biDirectedEdge(self):
            return self.getTypedRuleContext(MemNetLayerParser.BiDirectedEdgeContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitWireBiDirected" ):
                return visitor.visitWireBiDirected(self)
            else:
                return visitor.visitChildren(self)



    def edgeWire(self):

        localctx = MemNetLayerParser.EdgeWireContext(self, self._ctx, self.state)
        self.enterRule(localctx, 18, self.RULE_edgeWire)
        try:
            self.state = 192
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,13,self._ctx)
            if la_ == 1:
                localctx = MemNetLayerParser.WireDirectedContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 189
                self.directedEdge()
                pass

            elif la_ == 2:
                localctx = MemNetLayerParser.WireNonDirectedContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 190
                self.nonDirectedEdge()
                pass

            elif la_ == 3:
                localctx = MemNetLayerParser.WireBiDirectedContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 191
                self.biDirectedEdge()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class DirectedEdgeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ARROW_DASH(self):
            return self.getToken(MemNetLayerParser.ARROW_DASH, 0)

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def ARROW_R_DIR(self):
            return self.getToken(MemNetLayerParser.ARROW_R_DIR, 0)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_directedEdge

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitDirectedEdge" ):
                return visitor.visitDirectedEdge(self)
            else:
                return visitor.visitChildren(self)




    def directedEdge(self):

        localctx = MemNetLayerParser.DirectedEdgeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 20, self.RULE_directedEdge)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 194
            self.match(MemNetLayerParser.ARROW_DASH)
            self.state = 195
            self.match(MemNetLayerParser.IDENT)
            self.state = 196
            self.match(MemNetLayerParser.ARROW_R_DIR)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NonDirectedEdgeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ARROW_DASH(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.ARROW_DASH)
            else:
                return self.getToken(MemNetLayerParser.ARROW_DASH, i)

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_nonDirectedEdge

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNonDirectedEdge" ):
                return visitor.visitNonDirectedEdge(self)
            else:
                return visitor.visitChildren(self)




    def nonDirectedEdge(self):

        localctx = MemNetLayerParser.NonDirectedEdgeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 22, self.RULE_nonDirectedEdge)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 198
            self.match(MemNetLayerParser.ARROW_DASH)
            self.state = 199
            self.match(MemNetLayerParser.IDENT)
            self.state = 200
            self.match(MemNetLayerParser.ARROW_DASH)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class BiDirectedEdgeContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def ARROW_BI_L(self):
            return self.getToken(MemNetLayerParser.ARROW_BI_L, 0)

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def ARROW_R_DIR(self):
            return self.getToken(MemNetLayerParser.ARROW_R_DIR, 0)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_biDirectedEdge

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitBiDirectedEdge" ):
                return visitor.visitBiDirectedEdge(self)
            else:
                return visitor.visitChildren(self)




    def biDirectedEdge(self):

        localctx = MemNetLayerParser.BiDirectedEdgeContext(self, self._ctx, self.state)
        self.enterRule(localctx, 24, self.RULE_biDirectedEdge)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 202
            self.match(MemNetLayerParser.ARROW_BI_L)
            self.state = 203
            self.match(MemNetLayerParser.IDENT)
            self.state = 204
            self.match(MemNetLayerParser.ARROW_R_DIR)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class EndpointContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LBRACK(self):
            return self.getToken(MemNetLayerParser.LBRACK, 0)

        def endpointAtom(self):
            return self.getTypedRuleContext(MemNetLayerParser.EndpointAtomContext,0)


        def RBRACK(self):
            return self.getToken(MemNetLayerParser.RBRACK, 0)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_endpoint

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitEndpoint" ):
                return visitor.visitEndpoint(self)
            else:
                return visitor.visitChildren(self)




    def endpoint(self):

        localctx = MemNetLayerParser.EndpointContext(self, self._ctx, self.state)
        self.enterRule(localctx, 26, self.RULE_endpoint)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 206
            self.match(MemNetLayerParser.LBRACK)
            self.state = 207
            self.endpointAtom()
            self.state = 208
            self.match(MemNetLayerParser.RBRACK)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class EndpointAtomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def KW_NEW(self):
            return self.getToken(MemNetLayerParser.KW_NEW, 0)

        def IDENT(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.IDENT)
            else:
                return self.getToken(MemNetLayerParser.IDENT, i)

        def DOT(self):
            return self.getToken(MemNetLayerParser.DOT, 0)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_endpointAtom

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitEndpointAtom" ):
                return visitor.visitEndpointAtom(self)
            else:
                return visitor.visitChildren(self)




    def endpointAtom(self):

        localctx = MemNetLayerParser.EndpointAtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 28, self.RULE_endpointAtom)
        try:
            self.state = 215
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,14,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 210
                self.match(MemNetLayerParser.KW_NEW)
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 211
                self.match(MemNetLayerParser.IDENT)
                self.state = 212
                self.match(MemNetLayerParser.DOT)
                self.state = 213
                self.match(MemNetLayerParser.IDENT)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 214
                self.match(MemNetLayerParser.IDENT)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class IdAtomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def KW_NEW(self):
            return self.getToken(MemNetLayerParser.KW_NEW, 0)

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_idAtom

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitIdAtom" ):
                return visitor.visitIdAtom(self)
            else:
                return visitor.visitChildren(self)




    def idAtom(self):

        localctx = MemNetLayerParser.IdAtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 30, self.RULE_idAtom)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 217
            _la = self._input.LA(1)
            if not(_la==18 or _la==23):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class EdgeIdAtomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def KW_NEW(self):
            return self.getToken(MemNetLayerParser.KW_NEW, 0)

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_edgeIdAtom

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitEdgeIdAtom" ):
                return visitor.visitEdgeIdAtom(self)
            else:
                return visitor.visitChildren(self)




    def edgeIdAtom(self):

        localctx = MemNetLayerParser.EdgeIdAtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 32, self.RULE_edgeIdAtom)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 219
            _la = self._input.LA(1)
            if not(_la==18 or _la==23):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FieldContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def ASSIGN(self):
            return self.getToken(MemNetLayerParser.ASSIGN, 0)

        def fieldValue(self):
            return self.getTypedRuleContext(MemNetLayerParser.FieldValueContext,0)


        def PLUS_EQ(self):
            return self.getToken(MemNetLayerParser.PLUS_EQ, 0)

        def NUMBER(self):
            return self.getToken(MemNetLayerParser.NUMBER, 0)

        def MINUS_EQ(self):
            return self.getToken(MemNetLayerParser.MINUS_EQ, 0)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_field

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitField" ):
                return visitor.visitField(self)
            else:
                return visitor.visitChildren(self)




    def field(self):

        localctx = MemNetLayerParser.FieldContext(self, self._ctx, self.state)
        self.enterRule(localctx, 34, self.RULE_field)
        try:
            self.state = 230
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,15,self._ctx)
            if la_ == 1:
                self.enterOuterAlt(localctx, 1)
                self.state = 221
                self.match(MemNetLayerParser.IDENT)
                self.state = 222
                self.match(MemNetLayerParser.ASSIGN)
                self.state = 223
                self.fieldValue()
                pass

            elif la_ == 2:
                self.enterOuterAlt(localctx, 2)
                self.state = 224
                self.match(MemNetLayerParser.IDENT)
                self.state = 225
                self.match(MemNetLayerParser.PLUS_EQ)
                self.state = 226
                self.match(MemNetLayerParser.NUMBER)
                pass

            elif la_ == 3:
                self.enterOuterAlt(localctx, 3)
                self.state = 227
                self.match(MemNetLayerParser.IDENT)
                self.state = 228
                self.match(MemNetLayerParser.MINUS_EQ)
                self.state = 229
                self.match(MemNetLayerParser.NUMBER)
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FieldValueContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return MemNetLayerParser.RULE_fieldValue

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)



    class ValueLawListContext(FieldValueContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.FieldValueContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def lawList(self):
            return self.getTypedRuleContext(MemNetLayerParser.LawListContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitValueLawList" ):
                return visitor.visitValueLawList(self)
            else:
                return visitor.visitChildren(self)


    class ValuePortListContext(FieldValueContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.FieldValueContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def portList(self):
            return self.getTypedRuleContext(MemNetLayerParser.PortListContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitValuePortList" ):
                return visitor.visitValuePortList(self)
            else:
                return visitor.visitChildren(self)


    class ValueRecordContext(FieldValueContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.FieldValueContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def recordBag(self):
            return self.getTypedRuleContext(MemNetLayerParser.RecordBagContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitValueRecord" ):
                return visitor.visitValueRecord(self)
            else:
                return visitor.visitChildren(self)


    class ValueAtomContext(FieldValueContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.FieldValueContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def atom(self):
            return self.getTypedRuleContext(MemNetLayerParser.AtomContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitValueAtom" ):
                return visitor.visitValueAtom(self)
            else:
                return visitor.visitChildren(self)


    class ValueStringContext(FieldValueContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.FieldValueContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def STRING(self):
            return self.getToken(MemNetLayerParser.STRING, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitValueString" ):
                return visitor.visitValueString(self)
            else:
                return visitor.visitChildren(self)


    class ValueAtomListContext(FieldValueContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a MemNetLayerParser.FieldValueContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def atom(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(MemNetLayerParser.AtomContext)
            else:
                return self.getTypedRuleContext(MemNetLayerParser.AtomContext,i)

        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.COMMA)
            else:
                return self.getToken(MemNetLayerParser.COMMA, i)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitValueAtomList" ):
                return visitor.visitValueAtomList(self)
            else:
                return visitor.visitChildren(self)



    def fieldValue(self):

        localctx = MemNetLayerParser.FieldValueContext(self, self._ctx, self.state)
        self.enterRule(localctx, 36, self.RULE_fieldValue)
        self._la = 0 # Token type
        try:
            self.state = 244
            self._errHandler.sync(self)
            la_ = self._interp.adaptivePredict(self._input,17,self._ctx)
            if la_ == 1:
                localctx = MemNetLayerParser.ValueStringContext(self, localctx)
                self.enterOuterAlt(localctx, 1)
                self.state = 232
                self.match(MemNetLayerParser.STRING)
                pass

            elif la_ == 2:
                localctx = MemNetLayerParser.ValueLawListContext(self, localctx)
                self.enterOuterAlt(localctx, 2)
                self.state = 233
                self.lawList()
                pass

            elif la_ == 3:
                localctx = MemNetLayerParser.ValuePortListContext(self, localctx)
                self.enterOuterAlt(localctx, 3)
                self.state = 234
                self.portList()
                pass

            elif la_ == 4:
                localctx = MemNetLayerParser.ValueRecordContext(self, localctx)
                self.enterOuterAlt(localctx, 4)
                self.state = 235
                self.recordBag()
                pass

            elif la_ == 5:
                localctx = MemNetLayerParser.ValueAtomListContext(self, localctx)
                self.enterOuterAlt(localctx, 5)
                self.state = 236
                self.atom()
                self.state = 239 
                self._errHandler.sync(self)
                _la = self._input.LA(1)
                while True:
                    self.state = 237
                    self.match(MemNetLayerParser.COMMA)
                    self.state = 238
                    self.atom()
                    self.state = 241 
                    self._errHandler.sync(self)
                    _la = self._input.LA(1)
                    if not (_la==14):
                        break

                pass

            elif la_ == 6:
                localctx = MemNetLayerParser.ValueAtomContext(self, localctx)
                self.enterOuterAlt(localctx, 6)
                self.state = 243
                self.atom()
                pass


        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class LawListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LAW_SEG(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.LAW_SEG)
            else:
                return self.getToken(MemNetLayerParser.LAW_SEG, i)

        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.COMMA)
            else:
                return self.getToken(MemNetLayerParser.COMMA, i)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_lawList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitLawList" ):
                return visitor.visitLawList(self)
            else:
                return visitor.visitChildren(self)




    def lawList(self):

        localctx = MemNetLayerParser.LawListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 38, self.RULE_lawList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 246
            self.match(MemNetLayerParser.LAW_SEG)
            self.state = 251
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==14:
                self.state = 247
                self.match(MemNetLayerParser.COMMA)
                self.state = 248
                self.match(MemNetLayerParser.LAW_SEG)
                self.state = 253
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PortListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def portToken(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(MemNetLayerParser.PortTokenContext)
            else:
                return self.getTypedRuleContext(MemNetLayerParser.PortTokenContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.COMMA)
            else:
                return self.getToken(MemNetLayerParser.COMMA, i)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_portList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPortList" ):
                return visitor.visitPortList(self)
            else:
                return visitor.visitChildren(self)




    def portList(self):

        localctx = MemNetLayerParser.PortListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 40, self.RULE_portList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 254
            self.portToken()
            self.state = 259
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==14:
                self.state = 255
                self.match(MemNetLayerParser.COMMA)
                self.state = 256
                self.portToken()
                self.state = 261
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PortTokenContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def COLON(self):
            return self.getToken(MemNetLayerParser.COLON, 0)

        def LBRACE(self):
            return self.getToken(MemNetLayerParser.LBRACE, 0)

        def RBRACE(self):
            return self.getToken(MemNetLayerParser.RBRACE, 0)

        def attrList(self):
            return self.getTypedRuleContext(MemNetLayerParser.AttrListContext,0)


        def getRuleIndex(self):
            return MemNetLayerParser.RULE_portToken

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPortToken" ):
                return visitor.visitPortToken(self)
            else:
                return visitor.visitChildren(self)




    def portToken(self):

        localctx = MemNetLayerParser.PortTokenContext(self, self._ctx, self.state)
        self.enterRule(localctx, 42, self.RULE_portToken)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 262
            self.match(MemNetLayerParser.IDENT)
            self.state = 263
            self.match(MemNetLayerParser.COLON)
            self.state = 264
            self.match(MemNetLayerParser.LBRACE)
            self.state = 266
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==23:
                self.state = 265
                self.attrList()


            self.state = 268
            self.match(MemNetLayerParser.RBRACE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class RecordBagContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LBRACE(self):
            return self.getToken(MemNetLayerParser.LBRACE, 0)

        def RBRACE(self):
            return self.getToken(MemNetLayerParser.RBRACE, 0)

        def attrList(self):
            return self.getTypedRuleContext(MemNetLayerParser.AttrListContext,0)


        def getRuleIndex(self):
            return MemNetLayerParser.RULE_recordBag

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitRecordBag" ):
                return visitor.visitRecordBag(self)
            else:
                return visitor.visitChildren(self)




    def recordBag(self):

        localctx = MemNetLayerParser.RecordBagContext(self, self._ctx, self.state)
        self.enterRule(localctx, 44, self.RULE_recordBag)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 270
            self.match(MemNetLayerParser.LBRACE)
            self.state = 272
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==23:
                self.state = 271
                self.attrList()


            self.state = 274
            self.match(MemNetLayerParser.RBRACE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AttrListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def attr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(MemNetLayerParser.AttrContext)
            else:
                return self.getTypedRuleContext(MemNetLayerParser.AttrContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.COMMA)
            else:
                return self.getToken(MemNetLayerParser.COMMA, i)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_attrList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAttrList" ):
                return visitor.visitAttrList(self)
            else:
                return visitor.visitChildren(self)




    def attrList(self):

        localctx = MemNetLayerParser.AttrListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 46, self.RULE_attrList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 276
            self.attr()
            self.state = 281
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==14:
                self.state = 277
                self.match(MemNetLayerParser.COMMA)
                self.state = 278
                self.attr()
                self.state = 283
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AttrContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def ASSIGN(self):
            return self.getToken(MemNetLayerParser.ASSIGN, 0)

        def attrValue(self):
            return self.getTypedRuleContext(MemNetLayerParser.AttrValueContext,0)


        def getRuleIndex(self):
            return MemNetLayerParser.RULE_attr

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAttr" ):
                return visitor.visitAttr(self)
            else:
                return visitor.visitChildren(self)




    def attr(self):

        localctx = MemNetLayerParser.AttrContext(self, self._ctx, self.state)
        self.enterRule(localctx, 48, self.RULE_attr)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 284
            self.match(MemNetLayerParser.IDENT)
            self.state = 285
            self.match(MemNetLayerParser.ASSIGN)
            self.state = 286
            self.attrValue()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AttrValueContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self):
            return self.getToken(MemNetLayerParser.NUMBER, 0)

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def ALIAS_REF(self):
            return self.getToken(MemNetLayerParser.ALIAS_REF, 0)

        def LAW_SEG(self):
            return self.getToken(MemNetLayerParser.LAW_SEG, 0)

        def STRING(self):
            return self.getToken(MemNetLayerParser.STRING, 0)

        def BARE_ATOM(self):
            return self.getToken(MemNetLayerParser.BARE_ATOM, 0)

        def nestedRecord(self):
            return self.getTypedRuleContext(MemNetLayerParser.NestedRecordContext,0)


        def getRuleIndex(self):
            return MemNetLayerParser.RULE_attrValue

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAttrValue" ):
                return visitor.visitAttrValue(self)
            else:
                return visitor.visitChildren(self)




    def attrValue(self):

        localctx = MemNetLayerParser.AttrValueContext(self, self._ctx, self.state)
        self.enterRule(localctx, 50, self.RULE_attrValue)
        try:
            self.state = 295
            self._errHandler.sync(self)
            token = self._input.LA(1)
            if token in [22]:
                self.enterOuterAlt(localctx, 1)
                self.state = 288
                self.match(MemNetLayerParser.NUMBER)
                pass
            elif token in [23]:
                self.enterOuterAlt(localctx, 2)
                self.state = 289
                self.match(MemNetLayerParser.IDENT)
                pass
            elif token in [19]:
                self.enterOuterAlt(localctx, 3)
                self.state = 290
                self.match(MemNetLayerParser.ALIAS_REF)
                pass
            elif token in [20]:
                self.enterOuterAlt(localctx, 4)
                self.state = 291
                self.match(MemNetLayerParser.LAW_SEG)
                pass
            elif token in [21]:
                self.enterOuterAlt(localctx, 5)
                self.state = 292
                self.match(MemNetLayerParser.STRING)
                pass
            elif token in [24]:
                self.enterOuterAlt(localctx, 6)
                self.state = 293
                self.match(MemNetLayerParser.BARE_ATOM)
                pass
            elif token in [8]:
                self.enterOuterAlt(localctx, 7)
                self.state = 294
                self.nestedRecord()
                pass
            else:
                raise NoViableAltException(self)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class NestedRecordContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def LBRACE(self):
            return self.getToken(MemNetLayerParser.LBRACE, 0)

        def RBRACE(self):
            return self.getToken(MemNetLayerParser.RBRACE, 0)

        def flatAttrList(self):
            return self.getTypedRuleContext(MemNetLayerParser.FlatAttrListContext,0)


        def getRuleIndex(self):
            return MemNetLayerParser.RULE_nestedRecord

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitNestedRecord" ):
                return visitor.visitNestedRecord(self)
            else:
                return visitor.visitChildren(self)




    def nestedRecord(self):

        localctx = MemNetLayerParser.NestedRecordContext(self, self._ctx, self.state)
        self.enterRule(localctx, 52, self.RULE_nestedRecord)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 297
            self.match(MemNetLayerParser.LBRACE)
            self.state = 299
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            if _la==23:
                self.state = 298
                self.flatAttrList()


            self.state = 301
            self.match(MemNetLayerParser.RBRACE)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FlatAttrListContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def flatAttr(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(MemNetLayerParser.FlatAttrContext)
            else:
                return self.getTypedRuleContext(MemNetLayerParser.FlatAttrContext,i)


        def COMMA(self, i:int=None):
            if i is None:
                return self.getTokens(MemNetLayerParser.COMMA)
            else:
                return self.getToken(MemNetLayerParser.COMMA, i)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_flatAttrList

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFlatAttrList" ):
                return visitor.visitFlatAttrList(self)
            else:
                return visitor.visitChildren(self)




    def flatAttrList(self):

        localctx = MemNetLayerParser.FlatAttrListContext(self, self._ctx, self.state)
        self.enterRule(localctx, 54, self.RULE_flatAttrList)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 303
            self.flatAttr()
            self.state = 308
            self._errHandler.sync(self)
            _la = self._input.LA(1)
            while _la==14:
                self.state = 304
                self.match(MemNetLayerParser.COMMA)
                self.state = 305
                self.flatAttr()
                self.state = 310
                self._errHandler.sync(self)
                _la = self._input.LA(1)

        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FlatAttrContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def ASSIGN(self):
            return self.getToken(MemNetLayerParser.ASSIGN, 0)

        def flatAttrValue(self):
            return self.getTypedRuleContext(MemNetLayerParser.FlatAttrValueContext,0)


        def getRuleIndex(self):
            return MemNetLayerParser.RULE_flatAttr

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFlatAttr" ):
                return visitor.visitFlatAttr(self)
            else:
                return visitor.visitChildren(self)




    def flatAttr(self):

        localctx = MemNetLayerParser.FlatAttrContext(self, self._ctx, self.state)
        self.enterRule(localctx, 56, self.RULE_flatAttr)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 311
            self.match(MemNetLayerParser.IDENT)
            self.state = 312
            self.match(MemNetLayerParser.ASSIGN)
            self.state = 313
            self.flatAttrValue()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class FlatAttrValueContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def NUMBER(self):
            return self.getToken(MemNetLayerParser.NUMBER, 0)

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def ALIAS_REF(self):
            return self.getToken(MemNetLayerParser.ALIAS_REF, 0)

        def LAW_SEG(self):
            return self.getToken(MemNetLayerParser.LAW_SEG, 0)

        def STRING(self):
            return self.getToken(MemNetLayerParser.STRING, 0)

        def BARE_ATOM(self):
            return self.getToken(MemNetLayerParser.BARE_ATOM, 0)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_flatAttrValue

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitFlatAttrValue" ):
                return visitor.visitFlatAttrValue(self)
            else:
                return visitor.visitChildren(self)




    def flatAttrValue(self):

        localctx = MemNetLayerParser.FlatAttrValueContext(self, self._ctx, self.state)
        self.enterRule(localctx, 58, self.RULE_flatAttrValue)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 315
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 33030144) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class AtomContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def STRING(self):
            return self.getToken(MemNetLayerParser.STRING, 0)

        def NUMBER(self):
            return self.getToken(MemNetLayerParser.NUMBER, 0)

        def KW_NEW(self):
            return self.getToken(MemNetLayerParser.KW_NEW, 0)

        def IDENT(self):
            return self.getToken(MemNetLayerParser.IDENT, 0)

        def BARE_ATOM(self):
            return self.getToken(MemNetLayerParser.BARE_ATOM, 0)

        def getRuleIndex(self):
            return MemNetLayerParser.RULE_atom

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitAtom" ):
                return visitor.visitAtom(self)
            else:
                return visitor.visitChildren(self)




    def atom(self):

        localctx = MemNetLayerParser.AtomContext(self, self._ctx, self.state)
        self.enterRule(localctx, 60, self.RULE_atom)
        self._la = 0 # Token type
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 317
            _la = self._input.LA(1)
            if not((((_la) & ~0x3f) == 0 and ((1 << _la) & 31719424) != 0)):
                self._errHandler.recoverInline(self)
            else:
                self._errHandler.reportMatch(self)
                self.consume()
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx





