# Copyright (c) 2007 Jakub Wilk <jwilk@jwilk.net>

'''Types of the Javalette language.'''

import byteplay as bp
import x86

from struct import pack

__all__ = \
[
'simple_type',
'void_type', 'x86_dword_type', 'boolean_type', 'int_type', 'double_type', 'string_type', 'function_type',
'void_t', 'boolean_t', 'int_t', 'double_t', 'string_t', 'main_t',
'eq_comparable_types', 'ineq_comparable_types', 'numeric_types'
]

eq_comparable_types = set()
ineq_comparable_types = set()
numeric_types = set()

class base(object):

	'''An abstract type.'''

	def __init__(self):
		global eq_comparable_types, ineq_comparable_types, numeric_types
		if (self.is_eq_comparable()):
			eq_comparable_types.add(self)
		if (self.is_ineq_comparable()):
			ineq_comparable_types.add(self)
		if (self.is_numeric()):
			numeric_types.add(self)

	def is_eq_comparable(self):
		return False

	def is_ineq_comparable(self):
		return False

	def is_numeric(self):
		return False

	def is_castable_to(self, type):
		return isinstance(type, void_type)

	def py_cast_to(self, type):
		global void_type
		if isinstance(type, void_type):
			return \
			[
				(bp.POP_TOP, None),
				(bp.LOAD_CONST, None)
			]
		else:
			return NotImplemented

	_doc = \
	{
		'is_eq_comparable': "Returns whether you can compare values of this type with '==' and '!=' operators.",
		'is_ineq_comparable': "Returns whether you can compare values of this type with '<', '<=', '>' etc. operators.",
		'is_numeric': 'Return whether you can do arithmetic operations on values of this type.',
		'is_castable_to': 'Return whether it is legal to cast this type to an other type.',
		'py_cast_to': '[py] Generate code for type-casting a value of this type to the provided type.',
		'py_cast_from': '[py] Generate code for type-casting a value of the provided type to this type.',
		'x86_asm_push': '[x86] Generate code for pushing a value of this type.',
		'x86_asm_discard': '[x86] Generate code for discarding a value of this type.',
		'x86_size': '[x86] Return size of a value of this type.',
		'x86_asm_cast_to': '[x86] Generate code for type-casting a value of this type to the provided type.',
		'x86_asm_read': '[x86] Generate code for loading value of the variable (of this type).',
		'x86_asm_write': '[x86] Generate code for storing value to the variable (of this type).',
		'x86_asm_const': '[x86] Generate code for loading a constant (of this type).'
	}

def simple_type(type_ident):
	if type_ident == 'int':
		return int_t
	elif type_ident == 'double':
		return double_t
	elif type_ident == 'boolean':
		return boolean_t
	elif type_ident == 'void':
		return void_t

class py_simple_type(base):

	'''[py] An abstract simple type.'''

	def is_eq_comparable(self):
		return True

	def is_castable_to(self, type):
		return base.is_castable_to(self, type) or isinstance(type, py_simple_type)

	def py_cast_to(self, type):
		result = base.py_cast_to(self, type)
		if (result == NotImplemented):
			result = type.py_cast_from(self)
		return result

class void_type(base):

	'''The void type'''

	def py_cast_to(self, type):
		global void_type
		if isinstance(type, void_type):
			return []
		else:
			raise NotImplementedError()

	def __str__(self):
		return 'void'

	def x86_asm_discard(self, env):
		return []

class x86_dword_type(base):

	'''[x86] An abstract 32-bit type.'''

	def x86_size(self):
		return 4

	def x86_asm_write(self, var, expression, env):
		result = []
		result += expression.to_x86_asm(env);
		result += 'mov [%s], eax' % var.uid,
		return result

	def x86_asm_read(self, var, env):
		return ['mov eax, [%s]' % var.uid]

	def x86_asm_push(self, env):
		return ['push eax']

	def x86_asm_discard(self, env):
		return []

class numeric_type(base):

	'''An abstract numeric type.'''

	def is_numeric(self):
		return True

	def is_ineq_comparable(self):
		return True

class int_type(numeric_type, py_simple_type, x86_dword_type):

	'''The integer (int) type.'''

	def py_cast_from(self, type):
		return \
		[
			(bp.LOAD_GLOBAL, '*int'),
			(bp.ROT_TWO, None),
			(bp.CALL_FUNCTION, 1)
		]

	def x86_asm_const(self, value, env):
		return ['mov eax, %d' % value]

	def x86_asm_cast_to(self, type, env):
		if isinstance(type, (void_type, int_type)):
			return []
		elif isinstance(type, double_type):
			return \
			[
				'push eax',
				'fild DWORD [esp]',
				x86.AddESP(4)
			]
		elif isinstance(type, boolean_type):
			return \
			[
				'or eax, eax',
				'setnz al',
				'and eax, 1'
			]
		else:
			raise NotImplemenedError()

	def __str__(self):
		return 'int'

