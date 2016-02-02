# encoding=UTF-8

# Copyright © 2007, 2012 Jakub Wilk <jwilk@jwilk.net>
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

'''Expression nodes of Javalette syntax trees.'''

import syntax
import type
from syntax import TypeMismatch
from type import int_t, double_t, boolean_t, void_t
from builtins import x86_0div_error

import bp
import x86

__all__ = ['expression', 'assignment', 'binary_operator', 'call', 'cast', 'const', 'reference', 'unary_operator']

class expression(syntax.base):

	'''An expression.'''

	def __init__(self):
		self.type = None
		self.position = None

	def get_var_refs(self):
		raise NotImplementedError()

	def validate(self):
		ok = self._validate()
		if self.type is None:
			self._update_type()
		ok &= self.type is not None
		return ok

	def _validate(self):
		raise NotImplementedError()

	def _update_type(self):
		raise NotImplementedError()

	def check_var_usage(self, lsv, rsv):
		raise NotImplementedError()

	def py_cast_to(self, type):
		'''[py] Generate code for type-casting the expression value.'''
		return self.type.py_cast_to(type)

	def x86_asm_push(self, env):
		'''[x86] Generate code for pushing the expression value on the stack.'''
		return self.to_x86_asm(env) + self.type.x86_asm_push(env)

	def x86_asm_discard(self, env):
		'''[x86] Generate code for discarding the expression value.'''
		return self.type.x86_asm_discard(env)

	def x86_size(self):
		'''[x86] Return size of the expression value, in bytes.'''
		return self.type.x86_size()

	def x86_asm_cast_to(self, type, env):
		'''[x86] Generate code for type-casting the expression value.'''
		return self.type.x86_asm_cast_to(type, env)

	def is_evaluatable(self):
		'''Return whether the expression can be used in an evaluation statement,
		even without an explicit type-cast to <void>.'''
		return self.type == void_t

	_doc = \
	{
		'is_evaluatable': 'Return whether the expression can be used in an evaluation statement,\neven without an explicit type-cast to <void>.'
	}
	for _method in ('validate', 'to_py', 'to_x86_asm', 'get_var_refs', 'check_var_usage'):
		_doc[_method] = syntax.base._doc[_method]
	del _method

class const(expression):

	'''A constant.'''

	def __init__(self, value, type, position):
		expression.__init__(self)
		self.position = position
		self.value = value
		self.type = type

	def _validate(self):
		return True

	def get_var_refs(self):
		return ()

	def check_var_usage(self, lsv, rsv):
		return True

	def to_py(self):
		return \
		[
			(bp.SetLineno, self.y),
			(bp.LOAD_CONST, self.value)
		]

	def to_x86_asm(self, env):
		return self.type.x86_asm_const(self.value, env)

	def __str__(self):
		return repr(self.value)

_binary_numeric_ops = set(('+', '-', '*', '/', '%'))
_inequality_ops = set(('<', '<=', '>', '>='))
_equality_ops = set(('==', '!='))
_binary_logical_ops = set(('&&', '||'))
_commutative_binary_ops = set(('+', '*', '==', '!=', '&&', '||'))

_py_binary_numeric_op = \
{
	'+':             bp.BINARY_ADD,
	'-':             bp.BINARY_SUBTRACT,
	'*':             bp.BINARY_MULTIPLY,
	('/', int_t):    bp.BINARY_FLOOR_DIVIDE,
	('/', double_t): bp.BINARY_TRUE_DIVIDE,
	'%':             bp.BINARY_MODULO
}

_py_binary_logical_op = \
{
	'&&': bp.jump_if_false,
	'||': bp.jump_if_true,
}


_x86_binary_int_op = \
{
	'+':  ['add eax, ecx'],
	'-':  ['sub eax, ecx'],
	'*':  ['imul ecx'],
}

_x86_binary_double_op = \
{
	'+': 'add',
	'-': 'subr',
	'*': 'mul',
	'/': 'divr'
}

