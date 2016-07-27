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

'''Built-ins for the Javalette language.'''

import sys

import syntax
import type

import bp
import x86

_py_globals = {
    'bool': '*bool',
    'int': '*int',
    'float': '*float',
    'raw_input': '*input',
    'RuntimeError': '*error'
}
py_stub_pre = sum(
    [[(bp.LOAD_GLOBAL, _name), (bp.STORE_GLOBAL, _alias)] for _name, _alias in _py_globals.iteritems()],
    []
)
del _name, _alias

_stub_label = bp.Label()
py_stub_post = filter(None,
[
    (bp.BUILD_LIST, 0),
    (bp.STORE_GLOBAL, '__all__'),
    (bp.LOAD_GLOBAL, '__name__'),
    (bp.LOAD_CONST, '__main__'),
    (bp.COMPARE_OP, '=='),
] + bp.jump_if_false(_stub_label) + [
    sys.version_info >= (2, 5) and (bp.LOAD_CONST, -1),
    (bp.LOAD_CONST, None),
    (bp.IMPORT_NAME, 'sys'),
    (bp.IMPORT_FROM, 'exit'),
    (bp.LOAD_GLOBAL, 'main'),
    (bp.CALL_FUNCTION, 0),
    (bp.CALL_FUNCTION, 1),
    (bp.POP_TOP, None),
    (_stub_label, None),
    (bp.RETURN_VALUE, None)
])
del _stub_label

_label_io_error = x86.Label()
x86_0div_error = x86.Label()
_s_io_error = x86.Const('IOError\n\0')
_s_0div_error = x86.Const('ZeroDivisionError\n\0')
_x_stderr = x86.Extern('stderr')
_x_fputs = x86.Extern('fputs')
_x_exit = x86.Extern('exit')
x86_stub = [
    _s_io_error, _s_0div_error,
    _x_stderr, _x_fputs, _x_exit,
    x86.Label('main', public=True),
    'jmp _f_main',
    _label_io_error,
    'push DWORD [%s]' % _x_stderr,
    'push %s' % _s_io_error,
    'call %s' % _x_fputs,
    'push 1',
    'call %s' % _x_exit,
    x86_0div_error,
    'push DWORD [%s]' % _x_stderr,
    'push %s' % _s_0div_error,
    'call %s' % _x_fputs,
    'push 1',
    'call %s' % _x_exit
]
del _s_io_error, _s_0div_error

from os.path import basename as _basename
this_module_file_name = '<%s>' % _basename((lambda: None).func_code.co_filename)

class pdf_function(syntax.function):

    '''A built-in function/procedure'''

    class _pdf_block(syntax.block_statement):
        def __init__(self):
            syntax.block.__init__(self, [])

        def __str__(self):
            return syntax.block.indent('<pre-defined function>')

    def validate(self):
        '''Returns True. Built-in functions are always valid.'''
        return True

    def __init__(self, name, return_type, *arg_types):
        self.type = type.function_type(return_type, arg_types)
        syntax.variable.__init__(self, self.type, name, pdf_function._pdf_block(), None)

    @staticmethod
    def construct_all():
        '''Return a sequence of all known built-in functions.'''
        return (
            pdf_print_int(),
            pdf_print_double(),
            pdf_print_string(),
            pdf_error(),
            pdf_read_int(),
            pdf_read_double())

    def body_to_pyc(self, filename):
        code = bp.Code(
            code=self.py,
            freevars=[],
            args=['_%d' % n for n in xrange(len(self.type.arg_type_list))],
            varargs=False,
            varkwargs=False,
            newlocals=True,
            name=self.name,
            filename=this_module_file_name,
            firstlineno=0,
            docstring=None)
        return code

    body_to_pyc.__doc__ = syntax.function.body_to_pyc.im_func.__doc__

    def to_x86_asm(self):
        result = []
        result += x86.Label(self.x86_name),
        result += self.x86_asm
        return result

    to_x86_asm.__doc__ = syntax.function.to_x86_asm.im_func.__doc__

_py_pdf_print = [
    (bp.LOAD_FAST, '_0'),
    (bp.PRINT_ITEM, None),
    (bp.PRINT_NEWLINE, None),
    (bp.LOAD_CONST, None),
    (bp.RETURN_VALUE, None)
]

_py_pdf_error = [
    (bp.LOAD_GLOBAL, '*error'),
    (bp.CALL_FUNCTION, 0),
    (bp.RAISE_VARARGS, 1),
    (bp.LOAD_CONST, None),
    (bp.RETURN_VALUE, None)
]

_py_pdf_read_int = [
    (bp.LOAD_GLOBAL, '*int'),
    (bp.LOAD_GLOBAL, '*input'),
    (bp.CALL_FUNCTION, 0),
    (bp.CALL_FUNCTION, 1),
    (bp.RETURN_VALUE, None)
]

