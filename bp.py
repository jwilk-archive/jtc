# encoding=UTF-8

# Copyright © 2012 Jakub Wilk <jwilk@jwilk.net>
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
        return [
            (JUMP_IF_FALSE, label),
            (POP_TOP, None)
        ]

    def jump_if_true(label):
        return [
            (JUMP_IF_TRUE, label),
            (POP_TOP, None)
        ]

__all__ = list(__all__) + ['jump_if_true', 'jump_if_false']

# vim:ts=4 sts=4 sw=4 et