_x86_inequality_int_op = \
{
	'<':  'l',
	'<=': 'le',
	'>=': 'ge',
	'>':  'g',
	'==': 'e',
	'!=': 'ne',
}

_x86_inequality_double_op = \
{
	'<':  'b',
	'<=': 'be',
	'>=': 'ae',
	'>':  'a',
	'==': 'e',
	'!=': 'ne',
}

_x86_binary_logical_op = \
{
	'&&': 'z',
	'||': 'nz'
}

class binary_operator(expression):

	__doc__ = '\n'.join(
	[
		'A binary operation.',
		'Available operators:',
		'- arithmetic operators: %s;' % ', '.join(map(repr, _binary_numeric_ops)),
		'- inequality operators: %s;' % ', '.join(map(repr, _inequality_ops)),
		'- equality operators: %s;' % ', '.join(map(repr, _inequality_ops)),
		'- logical connectives: %s.' % ', '.join(map(repr, _inequality_ops))
	])

	def __init__(self, operator, left_operand, right_operand, position):
		expression.__init__(self)
		self.position = position
		self.operator = operator
		self.left = left_operand
		self.right = right_operand

	def get_var_refs(self):
		result = []
		if isinstance(self.left, expression):
			result += self.left.get_var_refs()
		if isinstance(self.right, expression):
			result += self.right.get_var_refs()
		return result

	def _validate(self):
		ok =   self.left.validate()
		ok &= self.right.validate()
		return ok

	def _update_type(self):
		ltype = self.left.type
		rtype = self.right.type
		op = self.operator
		if ltype is None or rtype is None:
			return
		if op in _binary_numeric_ops:
			if ltype == rtype and ltype in type.numeric_types:
				self.type = ltype
			else:
				expected = ' or '.join('<%s> %s <%s>' % (t, op, t) for t in sorted(map(str, type.numeric_types)))
				TypeMismatch(self.position,
					'Incompatible types: <%s> %s <%s> provided but %s expected' %
					(ltype, op, rtype, expected)).warn()
		elif op in _inequality_ops:
			if ltype == rtype and ltype in type.ineq_comparable_types:
				self.type = boolean_t
			else:
				expected = ' or '.join('<%s> %s <%s>' % (t, op, t) for t in sorted(map(str, type.ineq_comparable_types)))
				TypeMismatch(self.position,
					'Incompatible types: <%s> %s <%s> provided but %s expected' %
					(ltype, op, rtype, expected)).warn()
		elif op in _binary_logical_ops:
			if ltype == rtype == boolean_t:
				self.type = boolean_t
			else:
				TypeMismatch(self.position,
					'Incompatible types: <%s> %s <%s> provided but <boolean> %s <boolean> expected' %
					(ltype, op, rtype, op)).warn()
		elif op in _equality_ops:
			if ltype == rtype and ltype in type.eq_comparable_types:
				self.type = boolean_t
			else:
				expected = ' or '.join('<%s> %s <%s>' % (t, op, t) for t in sorted(map(str,type.eq_comparable_types)))
				TypeMismatch(self.position,
					'Incompatible types: <%s> %s <%s> provided but %s expected' %
					(ltype, op, rtype, expected)).warn()
		else:
			raise NotImplementedError('Type checking for binary operator %s' % op)

	def check_var_usage(self, lsv, rsv):
		ok  =  self.left.check_var_usage(lsv, rsv)
		ok &= self.right.check_var_usage(lsv, rsv)
		return ok

	def to_py(self):
		lpy = self.left.to_py()
		rpy = self.right.to_py()
		op = self.operator
		if op in _binary_logical_ops:
			label = bp.Label()
			condition = _py_binary_logical_op[op]
			result = []
			result += lpy
			result += [(bp.SetLineno, self.y)]
			result += condition(label)
			result += rpy
			result += (label, None),
			return result
		elif op in _binary_numeric_ops:
			if op in _py_binary_numeric_op:
				result = [(_py_binary_numeric_op[op], None)]
			elif (op, self.type) in _py_binary_numeric_op:
				result = [(_py_binary_numeric_op[(op, self.type)], None)]
			else:
				raise NotImplementedError('Python code for binary operator %s' % op)
			return lpy + rpy + result
		elif op in _inequality_ops | _equality_ops:
			result = [(bp.COMPARE_OP, op)]
		else:
			raise NotImplementedError('Python code for binary operator %s' % op)
		return lpy + rpy + [(bp.SetLineno, self.y)] + result

	def to_x86_asm(self, env):
		op = self.operator
		if op in _binary_logical_ops:
			label = x86.Label()
			condition = _x86_binary_logical_op[op]
			result = []
			result += self.left.to_x86_asm(env)
			result += \
			[
				'or eax, eax',
				'j%s %s' % (condition, label),
			]
			result += self.left.x86_asm_discard(env)
			result += self.right.to_x86_asm(env)
			result += label,
			return result
		lx = self.left.x86_asm_push(env)
		rx = self.right.to_x86_asm(env)
		if isinstance(self.left.type, type.x86_dword_type):
			result = lx + rx + ['pop ecx']
			if op in _x86_inequality_int_op:
				result += \
				[
					'cmp ecx, eax',
					'set%s al' % _x86_inequality_int_op[op],
					'and eax, 1'
				]
				return result
			if op not in _commutative_binary_ops:
				result += 'xchg eax, ecx',
			if op in _x86_binary_int_op:
				result += _x86_binary_int_op[op]
				return result
			if op in ('%', '/'):
				result += \
				[
					'or ecx, ecx',
					'jz %s' % x86_0div_error,
					'cdq',
					'idiv ecx'
				]
				if op == '%':
					label = x86.Label()
					result += \
					[
						'mov eax, edx',
						'or eax, eax',
						'jz %s' % label,
						'mov edx, ecx',
						'xor ecx, eax',
						'jns %s' % label,
						'add eax, edx',
						label,
					]
				return result
		elif self.left.type == double_t:
			result = lx + rx + ['fld QWORD [esp]', x86.AddESP(8)]
			if op in _x86_binary_double_op:
				return result + ['f%sp st1' % _x86_binary_double_op[op]]
			elif op == '%':
				label = x86.Label()
				const = x86.Const('touch:\0')
				result += \
				[
					const,
					'fprem1',
					'fldz',            # st0 = 0,     st1 = r,    st2 = b
					'fucomi st0, st1',
					'je %s' % label,
					'seta al',
					'fucomi st0, st2',
					'seta dl',
					'cmp al, dl',
					'je %s' % label,
					'fxch st1',        # st0 = r,     st1 = 0,    st2 = b
					'fadd st2',        # st0 = r + b, st1 = 0
					'fxch st1',        #              st1 = r + b
					label,
					'fstp st0',
					'ffree st1'
				]
				return result
			elif op in _x86_inequality_double_op:
				result += \
				[
					'fucomip st1',
					'set%s al' % _x86_inequality_double_op[op],
					'and eax, 1',
				]
				result += double_t.x86_asm_discard(env) * 2
				return result
		raise NotImplementedError('X86 code for binary operator <%s> %s <%s>' % (self.left.type, self.operator, self.right.type))

	def __str__(self):
		return '(%s %s %s)' % (self.left, self.operator, self.right)

