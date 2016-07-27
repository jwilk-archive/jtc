# encoding=UTF-8

# Copyright © 2007-2012 Jakub Wilk <jwilk@jwilk.net>
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

'''Usage:
\tjtc [-T|-P|-X] [-o <output_file>] <source_file>

Options:
\t-T\tpretty print
\t-P\tcompile to python bytecode (default)
\t-X\tcompile to x86 machine code
'''

from getopt import GetoptError, gnu_getopt as getopt
import sys

def usage():
    print >>sys.stderr, __doc__
    sys.exit(1)

def failure(message=None):
    if message is not None:
        print >>sys.stderr, message
    print >>sys.stderr, 'Compilation failed!'
    sys.exit(2)

def main(args):
    try:
        (opts, args) = getopt(args, 'o:TPX')
    except GetoptError:
        usage()
    if len(args) != 1:
        usage()

    from tokenizer import Tokenizer
    from parser import Parser
    from error import JtError
    import context
    from os.path import abspath

    filename = abspath(args[0])
    stdin = file(filename, 'r')
    target = 'P'
    stdout = sys.stdout
    for (ok, ov) in opts:
        if ok in ('-T', '-P', '-X'):
            target = ok[1]
        elif ok == '-o':
            stdout = file(ov, 'w')
    contents = stdin.read()
    tokenizer = Tokenizer()
    tokenizer.build()
    tokenizer.input(contents)
    parser = Parser(tokenizer)
    result_tree = None
    try:
        result_tree = parser.parse()
    except JtError, error:
        failure(error)
    context.add_pdf(result_tree)
    ok = context.inspect(result_tree)
    ok &= context.validate(result_tree)
    if target == 'T':
        print >>stdout, result_tree
    if not ok:
        failure()
    result_tree.filename = filename

    if target != 'T':
        if stdout.isatty():
            failure('Prevented from printing binary garbage to the terminal.')
        if target == 'P':
            result_tree.compile_pyc(stdout)
        elif target == 'X':
            result_tree.compile_x86(stdout)
        else:
            raise NotImplementedError()

# vim:ts=4 sts=4 sw=4 et
