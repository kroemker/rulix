package com.rulix.plugin.highlighting

import com.intellij.lexer.Lexer
import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighterBase
import com.intellij.psi.tree.IElementType
import com.rulix.plugin.RulixTokenTypes
import com.rulix.plugin.lexer.RulixLexer

class RulixSyntaxHighlighter : SyntaxHighlighterBase() {

    override fun getHighlightingLexer(): Lexer = RulixLexer()

    override fun getTokenHighlights(tokenType: IElementType): Array<TextAttributesKey> =
        when (tokenType) {
            RulixTokenTypes.KEYWORD          -> pack(RulixHighlighterColors.KEYWORD)
            RulixTokenTypes.BUILTIN_FUNCTION -> pack(RulixHighlighterColors.BUILTIN_FUNCTION)
            RulixTokenTypes.IDENTIFIER       -> pack(RulixHighlighterColors.IDENTIFIER)
            RulixTokenTypes.LINE_COMMENT     -> pack(RulixHighlighterColors.LINE_COMMENT)
            RulixTokenTypes.STRING           -> pack(RulixHighlighterColors.STRING)
            RulixTokenTypes.NUMBER           -> pack(RulixHighlighterColors.NUMBER)
            RulixTokenTypes.ARROW            -> pack(RulixHighlighterColors.ARROW)
            RulixTokenTypes.EQ_EQ,
            RulixTokenTypes.NOT_EQ,
            RulixTokenTypes.LT_EQ,
            RulixTokenTypes.GT_EQ,
            RulixTokenTypes.LT,
            RulixTokenTypes.GT,
            RulixTokenTypes.ASSIGN,
            RulixTokenTypes.PLUS,
            RulixTokenTypes.MINUS,
            RulixTokenTypes.STAR,
            RulixTokenTypes.SLASH,
            RulixTokenTypes.PERCENT          -> pack(RulixHighlighterColors.OPERATOR)
            RulixTokenTypes.LBRACE,
            RulixTokenTypes.RBRACE           -> pack(RulixHighlighterColors.BRACES)
            RulixTokenTypes.LPAREN,
            RulixTokenTypes.RPAREN           -> pack(RulixHighlighterColors.PARENTHESES)
            RulixTokenTypes.COMMA            -> pack(RulixHighlighterColors.COMMA)
            RulixTokenTypes.DOT              -> pack(RulixHighlighterColors.DOT)
            else                             -> emptyArray()
        }
}
