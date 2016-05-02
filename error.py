# encoding=UTF-8

# Copyright © 2007 Jakub Wilk <jwilk@jwilk.net>
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the “Software”), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED “AS IS”, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
		'''Initialize the exception:
		- 'position' is a (y, x) tuple or None;
		- 'text' is an error message text.'''
		Exception.__init__(self, JtError._message(position, text))

# vim:ts=4 sts=4 sw=4
