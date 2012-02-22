# encoding=UTF-8
# Copyright © 2012 Jakub Wilk <jwilk@jwilk.net>

import sys

from byteplay import *
from byteplay import __all__

if sys.version_info >= (2, 7):

	def jump_if_false(label):
		return [(JUMP_IF_FALSE_OR_POP, label)]

	def jump_if_true(label):
		return [(JUMP_IF_TRUE_OR_POP, label)]

else:

	def jump_if_false(label):
		return \
		[
			(JUMP_IF_FALSE, label),
			(POP_TOP, None)
		]

	def jump_if_true(label):
		return \
		[
			(JUMP_IF_TRUE, label),
			(POP_TOP, None)
		]

__all__ = list(__all__) + ['jump_if_true', 'jump_if_false']

# vim:ts=4 sw=4