_py_pdf_read_double = [
    (bp.LOAD_GLOBAL, '*float'),
    (bp.LOAD_GLOBAL, '*input'),
    (bp.CALL_FUNCTION, 0),
    (bp.CALL_FUNCTION, 1),
    (bp.RETURN_VALUE, None)
]

_const = x86.Const('%d\n\0')
_x_printf = x86.Extern('printf')
_x86_pdf_print_int = [
    _const, _x_printf,
    'push DWORD [esp + 4]',
    'push %s' % _const,
    'call %s' % _x_printf,
    'test eax, eax',
    'js %s' % _label_io_error,
    'add esp, 8',
    'ret'
]
del _const

_const = x86.Const('%.12g\0')
_x_snprintf = x86.Extern('snprintf')
_x_puts = x86.Extern('puts')
_label_loop = x86.Label()
_label_exit_loop = x86.Label()
_x86_pdf_print_double = [
    _const, _x_snprintf, _x_puts,
    'sub esp, 36',
    'mov edx, esp',
    'push DWORD [esp + 44]',
    'push DWORD [esp + 44]',
    'push %s' % _const,
    'push 32',
    'push edx',
    'call %s' % _x_snprintf,
    'test eax, eax',
    'js %s' % _label_io_error,
    'add esp, 20',
    'lea edx, [esp - 1]',
    _label_loop,
    'inc edx',
    'mov al, [edx]',
    'cmp al, "-"',
    'je %s' % _label_loop,
    'cmp al, "."',
    'je %s' % _label_exit_loop,
    'cmp al, "9"',
    'ja %s' % _label_exit_loop,
    'cmp al, 0',
    'jne %s' % _label_loop,
    'mov eax, ".0"',
    'mov [edx], eax',
    _label_exit_loop,
    'push esp',
    'call %s' % _x_puts,
    'add esp, 40',
    'test eax, eax',
    'js %s' % _label_io_error,
    'ret'
]
del _const
del _label_loop, _label_exit_loop

_x86_pdf_print_string = [
    _x_puts,
    'push DWORD [esp + 4]',
    'call %s' % _x_puts,
    'test eax, eax',
    'js %s' % _label_io_error,
    'add esp, 4',
    'ret'
]

_const = x86.Const('RuntimeError\n\0')
_x86_pdf_error = [
    _const, _x_fputs, _x_exit,
    'push DWORD [stderr]',
    'push %s' % _const,
    'call %s' % _x_fputs,
    'push 1',
    'call %s' % _x_exit
]
del _const

_const = x86.Const('%d\0')
_x_scanf = x86.Extern('scanf')
_x86_pdf_read_int = [
    _const, _x_scanf,
    'sub esp, 4',
    'mov eax, esp',
    'push eax',
    'push %s' % _const,
    'call %s' % _x_scanf,
    'dec eax',
    'jnz %s ' % _label_io_error,
    'add esp, 12',
    'mov eax, [esp - 4]',
    'ret'
]
del _const

_const = x86.Const('%lf\0')
_x86_pdf_read_double = [
    _const, _x_scanf,
    'sub esp, 8',
    'mov eax, esp',
    'push eax',
    'push %s' % _const,
    'call %s' % _x_scanf,
    'dec eax',
    'jnz %s' % _label_io_error,
    'add esp, 16',
    'fld QWORD [esp - 8]',
    'ret'
]
del _const

class pdf_print_int(pdf_function):

    '''printInt(int) built-in function.'''

    def __init__(self):
        self.py = _py_pdf_print
        self.x86_asm = _x86_pdf_print_int
        pdf_function.__init__(self, 'printInt', type.void_t, type.int_t)

class pdf_print_double(pdf_function):

    '''printDouble(double) built-in function.'''

    def __init__(self):
        self.py = _py_pdf_print
        self.x86_asm = _x86_pdf_print_double
        pdf_function.__init__(self, 'printDouble', type.void_t, type.double_t)

class pdf_print_string(pdf_function):

    '''printString("...") built-in function.'''

    def __init__(self):
        self.py = _py_pdf_print
        self.x86_asm = _x86_pdf_print_string
        pdf_function.__init__(self, 'printString', type.void_t, type.string_t)

class pdf_error(pdf_function):

    '''error() built-in procedure.'''

    def __init__(self):
        self.py = _py_pdf_error
        self.x86_asm = _x86_pdf_error
        pdf_function.__init__(self, 'error', type.void_t)

class pdf_read_int(pdf_function):

    '''readInt() built-in function.'''

    def __init__(self):
        self.py = _py_pdf_read_int
        self.x86_asm = _x86_pdf_read_int
        pdf_function.__init__(self, 'readInt', type.int_t)

class pdf_read_double(pdf_function):

    '''readDouble() built-in function.'''

    def __init__(self):
        self.py = _py_pdf_read_double
        self.x86_asm = _x86_pdf_read_double
        pdf_function.__init__(self, 'readDouble', type.double_t)

del _label_io_error
del _x_stderr, _x_fputs, _x_exit, _x_snprintf, _x_puts

# vim:ts=4 sts=4 sw=4 et