_unary_logical_ops = set(('!',))
_unary_numeric_ops = set(('+', '-'))

_py_unary_op = \
{
	'!': bp.UNARY_NOT,
	'+': bp.UNARY_POSITIVE,
	'-': bp.UNARY_NEGATIVE
}

_x86_unary_dword_op = \
{
	'!': ['xor eax, 1'],
	'+': [],
	'-': ['neg eax']
}

_x86_unary_double_op = \
{
	'-': ['fldz', 'fsubrp st1'],
	'+': []
}

class unary_operator(expression):

	__doc__ = '\n'.join(
	[
		'A unary operation.',
		'Available operators:',
		'- arithmetic operators: %s;' % ', '.join(map(repr, _unary_numeric_ops)),
		'- logical connectives: %s.' % ', '.join(map(repr, _unary_logical_ops)),
	])

	def __init__(self, operator, operand, position):
		expression.__init__(self)
		self.operator = operator
		self.left = operand
		self.position = position

	def get_var_refs(self):
		if isinstance(self.left, expression):
			return self.left.get_var_refs()
		else:
			return ()

	def _validate(self):
		return self.left.validate()

	def _update_type(self):
		ltype = self.left.type
		if ltype is None:
			return
		if self.operator in _unary_logical_ops:
			if ltype == boolean_t:
				self.type = boolean_t
			else:
				TypeMismatch(self.position,
					'Incompatible types: %s <%s> provided but %s <boolean> expected' %
					(self.operator, ltype, self.operator)).warn()
		elif self.operator in _unary_numeric_ops:
			if ltype in (int_t, double_t):
				self.type = ltype
			else:
				TypeMismatch(self.position,
					'Incompatible types: %s <%s> provided but %s <int> or %s <double> expected' %
					(self.operator, ltype, self.operator, self.operator)).warn()
		else:
			raise NotImplementedError('Type checking for unary operator %s' % self.operator)

	def check_var_usage(self, lsv, rsv):
		return self.left.check_var_usage(lsv, rsv)

	def to_py(self):
		return self.left.to_py() + [(bp.SetLineno, self.y), (_py_unary_op[self.operator], None)]

	def to_x86_asm(self, env):
		op = self.operator
		if isinstance(self.left.type, type.x86_dword_type):
			return self.left.to_x86_asm(env) + _x86_unary_dword_op[op]
		elif self.left.type == double_t:
			return self.left.to_x86_asm(env) + _x86_unary_double_op[op]
		raise NotImplementedError('X86 code for unary operator %s <%s>' % (self.operator, self.left.type))

	def __str__(self):
		return '(%s %s)' % (self.operator, self.left)

