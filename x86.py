# encoding=UTF-8

# Copyright © 2007-2016 Jakub Wilk <jwilk@jwilk.net>
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

'''x86 (IA-32) assembly support.'''

from tempfile import NamedTemporaryFile as mktemp
from subprocess import call
from shutil import copyfileobj

class CompileError(Exception):
    '''An error occurred during compilation.'''
    pass

class NasmError(CompileError):
    '''NASM reported errors.'''
    pass

class GccError(CompileError):
    '''GCC reported errors.'''
    pass

class Env(object):
    def __init__(self, vsp = 0):
        self.vsp = vsp

    def clone(self):
        return Env(self.vsp)

class Const(object):

    '''A sequence of bytes that will remain constant during the program execution.'''

    def __init__(self, *args):
        self.bytes = []
        for arg in args:
            self.bytes += [ord(ch) for ch in arg]
        self.bytes = tuple(self.bytes)

    def __str__(self):
        '''Return a label for the constant.'''
        return ('_c_%x' % id(self)).replace('-', 'M')

class Extern(object):

    '''A symbol declared in an external module.'''

    def __init__(self, symbol):
        self.symbol = symbol

    def __str__(self):
        return self.symbol

class Label(object):

    '''A point in the code with a label.'''

    def __init__(self, name = None, public = False):
        if name is None:
            name = ('_l_%x' % id(self)).replace('-', 'M')
        self.name = name
        self.public = public

    def __str__(self):
        '''Return the label'''
        return self.name

class Return(object):
    '''Pseudo-instruction: clean up the stack and return from a procedure/function.'''
    pass

class SyncESP(object):
    '''Pseudo-instruction: forget any non-yet-performed lazy ESP operations.'''
    pass

class SubESP(object):

    '''Pseudo-instruction: decrease ESP lazily.'''

    def __init__(self, n):
        self.n = n

class AddESP(SubESP):

    '''Pseudo-instruction: increase ESP lazily.'''

    def __init__(self, n):
        SubESP.__init__(self, -n)

def _maybe_mktemp(file, *args, **kwargs):
    if file is None or file.name.startswith('<'):
        return mktemp(*args, **kwargs)
    else:
        return file

def _maybe_copy(in_file, out_file):
    if out_file is not None and out_file != in_file:
        copyfileobj(in_file, out_file)
        return out_file
    else:
        return in_file

def _maybe_close(tmp_file, orig_file):
    if tmp_file == orig_file:
        return
    try:
        tmp_file.close()
    except OSError:
        pass
    raise GccError()

_stack_ops = \
{
    'call': 0,
    'enter': NotImplemented,
    'leave': NotImplemented,
    'int': 0,
    'int1': 0,
    'int01': 0,
    'icebp': 0,
    'int3': 0,
    'int03': 0,
    'into': 0,
    'iret': 0,
    'iretw': NotImplemented,
    'iretd': 0,
    'pop': -4,
    'popa': 8 * -4,
    'popaw': NotImplemented,
    'popad': 8 * -4,
    'popf': -4,
    'popfw': NotImplemented,
    'popfd': -4,
    'push': 4,
    'pusha': 8 * 4,
    'pushaw': NotImplemented,
    'pushad': 8 * 4,
    'pushf': 4,
    'pushfw': NotImplemented,
    'pushfd': 4,
    'ret': 0,
    'retn': 0,
    'retf': NotImplemented
}

_jmp_ops = \
set((
    'jmp',
    'jcxz', 'jecxz',
    'ja', 'jae', 'jb', 'jbe', 'jc', 'je', 'jg', 'jge', 'jl', 'jle', 'jna', 'jnae', 'jnb', 'jnbe', 'jnc',
    'jne', 'jng', 'jnge', 'jnl', 'jnle', 'jno', 'jnp', 'jns', 'jnz', 'jo', 'jp', 'jpe', 'jpo', 'js', 'jz'
))

import re

_sj_ops_re = re.compile(r'\be?sp\b|^(%s)\b' % '|'.join(set(_stack_ops) | _jmp_ops))
_bp_re = re.compile(r'##\((-?\d+)\)')

def compile(listing, o_file = None):
    '''Compile the x86 assembly code into an executable ELF file.'''
    asm_file = mktemp(prefix = 'jtc', suffix = '.asm')
    o_file_tmp = _maybe_mktemp(o_file, prefix = 'jtc', suffix = '.o')
    consts = {}
    esp = 0
    lazy_esp = 0
    print >>asm_file, 'BITS 32'
    print >>asm_file, 'SECTION .text'
    for line in listing:
        if isinstance(line, Const):
            bytes = line.bytes
            if bytes in consts:
                consts[bytes] += line,
            else:
                consts[bytes] = [line]
        elif isinstance(line, Extern):
            print >>asm_file, 'EXTERN %s' % line
        elif isinstance(line, SubESP):
            lazy_esp -= line.n
        elif isinstance(line, SyncESP):
            lazy_esp = 0
            esp = 0
        elif isinstance(line, Return):
            if esp:
                print >>asm_file, '\tadd esp, %d' % esp
            print >>asm_file, '\tret'
        else:
            was_label = isinstance(line, Label)
            if was_label and line.public:
                print >>asm_file, 'GLOBAL %s' % line
            line = str(line)
            if was_label:
                line += ':'
            was_instr = line[:1].islower() and not was_label
            if was_instr:
                op = line.split(None, 1)[0]
                if op in _stack_ops:
                    diff_esp = _stack_ops[op]
                    if diff_esp == NotImplemented:
                        raise NotImplementedError('The "%s" x86 instruction is not supported' % op)
                    esp += diff_esp
            if lazy_esp != 0 and (_sj_ops_re.search(line) or was_label):
                print >>asm_file, '\tlea esp, [esp + %d]' % lazy_esp
                esp -= lazy_esp
                lazy_esp = 0
            if was_instr:
                line = re.sub(_bp_re, lambda m: 'esp + %d' % (int(m.group(1)) + esp), line)
                line = '\t' + line
            print >>asm_file, line
    for bytes, lines in consts.iteritems():
        for line in lines:
            print >>asm_file, '%s:' % line
        print >>asm_file, '\tDB %s' % ','.join(str(byte) for byte in bytes)
    asm_file.flush()
    retcode = call(['nasm', '-O3', '-f', 'elf', asm_file.name, '-o', o_file_tmp.name])
    asm_file.close()
    if retcode == 0:
        return _maybe_copy(o_file_tmp, o_file)
    else:
        _maybe_close(o_file_tmp, o_file)
        raise NasmError()

def link(o_file, x_file = None):
    '''Link the ELF object file into an executable ELF file.'''
    x_file_tmp = _maybe_mktemp(x_file, prefix = 'jtc')
    if call(['gcc', '-m32', o_file.name, '-o', x_file_tmp.name]) == 0:
        return _maybe_copy(x_file_tmp, x_file)
    else:
        _maybe_close(x_file_tmp, x_file)
        raise GccError()

def build(listing, x_file):
    '''Build the x86 assembly code into an executable ELF file.'''
    return link(compile(listing), x_file)

# vim:ts=4 sts=4 sw=4 et
