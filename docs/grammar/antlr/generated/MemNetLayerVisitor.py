# Generated from MemNetLayer.g4 by ANTLR 4.13.2
from antlr4 import *
if "." in __name__:
    from .MemNetLayerParser import MemNetLayerParser
else:
    from MemNetLayerParser import MemNetLayerParser

# This class defines a complete generic visitor for a parse tree produced by MemNetLayerParser.

class MemNetLayerVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by MemNetLayerParser#document.
    def visitDocument(self, ctx:MemNetLayerParser.DocumentContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#CreateNodeLine.
    def visitCreateNodeLine(self, ctx:MemNetLayerParser.CreateNodeLineContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#PatchNodeLine.
    def visitPatchNodeLine(self, ctx:MemNetLayerParser.PatchNodeLineContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#CreateEdgeLine.
    def visitCreateEdgeLine(self, ctx:MemNetLayerParser.CreateEdgeLineContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#PatchEdgeLine.
    def visitPatchEdgeLine(self, ctx:MemNetLayerParser.PatchEdgeLineContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#DropEdgeLine.
    def visitDropEdgeLine(self, ctx:MemNetLayerParser.DropEdgeLineContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#PresentNodeLine.
    def visitPresentNodeLine(self, ctx:MemNetLayerParser.PresentNodeLineContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#PresentEdgeLine.
    def visitPresentEdgeLine(self, ctx:MemNetLayerParser.PresentEdgeLineContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#presentNode.
    def visitPresentNode(self, ctx:MemNetLayerParser.PresentNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#createNode.
    def visitCreateNode(self, ctx:MemNetLayerParser.CreateNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#patchNode.
    def visitPatchNode(self, ctx:MemNetLayerParser.PatchNodeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#presentEdge.
    def visitPresentEdge(self, ctx:MemNetLayerParser.PresentEdgeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#createEdge.
    def visitCreateEdge(self, ctx:MemNetLayerParser.CreateEdgeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#patchEdge.
    def visitPatchEdge(self, ctx:MemNetLayerParser.PatchEdgeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#dropEdge.
    def visitDropEdge(self, ctx:MemNetLayerParser.DropEdgeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#WireDirected.
    def visitWireDirected(self, ctx:MemNetLayerParser.WireDirectedContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#WireNonDirected.
    def visitWireNonDirected(self, ctx:MemNetLayerParser.WireNonDirectedContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#WireBiDirected.
    def visitWireBiDirected(self, ctx:MemNetLayerParser.WireBiDirectedContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#directedEdge.
    def visitDirectedEdge(self, ctx:MemNetLayerParser.DirectedEdgeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#nonDirectedEdge.
    def visitNonDirectedEdge(self, ctx:MemNetLayerParser.NonDirectedEdgeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#biDirectedEdge.
    def visitBiDirectedEdge(self, ctx:MemNetLayerParser.BiDirectedEdgeContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#endpoint.
    def visitEndpoint(self, ctx:MemNetLayerParser.EndpointContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#endpointAtom.
    def visitEndpointAtom(self, ctx:MemNetLayerParser.EndpointAtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#idAtom.
    def visitIdAtom(self, ctx:MemNetLayerParser.IdAtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#edgeIdAtom.
    def visitEdgeIdAtom(self, ctx:MemNetLayerParser.EdgeIdAtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#field.
    def visitField(self, ctx:MemNetLayerParser.FieldContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#ValueString.
    def visitValueString(self, ctx:MemNetLayerParser.ValueStringContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#ValueLawList.
    def visitValueLawList(self, ctx:MemNetLayerParser.ValueLawListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#ValuePortList.
    def visitValuePortList(self, ctx:MemNetLayerParser.ValuePortListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#ValueRecord.
    def visitValueRecord(self, ctx:MemNetLayerParser.ValueRecordContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#ValueAtomList.
    def visitValueAtomList(self, ctx:MemNetLayerParser.ValueAtomListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#ValueAtom.
    def visitValueAtom(self, ctx:MemNetLayerParser.ValueAtomContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#lawList.
    def visitLawList(self, ctx:MemNetLayerParser.LawListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#portList.
    def visitPortList(self, ctx:MemNetLayerParser.PortListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#portToken.
    def visitPortToken(self, ctx:MemNetLayerParser.PortTokenContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#recordBag.
    def visitRecordBag(self, ctx:MemNetLayerParser.RecordBagContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#attrList.
    def visitAttrList(self, ctx:MemNetLayerParser.AttrListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#attr.
    def visitAttr(self, ctx:MemNetLayerParser.AttrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#attrValue.
    def visitAttrValue(self, ctx:MemNetLayerParser.AttrValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#nestedRecord.
    def visitNestedRecord(self, ctx:MemNetLayerParser.NestedRecordContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#flatAttrList.
    def visitFlatAttrList(self, ctx:MemNetLayerParser.FlatAttrListContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#flatAttr.
    def visitFlatAttr(self, ctx:MemNetLayerParser.FlatAttrContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#flatAttrValue.
    def visitFlatAttrValue(self, ctx:MemNetLayerParser.FlatAttrValueContext):
        return self.visitChildren(ctx)


    # Visit a parse tree produced by MemNetLayerParser#atom.
    def visitAtom(self, ctx:MemNetLayerParser.AtomContext):
        return self.visitChildren(ctx)



del MemNetLayerParser