class double_type(numeric_type, py_simple_type):

	'''The floating-point (double) type.'''

	def py_cast_from(self, type):
		return \
		[
			(bp.LOAD_GLOBAL, '*float'),
			(bp.ROT_TWO, None),
			(bp.CALL_FUNCTION, 1)
		]

	x86_consts = \
	{
		1.0000000000000000000000000000000000: '1',
		3.1415926535897932384626433832795029: 'pi',
		1.4426950408889634073599246810018921: 'l2e',
		3.3219280948873623478703194294893902: 'l2t',
		0.3010299956639811952137388947244930: 'lg2',
        0.6931471805599453094172321214581765: 'ln2'
		# *** do NOT include 0.0 here ***
	}

	def x86_asm_const(self, value, env):
		if value in double_type.x86_consts:
			return ['fld%s' % double_type.x86_consts[value]]
		const = x86.Const(pack('<d', value))
		return \
		[
			const,
			'fld QWORD [%s]' % const
		]

	def x86_asm_read(self, var, env):
		return ['fld QWORD [%s]' % var.uid]

	def x86_asm_write(self, var, expression, env):
		result = []
		result += expression.to_x86_asm(env);
		result += 'fstp QWORD [%s]' % var.uid,
		return result

	def x86_asm_push(self, env):
		return \
		[
			x86.SubESP(8),
			'fstp QWORD [esp]'
		]

	def x86_asm_discard(self, env):
		return ['fstp st0']

	def x86_size(self):
		return 8

	def x86_asm_cast_to(self, type, env):
		if isinstance(type, void_type):
			return ['fstp st0']
		elif isinstance(type, double_type):
			return []
		elif isinstance(type, int_type):
			return \
			[
				x86.SubESP(12),
				'fnstcw [esp + 4]',
				'mov eax, [esp + 4]',
				'and eax, 0xf3ff',
				'or eax, 0x0400',
				'mov [esp + 8], eax',
				'fldcw [esp + 8]',
				'fistp DWORD [esp]',
				'fldcw [esp + 4]',
				'pop eax',
				x86.AddESP(8)
			]
		elif isinstance(type, boolean_type):
			return \
			[
				'fldz',
				'fucomi st0, st1',
				'setne al',
				'and eax, 1',
				'fstp st0',
				'fstp st0'
			]
		else:
			raise NotImplemenedError()

	def __str__(self):
		return 'double'

class string_type(x86_dword_type):

	'''The string type.'''

	def x86_asm_const(self, value, env):
		const = x86.Const(value, '\0')
		return \
		[
			const,
			'mov eax, %s' % const
		]

	def x86_asm_cast_to(self, type, env):
		return []

	def __str__(self):
		return 'string'

class boolean_type(py_simple_type, x86_dword_type):

	'''The boolean type.'''

	def py_cast_from(self, type):
		return \
		[
			(bp.LOAD_GLOBAL, '*bool'),
			(bp.ROT_TWO, None),
			(bp.CALL_FUNCTION, 1)
		]

	def x86_asm_const(self, value, env):
		return ['xor eax, eax'] + ['inc eax'] * value

	def x86_asm_cast_to(self, type, env):
		if isinstance(type, (void_type, int_type, boolean_type)):
			return []
		elif isinstance(type, double_type):
			return int_t.x86_asm_cast_to(type, env)
		else:
			raise NotImplemenedError()

	def __str__(self):
		return 'boolean'

void_t = void_type()
int_t = int_type()
double_t = double_type()
boolean_t = boolean_type()
void_t = void_type()
string_t = string_type()

class function_type(base):

	'''A function type.'''

	def __init__(self, return_type, argument_types):
		self.return_type = return_type
		self.arg_type_list = argument_types

	def __ne__(self, rival):
		return not self.__eq__(rival)

	def __eq__(self, rival):
		return \
			isinstance(rival, function_type) and \
			rival.return_type == self.return_type and \
			rival.arg_type_list == self.arg_type_list

	def __str__(self):
		if len(self.arg_type_list) == 0:
			arg_type_list_repr = 'unit'
		else:
			arg_type_list_repr = ' x '.join([str(type) for type in self.arg_type_list])
		return '%s -> %s' % (arg_type_list_repr, self.return_type)

main_t = function_type(int_t, [])

_globals = list(globals().itervalues())
for _item in _globals:
	try:
		if base not in _item.__mro__:
			continue
	except AttributeError:
		continue
	for _method, _doc in base._doc.iteritems():
		try:
			_method = getattr(_item, _method)
		except AttributeError:
			continue
		if _method.__doc__ is None:
			_method.im_func.__doc__ = _doc
del _globals, _method, _item, _doc

# vim:ts=4 sw=4
