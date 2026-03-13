package com.rulix.plugin

import com.intellij.psi.tree.IElementType
import com.intellij.psi.tree.TokenSet

class RulixTokenType(debugName: String) : IElementType(debugName, RulixLanguage)

object RulixTokenTypes {
    // Identifiers and literals
    val KEYWORD           = RulixTokenType("KEYWORD")
    val BUILTIN_FUNCTION  = RulixTokenType("BUILTIN_FUNCTION")
    val IDENTIFIER        = RulixTokenType("IDENTIFIER")
    val STRING            = RulixTokenType("STRING")
    val NUMBER            = RulixTokenType("NUMBER")

    // Comments
    val LINE_COMMENT      = RulixTokenType("LINE_COMMENT")

    // Operators
    val ARROW             = RulixTokenType("ARROW")    // =>
    val EQ_EQ             = RulixTokenType("EQ_EQ")    // ==
    val NOT_EQ            = RulixTokenType("NOT_EQ")   // !=
    val LT_EQ             = RulixTokenType("LT_EQ")    // <=
    val GT_EQ             = RulixTokenType("GT_EQ")    // >=
    val LT                = RulixTokenType("LT")       // <
    val GT                = RulixTokenType("GT")       // >
    val ASSIGN            = RulixTokenType("ASSIGN")   // =
    val PLUS              = RulixTokenType("PLUS")     // +
    val MINUS             = RulixTokenType("MINUS")    // -
    val STAR              = RulixTokenType("STAR")     // *
    val SLASH             = RulixTokenType("SLASH")    // /
    val PERCENT           = RulixTokenType("PERCENT")  // %

    // Punctuation
    val COMMA             = RulixTokenType("COMMA")    // ,
    val DOT               = RulixTokenType("DOT")      // .
    val COLON             = RulixTokenType("COLON")    // :
    val LBRACE            = RulixTokenType("LBRACE")   // {
    val RBRACE            = RulixTokenType("RBRACE")   // }
    val LPAREN            = RulixTokenType("LPAREN")   // (
    val RPAREN            = RulixTokenType("RPAREN")   // )

    // Whitespace
    val WHITE_SPACE       = RulixTokenType("WHITE_SPACE")
    val NEWLINE           = RulixTokenType("NEWLINE")

    val BAD_CHARACTER     = RulixTokenType("BAD_CHARACTER")

    // Sets for ParserDefinition
    val COMMENTS_TOKEN_SET = TokenSet.create(LINE_COMMENT)
    val STRING_TOKEN_SET   = TokenSet.create(STRING)

    // Keyword and built-in function name sets (used by the lexer)
    val KEYWORDS = setOf(
        "rule", "true", "false", "null",
        "and", "or", "not",
        "disable", "stop"
    )

    val BUILTINS = setOf(
        // io
        "print", "input", "log",
        // type
        "str", "int", "float", "bool", "type",
        "is_null", "is_int", "is_float", "is_string", "is_bool",
        // math
        "abs", "min", "max", "floor", "ceil", "round", "pow", "sqrt",
        // string
        "len", "upper", "lower", "trim", "contains",
        "starts_with", "ends_with", "replace", "split",
        // state
        "delete", "exists"
    )
}
