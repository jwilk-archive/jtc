# encoding=UTF-8
# Copyright © 2007 Jakub Wilk <jwilk@jwilk.net>

'''Error handling of the Javalette programs.'''

class JtError(Exception):

	'''Syntax error of a Javalette program.'''

	@staticmethod
	def _message(position, text):
		if position is None:
			position = '?'
		else:
			position = '%d.%d' % position
		return '[%s] %s' % (position, text)

	def warn(self):
		'''Print the error message to sys.stderr.'''
		from sys import stderr
		print >>stderr, self

	def __init__(self, position, text):
		'''Initalize the exception:
		- 'position' is a (y, x) tuple or None;
		- 'text' is an error message text.'''
		Exception.__init__(self, JtError._message(position, text))

# vim:ts=4 sw=4
