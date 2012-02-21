# Copyright (c) 2007, 2012 Jakub Wilk <jwilk@jwilk.net>

'''Javalette tokenizer.'''

import ply.lex as lex
import re

__all__ = ['Tokenizer']

_STRING_re = re.compile(r'(?sx) \A" | "\Z | \\.')

class Tokenizer(object):

	tokens = \
	(
		'LPAREN', 'RPAREN',
		'COMMA',
		'LBRACE', 'RBRACE',
		'SEMICOLON',
		'ASSIGN',
		'INC', 'DEC',
		'LOR', 'LAND', 'EQUAL', 'NOTEQ',
		'LT', 'GT', 'LE', 'GE',
		'PLUS', 'MINUS',
		'TIMES', 'DIV', 'MOD',
		'NOT',
		'TYPE',
		'IF', 'ELSE', 'WHILE', 'FOR', 'RETURN',
		'INT', 'DOUBLE', 'BOOLEAN', 'STRING',
		'IDENT'
	)

	keywords = \
	{
		'if':     'IF',
		'else':   'ELSE',
		'while':  'WHILE',
		'for':    'FOR',
		'return': 'RETURN'
	}

	types = ('int', 'double', 'boolean', 'void')

	t_LPAREN    = '[(]'
	t_RPAREN    = '[)]'
	t_COMMA     = ','
	t_LBRACE    = '[{]'
	t_RBRACE    = '[}]'
	t_SEMICOLON = ';'
	t_ASSIGN    = '='
	t_INC       = '[+][+]'
	t_DEC       = '--'
	t_LOR       = '[|][|]'
	t_LAND      = '&&'
	t_EQUAL     = '=='
	t_NOTEQ     = '!='
	t_LT        = '<'
	t_GT        = '>'
	t_LE        = '<='
	t_GE        = '>='
	t_PLUS      = '[+]'
	t_MINUS     = '-'
	t_TIMES     = '[*]'
	t_DIV       = '/'
	t_MOD       = '%'
	t_NOT       = '!'

	def t_COMMENT(self, t):
		r'/[*].*?[*]/ | //.*?$ | \#.*?$'
		t.lexer.lineno += t.value.count('\n')
		t.lexer.x = len(t.value) - t.value.rfind('\n')
		pass

	def t_COMMENT_error(self, t):
		r'/[*]'
		self._error('Error: Unterminated /* ... */ comment')

	def t_DOUBLE(self, t):
		'''
			( \d+[.]\d* | \d*[.]\d+ ) ( [eE] [+-]?\d+ )? |
			\d+ [eE] [+-]?\d+
		'''
		try:
			t.value = float(t.value)
		except ValueError:
			self._error('Invalid literal for double type: ' + t.value)
			t.value = 0
		return t

	def t_INT(self, t):
		r'[0-9]+'
		try:
			t.value = int(t.value)
		except ValueError:
			self._error('Invalid literal for int type: ' + t.value)
			t.value = 0
		return t

	def _unescape(self, match_obj):
		substring = match_obj.string[match_obj.start() : match_obj.end()]
		if substring == '"':
			return ''
		elif substring[0] == '\\':
			substring = substring[1:]
			if substring == r'n':
				return '\n'
			elif substring == r't':
				return '\t'
			else:
				self._warn('Unknown string escape: \\ + ' + repr(substring))
				return substring

	def t_STRING(self, t):
		r'" ( [^"\\] | \\. )* "'
		t.value = re.sub(_STRING_re, self._unescape, t.value)
		return t

	def t_IDENT(self, t):
		r'[a-zA-Z][a-zA-Z0-9_]*'
		if t.value in self.types:
			t.type = 'TYPE'
		elif t.value == 'true':
			t.type = 'BOOLEAN'
			t.value = True
		elif t.value == 'false':
			t.type = 'BOOLEAN'
			t.value = False
		else:
			t.type = self.keywords.get(t.value, 'IDENT')
		return t

	def t_newline(self, t):
		r'\n+'
		t.lexer.lineno += len(t.value)
		t.lexer.x = 1

	def t_whitespace(self, t):
		r'[ \t\r\f\v]+'
		t.lexer.x += len(t.value)

	def t_error(self, t):
		ch = t.value[0]
		if ch == '"':
			self._error('Error: Unterminated string')
		else:
			self._error('Illegal character: ' + repr(ch))

	def _error(self, text):
		position = (self.lexer.lineno, self.lexer.x)
		raise LexError(position, text)

	def _warn(self, text):
		position = (self.lexer.lineno, self.lexer.x)
		LexError(position, 'Warning: ' + text).warn()

	def build(self):
		'''Initialize the tokenizer.'''
		self.lexer = lex.lex(object = self, reflags = re.DOTALL | re.MULTILINE | re.VERBOSE)
		self.lexer.x = 1

	def input(self, data):
		'''Feed the tokenizer with data.'''
		return self.lexer.input(data)

	def token(self):
		'''Return a token or None.'''
		token = self.lexer.token()
		if token is not None:
			self.lexer.x += self.lexer.lexpos - token.lexpos
			token.lexpos = (token.lineno, self.lexer.x)
		return token

from error import JtError

class LexError(JtError):
	pass

# vim:ts=4 sw=4
