package com.rulix.plugin.highlighting

import com.intellij.openapi.editor.colors.TextAttributesKey
import com.intellij.openapi.fileTypes.SyntaxHighlighter
import com.intellij.openapi.options.colors.AttributesDescriptor
import com.intellij.openapi.options.colors.ColorDescriptor
import com.intellij.openapi.options.colors.ColorSettingsPage
import com.rulix.plugin.RulixIcons
import javax.swing.Icon

class RulixColorSettingsPage : ColorSettingsPage {

    private val ATTRIBUTES = arrayOf(
        AttributesDescriptor("Keyword",          RulixHighlighterColors.KEYWORD),
        AttributesDescriptor("Built-in function",RulixHighlighterColors.BUILTIN_FUNCTION),
        AttributesDescriptor("Identifier",       RulixHighlighterColors.IDENTIFIER),
        AttributesDescriptor("Comment",          RulixHighlighterColors.LINE_COMMENT),
        AttributesDescriptor("String",           RulixHighlighterColors.STRING),
        AttributesDescriptor("Number",           RulixHighlighterColors.NUMBER),
        AttributesDescriptor("Operator",         RulixHighlighterColors.OPERATOR),
        AttributesDescriptor("Arrow (=>)",       RulixHighlighterColors.ARROW),
        AttributesDescriptor("Braces {}",        RulixHighlighterColors.BRACES),
        AttributesDescriptor("Parentheses ()",   RulixHighlighterColors.PARENTHESES),
        AttributesDescriptor("Comma",            RulixHighlighterColors.COMMA),
        AttributesDescriptor("Dot",              RulixHighlighterColors.DOT),
    )

    override fun getIcon(): Icon = RulixIcons.FILE
    override fun getHighlighter(): SyntaxHighlighter = RulixSyntaxHighlighter()
    override fun getAttributeDescriptors(): Array<AttributesDescriptor> = ATTRIBUTES
    override fun getColorDescriptors(): Array<ColorDescriptor> = ColorDescriptor.EMPTY_ARRAY
    override fun getDisplayName(): String = "Rulix"
    override fun getAdditionalHighlightingTagToDescriptorMap(): Map<String, TextAttributesKey>? = null

    override fun getDemoText(): String = """
        # Rulix example — run counter with threshold alert
        is_null(runs) => runs = 0
        is_null(ready) => ready = false

        => {
            runs = runs + 1
            ready = true
        }

        rule too_hot: temperature > 80, ready == true => {
            print("WARNING: temp is " + str(temperature))
            log("warn", "threshold exceeded")
            disable
        }

        rule once_and_stop: is_null(initialized) => {
            initialized = true
            stop
        }
    """.trimIndent()
}
