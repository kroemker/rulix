package com.rulix.plugin.highlighting

import com.intellij.openapi.editor.DefaultLanguageHighlighterColors
import com.intellij.openapi.editor.colors.TextAttributesKey

object RulixHighlighterColors {
    val KEYWORD          = key("RULIX_KEYWORD",   DefaultLanguageHighlighterColors.KEYWORD)
    val BUILTIN_FUNCTION = key("RULIX_BUILTIN",   DefaultLanguageHighlighterColors.PREDEFINED_SYMBOL)
    val IDENTIFIER       = key("RULIX_IDENTIFIER",DefaultLanguageHighlighterColors.IDENTIFIER)
    val LINE_COMMENT     = key("RULIX_COMMENT",   DefaultLanguageHighlighterColors.LINE_COMMENT)
    val STRING           = key("RULIX_STRING",    DefaultLanguageHighlighterColors.STRING)
    val NUMBER           = key("RULIX_NUMBER",    DefaultLanguageHighlighterColors.NUMBER)
    val OPERATOR         = key("RULIX_OPERATOR",  DefaultLanguageHighlighterColors.OPERATION_SIGN)
    val ARROW            = key("RULIX_ARROW",     DefaultLanguageHighlighterColors.OPERATION_SIGN)
    val BRACES           = key("RULIX_BRACES",    DefaultLanguageHighlighterColors.BRACES)
    val PARENTHESES      = key("RULIX_PARENS",    DefaultLanguageHighlighterColors.PARENTHESES)
    val COMMA            = key("RULIX_COMMA",     DefaultLanguageHighlighterColors.COMMA)
    val DOT              = key("RULIX_DOT",       DefaultLanguageHighlighterColors.DOT)

    private fun key(name: String, fallback: TextAttributesKey) =
        TextAttributesKey.createTextAttributesKey(name, fallback)
}
