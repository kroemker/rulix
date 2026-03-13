package com.rulix.plugin

import com.intellij.lang.ASTNode
import com.intellij.lang.ParserDefinition
import com.intellij.lang.PsiParser
import com.intellij.lexer.Lexer
import com.intellij.openapi.project.Project
import com.intellij.psi.FileViewProvider
import com.intellij.psi.PsiElement
import com.intellij.psi.PsiFile
import com.intellij.psi.tree.IFileElementType
import com.intellij.psi.tree.TokenSet
import com.rulix.plugin.lexer.RulixLexer

class RulixParserDefinition : ParserDefinition {

    companion object {
        val FILE = IFileElementType(RulixLanguage)
    }

    override fun createLexer(project: Project): Lexer = RulixLexer()

    override fun createParser(project: Project): PsiParser = PsiParser { root, builder ->
        val marker = builder.mark()
        while (!builder.eof()) builder.advanceLexer()
        marker.done(root)
        builder.treeBuilt
    }

    override fun getFileNodeType(): IFileElementType = FILE

    override fun getCommentTokens(): TokenSet = RulixTokenTypes.COMMENTS_TOKEN_SET

    override fun getStringLiteralElements(): TokenSet = RulixTokenTypes.STRING_TOKEN_SET

    override fun createElement(node: ASTNode): PsiElement =
        throw UnsupportedOperationException("No PSI elements beyond file level")

    override fun createFile(viewProvider: FileViewProvider): PsiFile = RulixFile(viewProvider)
}
