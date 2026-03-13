package com.rulix.plugin

import com.intellij.extapi.psi.PsiFileBase
import com.intellij.psi.FileViewProvider

class RulixFile(viewProvider: FileViewProvider) : PsiFileBase(viewProvider, RulixLanguage) {
    override fun getFileType() = RulixFileType
    override fun toString() = "Rulix File"
}
