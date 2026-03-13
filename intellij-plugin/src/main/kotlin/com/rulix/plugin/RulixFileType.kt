package com.rulix.plugin

import com.intellij.openapi.fileTypes.LanguageFileType
import javax.swing.Icon

object RulixFileType : LanguageFileType(RulixLanguage) {
    override fun getName(): String = "Rulix"
    override fun getDescription(): String = "Rulix rule-based script"
    override fun getDefaultExtension(): String = "rlx"
    override fun getIcon(): Icon = RulixIcons.FILE
}