class reference(expression):

	'''A reference to a variable, by its identifier.'''

	def __init__(self, identifier, position):
		expression.__init__(self)
		self.ident = identifier
		self.bind = None
		self.position = position

	def get_var_refs(self):
		return self,

	def _validate(self):
		return True

	def _update_type(self):
		if self.bind is None:
			return
		self.type = self.bind.type

	def check_var_usage(self, lsv, rsv):
		if self.bind == None:
			return True
		rsv.add(self.bind)
		if self.bind in lsv:
			return True
		else:
			ReferenceBeforeAssignment(self.position, 'Possible reference before assignment').warn()
			return False

	def to_py(self):
		return self.bind.py_read()

	def py_write(self, **kwargs):
		return self.bind.py_write(**kwargs)

	def to_x86_asm(self, env):
		return self.bind.x86_asm_read(env)

	def x86_asm_write(self, value, env):
		return self.bind.x86_asm_write(value, env)

	def __str__(self):
		prefix = '$'
		if self.bind is None:
			prefix = '?'
		return prefix + self.ident

class call(expression):

	'''A function call.'''

	def __init__(self, function, arguments, position):
		expression.__init__(self)
		self.function = function
		self.arguments = arguments
		self.position = position

	def get_var_refs(self):
		result = [self.function]
		for argument in self.arguments:
			result += argument.get_var_refs()
		return result

	def validate(self):
		return expression.validate(self) and self._post_validate()

	def _validate(self):
		ok = self.function.validate()
		for argument in self.arguments:
			ok &= argument.validate()
		return ok

	def _update_type(self):
		if self.function.type is not None:
			self.type = self.function.type.return_type

	def _post_validate(self):
		ok = True
		function = self.function.bind
		arg_type_list = function.type.arg_type_list
		argc = len(arg_type_list)
		if len(self.arguments) != argc:
			ArityMismatch(self.position,
				"'%s' takes exactly %d argument%s but %d provided" %
				(self.function.ident, argc, argc != 1 and 's' or '', len(self.arguments))).warn()
			return False
		else:
			i = 0
			for (argument, type) in zip(self.arguments, arg_type_list):
				i += 1
				if argument.type is None:
					continue
				if argument.type != type:
					ok = False
					TypeMismatch(argument.position,
						"Incompatible type for argument %d of '%s': <%s> provided but <%s> expected" %
						(i, function.name, argument.type, type)).warn()
		return ok

	def check_var_usage(self, lsv, rsv):
		ok = True
		for expression in self.arguments:
			ok &= expression.check_var_usage(lsv, rsv)
		return ok

	def to_py(self):
		result = []
		result += self.function.to_py()
		for argument in self.arguments:
			result += argument.to_py()
		result += \
		[
			(bp.SetLineno, self.y),
			(bp.CALL_FUNCTION, len(self.arguments))
		]
		return result

	def to_x86_asm(self, env):
		result = []
		size = 0
		for argument in self.arguments[::-1]:
			result += argument.x86_asm_push(env)
			size += argument.x86_size()
		result += 'call %s' % self.function.bind.x86_name,
		result += x86.AddESP(size),
		return result

	def __str__(self):
		return '%s(%s)' % (self.function, ', '.join(str(arg) for arg in self.arguments))

