package com.rulix.plugin

import com.intellij.lang.Language

object RulixLanguage : Language("Rulix") {
    private fun readResolve(): Any = RulixLanguage
}
