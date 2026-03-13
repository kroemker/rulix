package com.rulix.plugin

import com.intellij.lang.BracePair
import com.intellij.lang.PairedBraceMatcher
import com.intellij.psi.PsiFile
import com.intellij.psi.tree.IElementType

class RulixBraceMatcher : PairedBraceMatcher {

    private val PAIRS = arrayOf(
        BracePair(RulixTokenTypes.LBRACE, RulixTokenTypes.RBRACE, true),
        BracePair(RulixTokenTypes.LPAREN, RulixTokenTypes.RPAREN, false),
    )

    override fun getPairs(): Array<BracePair> = PAIRS
    override fun isPairedBracesAllowedBeforeType(lbraceType: IElementType, contextType: IElementType?): Boolean = true
    override fun getCodeConstructStart(file: PsiFile, openingBraceOffset: Int): Int = openingBraceOffset
}