class cast(expression):

	'''A type-cast.'''

	def __init__(self, operand, type, position):
		expression.__init__(self)
		self.expression = operand
		self.cast_type = type
		self.position = position

	def get_var_refs(self):
		if self.expression is not None:
			return self.expression.get_var_refs()
		else:
			return ()

	def _validate(self):
		return self.expression.validate()

	def _update_type(self):
		xtype = self.expression.type
		if xtype is None:
			return
		ctype = self.cast_type
		if xtype.is_castable_to(ctype):
			self.type = ctype
		else:
			TypeMismatch(self.position,
				'Incompatible types: cannot cast <%s> to <%s>' %
				(xtype, ctype)).warn()

	def check_var_usage(self, lsv, rsv):
		return self.expression.check_var_usage(lsv, rsv)

	def to_py(self):
		result = self.expression.to_py()
		result += self.expression.py_cast_to(self.cast_type)
		return result

	def to_x86_asm(self, env):
		result = self.expression.to_x86_asm(env)
		result += self.expression.x86_asm_cast_to(self.cast_type, env)
		return result

	def __str__(self):
		return 'cast (%s) as %s' % (self.expression, self.cast_type)

class assignment(expression):

	'''An assignment.'''

	def __init__(self, lvalue, rvalue, position):
		expression.__init__(self)
		self.lvalue = lvalue
		self.rvalue = rvalue
		self.position = position

	def validate(self):
		ok  = self.lvalue.validate()
		ok &= self.rvalue.validate()
		if ok:
			ltype = self.lvalue.type
			rtype = self.rvalue.type
			if ltype != rtype:
				TypeMismatch(self.position,
					'Incompatible types in assignment: <%s> provided but <%s> expected' % (ltype, rtype)).warn()
				return False
			else:
				self.type = ltype
		return ok

	def get_var_refs(self):
		result = [self.lvalue]
		result += self.rvalue.get_var_refs()
		return result

	def check_var_usage(self, lsv, rsv):
		ok = self.rvalue.check_var_usage(lsv, rsv)
		lvar = self.lvalue.bind
		if lvar is not None:
			lsv.add(lvar)
		return ok

	def to_py(self):
		return [(bp.SetLineno, self.y)] + self.lvalue.py_write(value = self.rvalue, pop = False)

	def to_x86_asm(self, env):
		return self.lvalue.x86_asm_write(self.rvalue, env)

	def is_evaluatable(self):
		return True

	def __str__(self):
		return '%s := %s' % (self.lvalue, self.rvalue)

from error import JtError

class ArityMismatch(JtError):
	pass

class ReferenceBeforeAssignment(JtError):
	pass

_globals = list(globals().itervalues())
for _item in _globals:
	try:
		if expression not in _item.__mro__:
			continue
	except AttributeError:
		continue
	for _method, _doc in expression._doc.iteritems():
		try:
			_method = getattr(_item, _method)
		except AttributeError:
			continue
		if _method.__doc__ is None:
			_method.im_func.__doc__ = _doc
del _globals, _method, _item, _doc

# vim:ts=4 sw=4
