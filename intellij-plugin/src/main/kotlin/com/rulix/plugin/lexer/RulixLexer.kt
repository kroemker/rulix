package com.rulix.plugin.lexer

import com.intellij.lexer.LexerBase
import com.intellij.psi.tree.IElementType
import com.rulix.plugin.RulixTokenTypes

/**
 * Hand-written lexer for Rulix (.rlx) source files.
 *
 * Token classification follows the language spec (SPEC.md):
 *   - Keywords:  rule true false null and or not disable stop
 *   - Builtins:  print, input, log, str, int, float, bool, type, is_null, …
 *   - Strings:   double-quoted, with \-escapes and {expr} interpolation holes
 *   - Numbers:   integer and float literals
 *   - Comments:  # … to end of line
 */
class RulixLexer : LexerBase() {

    private var buffer: CharSequence = ""
    private var bufferEnd: Int = 0
    private var position: Int = 0
    private var tokenStart: Int = 0
    private var tokenType: IElementType? = null

    override fun start(buffer: CharSequence, startOffset: Int, endOffset: Int, initialState: Int) {
        this.buffer    = buffer
        this.bufferEnd = endOffset
        this.position  = startOffset
        this.tokenStart = startOffset
        this.tokenType  = null
        advance()
    }

    override fun getState(): Int = 0
    override fun getTokenType(): IElementType? = tokenType
    override fun getTokenStart(): Int = tokenStart
    override fun getTokenEnd(): Int = position
    override fun getBufferSequence(): CharSequence = buffer
    override fun getBufferEnd(): Int = bufferEnd

    override fun advance() {
        tokenStart = position
        if (position >= bufferEnd) {
            tokenType = null
            return
        }
        tokenType = readToken()
    }

    private fun peek(offset: Int = 0): Char? =
        if (position + offset < bufferEnd) buffer[position + offset] else null

    private fun readToken(): IElementType {
        val ch = buffer[position]

        // ── Whitespace (non-newline) ──────────────────────────────────────
        if (ch == ' ' || ch == '\t' || ch == '\r') {
            while (position < bufferEnd &&
                (buffer[position] == ' ' || buffer[position] == '\t' || buffer[position] == '\r')
            ) position++
            return RulixTokenTypes.WHITE_SPACE
        }

        // ── Newline ───────────────────────────────────────────────────────
        if (ch == '\n') { position++; return RulixTokenTypes.NEWLINE }

        // ── Line comment: # … ─────────────────────────────────────────────
        if (ch == '#') {
            while (position < bufferEnd && buffer[position] != '\n') position++
            return RulixTokenTypes.LINE_COMMENT
        }

        // ── String literal: "…" ───────────────────────────────────────────
        if (ch == '"') {
            position++ // opening quote
            while (position < bufferEnd) {
                when (buffer[position]) {
                    '\\' -> position += 2          // skip escape sequence
                    '"'  -> { position++; break }  // closing quote
                    else -> position++
                }
            }
            return RulixTokenTypes.STRING
        }

        // ── Number literal ────────────────────────────────────────────────
        if (ch.isDigit()) {
            while (position < bufferEnd && buffer[position].isDigit()) position++
            // optional fractional part
            if (peek() == '.' && peek(1)?.isDigit() == true) {
                position++ // dot
                while (position < bufferEnd && buffer[position].isDigit()) position++
            }
            return RulixTokenTypes.NUMBER
        }

        // ── Identifier / keyword / built-in ──────────────────────────────
        if (ch.isLetter() || ch == '_') {
            while (position < bufferEnd &&
                (buffer[position].isLetterOrDigit() || buffer[position] == '_')
            ) position++
            val word = buffer.subSequence(tokenStart, position).toString()
            return when {
                word in RulixTokenTypes.KEYWORDS -> RulixTokenTypes.KEYWORD
                word in RulixTokenTypes.BUILTINS -> RulixTokenTypes.BUILTIN_FUNCTION
                else                             -> RulixTokenTypes.IDENTIFIER
            }
        }

        // ── Multi-character operators ─────────────────────────────────────
        position++
        return when (ch) {
            '=' -> when (peek()) {
                '>' -> { position++; RulixTokenTypes.ARROW  }
                '=' -> { position++; RulixTokenTypes.EQ_EQ  }
                else -> RulixTokenTypes.ASSIGN
            }
            '!' -> if (peek() == '=') { position++; RulixTokenTypes.NOT_EQ } else RulixTokenTypes.BAD_CHARACTER
            '<' -> if (peek() == '=') { position++; RulixTokenTypes.LT_EQ  } else RulixTokenTypes.LT
            '>' -> if (peek() == '=') { position++; RulixTokenTypes.GT_EQ  } else RulixTokenTypes.GT
            '+' -> RulixTokenTypes.PLUS
            '-' -> RulixTokenTypes.MINUS
            '*' -> RulixTokenTypes.STAR
            '/' -> RulixTokenTypes.SLASH
            '%' -> RulixTokenTypes.PERCENT
            ',' -> RulixTokenTypes.COMMA
            '.' -> RulixTokenTypes.DOT
            ':' -> RulixTokenTypes.COLON
            '{' -> RulixTokenTypes.LBRACE
            '}' -> RulixTokenTypes.RBRACE
            '(' -> RulixTokenTypes.LPAREN
            ')' -> RulixTokenTypes.RPAREN
            else -> RulixTokenTypes.BAD_CHARACTER
        }
    }
}
