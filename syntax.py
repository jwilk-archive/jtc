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

'''Nodes of Javalette syntax trees.'''

from struct import pack

_type = type
import type

import bp
import x86

__all__ =  ['argv', 'base', 'block', 'block_statement', 'declaration', 'error', 'evaluation', 'function', 'if_then_else', 'program', 'return_statement', 'statement', 'variable', 'while_loop']

class base(object):

	'''An abstract node.'''

	@property
	def x(self):
		'''Column number of appearance.'''
		return self.position[1]

	@property
	def y(self):
		'''Line number of appearance.'''
		return self.position[0]

	_doc = \
	{
		'validate': 'Look for type mismatches.\nCheck for proper variable usage.',
		'to_py': '[py] Generate code.',
		'to_x86_asm': '[x86] Generate code.',
		'bind_to_function': 'Bind the statement to the function in which it appears.',
		'get_blocks': 'Return a sequence of sub-blocks.',
		'get_var_refs': 'Return a sequence of referenced variables.',
		'check_var_usage': "Check for proper variable usage.\n'lsv' - set of declared variables\n'rsv' - set of used variables.\nBoth sets are updated."
	}

class block(base):

	'''An abstract block.'''

	def __init__(self, contents):
		'''Initialize the block with 'contents' - a list or a single item.'''
		if not isinstance(contents, list):
			contents = [contents]
		self.contents = contents

	@staticmethod
	def indent(s):
		return '  ' + str(s).replace('\n', '\n  ')

	def validate(self):
		ok = True
		for line in self.contents:
			ok &= line.validate()
		return ok

	def __str__(self):
		if len(self.contents) == 0:
			return block.indent('skip')
		else:
			return '\n'.join(block.indent(item) for item in self.contents)

class statement(base):

	'''A statement.'''

	def get_blocks(self):
		return ()

	def get_var_refs(self):
		return ()

	def check_var_usage(self, lsv, rsv):
		raise NotImplementedError()

	def validate(self):
		raise NotImplementedError()

	def bind_to_function(self, function):
		pass

	def returns(self):
		'''Check if the function returns (in this statement).'''
		return False

class block_statement(block, statement):

	'''A block statement.'''

	def returns(self):
		'''Check if the function returns (in this block).'''
		for line in self.contents:
			if line.returns():
				return True
		return False

	def check_var_usage(self, lsv, rsv):
		ok = True
		for line in self.contents:
			ok &= line.check_var_usage(lsv, rsv)
		return ok

	def to_py(self):
		result = []
		for line in self.contents:
			result += line.to_py()
		return result

	def to_x86_asm(self, env):
		env2 = env.clone()
		result = []
		for line in self.contents:
			result += line.to_x86_asm(env2)
		result += x86.AddESP(env2.vsp - env.vsp),
		return result

class program(block):

	'''A program.'''

	def __str__(self):
		return '\n\n'.join(str(item) for item in self.contents)

	def to_py(self):
		from builtins import py_stub_pre, py_stub_post
		listing = []
		listing += py_stub_pre
		for item in self.contents:
			listing += item.to_py(self.filename)
		listing += py_stub_post
		return listing

	def to_pyc(self):
		'''[py] Generate bytecode for the program.'''
		from builtins import this_module_file_name as builtins_module_file_name
		listing = self.to_py()
		return bp.Code(
			code = listing,
			freevars = [],
			args = [],
			varargs = False,
			varkwargs = False,
			newlocals = False,
			name = '__stub__',
			filename = builtins_module_file_name,
			firstlineno = 0,
			docstring = None)

	def compile_pyc(self, output_file):
		'''[py] Compile the program into a Python bytecode file.'''
		import imp
		import marshal
		output_file.write(imp.get_magic())
		output_file.write('\x00\x00\x00\x00')
		pyc = self.to_pyc()
		pyo = pyc.to_code()
		marshal.dump(pyo, output_file)

	def to_x86_asm(self):
		from builtins import x86_stub
		listing = list(x86_stub)
		for item in self.contents:
			listing += item.to_x86_asm()
		return listing

	def compile_x86(self, output_file):
		'''[x86] Compile the program into an ELF executable.'''
		x86_asm = self.to_x86_asm()
		x86.build(x86_asm, output_file)

	# Just to change the docstring
	def validate(self):
		return block.validate(self)

	validate.__doc__ = base._doc['validate'] + '\nCheck if every function returns.'

class error(base):

	'''An error indicator.'''

	def __init__(self):
		pass

	def __str__(self):
		return '!!!'

class variable(base):

	'''A variable declaration (possibly, with initialization).'''

	def __init__(self, type, name, value, position):
		object.__init__(self)
		self.name = name
		self.type = type
		self.value = value
		self.position = position
		self.uid = '&%x' % id(self)

	def get_var_refs(self):
		from expression import expression
		if isinstance(self.value, expression):
			return self.value.get_var_refs()
		else:
			return ()

	def check_var_usage(self, lsv, rsv):
		ok = True
		if self.value is not None:
			ok &= self.value.check_var_usage(lsv, rsv)
			lsv.add(self)
		return ok

	def validate(self):
		if self.value is None:
			return True
		ok = self.value.validate()
		if self.value.type is None or self.value.type == self.type:
			return ok
		else:
			TypeMismatch(self.position,
				'Incompatible types in initialization: <%s> provided but <%s> expected' %
				(self.value.type, self.type)).warn()
			return False

	def py_write(self, value = None, pop = True):
		'''[py] Generate code for storing the value to the variable.'''
		if value is None:
			value = self.value
		if value is None:
			return []
		else:
			result = []
			result += value.to_py()
			if not pop:
				result += (bp.DUP_TOP, None),
			result += (bp.STORE_FAST, self.uid),
			return result

	def py_read(self):
		'''[py] Generate code for reading the variables.'''
		return [(bp.LOAD_FAST, self.uid)]

	def x86_asm_write(self, expression, env):
		'''[x86] Generate code for storing value of the expression to the variable.'''
		if expression is None:
			return []
		else:
			return self.type.x86_asm_write(self, expression, env)

	def x86_asm_read(self, env):
		'''[x86] Generate code for loading value of the variable.'''
		return self.type.x86_asm_read(self, env)

	def __str__(self):
		return 'var $%s : %s = %s' % (self.name, self.type, self.value)

class function(variable):

	'''A function declaration.'''

	def __init__(self, name, return_type, arguments, code, position):
		self.type = type.function_type(return_type, [arg.type for arg in arguments])
		code = block_statement([argv(arguments), code])
		variable.__init__(self, self.type, name, code, position)

	def validate(self):
		ok = self.value.validate()
		if not self.value.returns():
			MissingReturn(self.position, "Missing return statement for function '%s'" % self.name).warn()
			return False
		lsv = set()
		rsv = set()
		self.value.check_var_usage(lsv, rsv)
		return ok

	validate.__doc__ = base._doc['validate'] + '\nCheck if the function returns.'

	def to_py(self, filename):
		body_code = self.body_to_pyc(filename)
		return \
		[
			(bp.LOAD_CONST, body_code),
			(bp.MAKE_FUNCTION, 0),
			(bp.STORE_GLOBAL, self.name)
		]

	def py_read(self):
		'''[py] Generate code for reading the function address.'''
		return [(bp.LOAD_GLOBAL, self.name)]

	def body_to_pyc(self, filename):
		'''[py] Generate bytecode for function body.'''
		code = bp.Code(
			code = self.value.to_py(),
			freevars = [],
			args = ['_%d' % n for n in xrange(len(self.type.arg_type_list))],
			varargs = False,
			varkwargs = False,
			newlocals = True,
			name = self.name,
			filename = filename,
			firstlineno = self.y,
			docstring = None)
		return code

	@property
	def x86_name(self):
		'''[x86] Mangled function name.'''
		return '_f_%s' % self.name

	def to_x86_asm(self):
		result = \
		[
			x86.SyncESP(),
			'%s:' % self.x86_name,
		]
		result += self.value.to_x86_asm(x86.Env())
		result += x86.SyncESP(),
		return result

	def __str__(self):
		return 'function %s : %s =\n%s' % (self.name, self.type, self.value)

class evaluation(statement):

	'''An evaluation statement.'''

	def __init__(self, expression):
		statement.__init__(self)
		self.expression = expression
		self.position = expression.position

	def validate(self):
		ok = self.expression.validate()
		xtype = self.expression.type
		if xtype is None or self.expression.is_evaluatable():
			return ok
		TypeMismatch(self.position,
			'Incompatible types in evaluation: <%s> provided but <void> expected' % xtype).warn()
		return False

	def get_var_refs(self):
		return self.expression.get_var_refs()

	def check_var_usage(self, lsv, rsv):
		return self.expression.check_var_usage(lsv, rsv)

	def to_py(self):
		result = self.expression.to_py() + [(bp.POP_TOP, None)]
		return result

	def to_x86_asm(self, env):
		return \
			self.expression.to_x86_asm(env) + \
			self.expression.x86_asm_discard(env)

	def __str__(self):
		return str(self.expression)

class declaration(statement):

	'''A group of variable declarations.'''

	def __init__(self, variables, position):
		statement.__init__(self)
		self.variables = variables
		self.position = position

	def validate(self):
		ok = True
		for variable in self.variables:
			ok &= variable.validate()
		return ok

	def get_var_refs(self):
		result = []
		for variable in self.variables:
			result += variable.get_var_refs()
		return result

	def check_var_usage(self, lsv, rsv):
		ok = True
		for variable in self.variables:
			ok &= variable.check_var_usage(lsv, rsv)
		return ok

	def to_py(self):
		result = [(bp.SetLineno, self.y)]
		for var in self.variables:
			result += var.py_write()
		return result

	def to_x86_asm(self, env):
		salloc = 0
		for var in self.variables:
			size = var.type.x86_size()
			env.vsp += size
			salloc += size
			var.uid = '##(-%d)' % env.vsp
		result = [x86.SubESP(salloc)]
		for var in self.variables:
			result += var.x86_asm_write(var.value, env)
		return result

	def __str__(self):
		return 'declare: ' + ', '.join(str(var) for var in self.variables)

class argv(declaration):

	'''An artificial declaration of function arguments.'''

	def __init__(self, variables):
		declaration.__init__(self, variables, None)

	def validate(self):
		return True

	def get_var_refs(self):
		return ()

	def check_var_usage(self, lsv, rsv):
		lsv |= set(self.variables)
		return True

	def to_py(self):
		for no, var in enumerate(self.variables):
			var.uid = '_%d' % no
		return []

	def to_x86_asm(self, env):
		for i, var in enumerate(self.variables):
			var.uid = '##(%d)' % (4 * (i + 1))
		return []

	def __str__(self):
		return 'argv: ' + ', '.join(str(var) for var in self.variables)

class if_then_else(statement):

	'''A condition statement.'''

	def __init__(self, expression, then_s, else_s, position):
		statement.__init__(self)
		self.expression = expression
		if not isinstance(then_s, block):
			then_s = block_statement(then_s)
		self.then_s = then_s
		if not isinstance(else_s, block):
			else_s = block_statement(else_s)
		self.else_s = else_s
		self.position = position

	def validate(self):
		ok = self.expression.validate()
		if self.expression.type is not None and self.expression.type != type.boolean_t:
			TypeMismatch(self.expression.position,
				'Incompatible types in conditional statement: <%s> provided but <boolean> expected' % self.expression.type).warn()
			ok = False
		ok &= self.then_s.validate()
		ok &= self.else_s.validate()
		return ok

	def get_blocks(self):
		return (self.then_s, self.else_s)

	def get_var_refs(self):
		return self.expression.get_var_refs()

	def check_var_usage(self, lsv, rsv):
		ok = self.expression.check_var_usage(lsv, rsv)
		lsv_if = set(lsv)
		lsv_then = set(lsv)
		ok &= self.then_s.check_var_usage(lsv_if, rsv)
		ok &= self.then_s.check_var_usage(lsv_then, rsv)
		lsv |= (lsv_if & lsv_then)
		return ok

	def returns(self):
		'''Check if the function returns (in every branch of this statement).'''
		return self.then_s.returns() and self.else_s.returns()

	def to_py(self):
		label_else = bp.Label()
		label_endif = bp.Label()
		result = [(bp.SetLineno, self.y)]
		result += self.expression.to_py()
		result += bp.jump_if_false(label_else)
		result += self.then_s.to_py()
		result += [
			(bp.JUMP_FORWARD, label_endif),
			(label_else, None),
			(bp.POP_TOP, None)
		]
		result += self.else_s.to_py()
		result += (label_endif, None),
		return result

	def to_x86_asm(self, env):
		label_else = x86.Label()
		label_endif = x86.Label()
		result = []
		result += self.expression.to_x86_asm(env)
		result += \
		[
			'or eax, eax',
			'jz %s' % label_else
		]
		result += self.expression.x86_asm_discard(env)
		result += self.then_s.to_x86_asm(env)
		result += \
		[
			'jmp %s' % label_endif,
			label_else
		]
		result += self.else_s.to_x86_asm(env)
		result += label_endif,
		return result

	def __str__(self):
		return 'if %s:\n%s\nelse:\n%s\nendif' % (self.expression, self.then_s, self.else_s)

class while_loop(statement):

	'''A loop.'''

	def __init__(self, expression, finally_s, then_s, position):
		statement.__init__(self)
		self.expression = expression
		if not isinstance(then_s, block):
			then_s = block_statement(then_s)
		if not isinstance(finally_s, block):
			finally_s = block_statement(finally_s)
		self.finally_s = finally_s
		self.then_s = then_s
		self.position = position

	def validate(self):
		ok = self.expression.validate()
		if self.expression.type is not None and self.expression.type != type.boolean_t:
			TypeMismatch(self.expression.position,
				'Incompatible types in loop condition: <%s> provided but <boolean> expected' % self.expression.type).warn()
			ok = False
		ok &= self.finally_s.validate()
		ok &= self.then_s.validate()
		return ok

	def get_blocks(self):
		return self.then_s, self.finally_s

	def get_var_refs(self):
		return self.expression.get_var_refs()

	def check_var_usage(self, lsv, rsv):
		ok = self.expression.check_var_usage(lsv, rsv)
		ok &= self.then_s.check_var_usage(set(lsv), rsv)
		ok &= self.finally_s.check_var_usage(set(lsv), rsv)
		return ok

	def to_py(self):
		loop_label = bp.Label()
		finally_label = bp.Label()
		end_label = bp.Label()
		result = \
		[
			(bp.SetLineno, self.y),
			(bp.JUMP_FORWARD, loop_label),
			(finally_label, None)
		]
		result += self.finally_s.to_py()
		result += (loop_label, None),
		result += self.expression.to_py()
		result += bp.jump_if_false(end_label)
		result += self.then_s.to_py()
		result += \
		[
			(bp.JUMP_ABSOLUTE, finally_label),
			(end_label, None),
			(bp.POP_TOP, None)
		]
		return result

	def to_x86_asm(self, env):
		loop_label = x86.Label()
		condition_label = x86.Label()
		result = \
		[
			'jmp %s' % condition_label,
		]
		result += loop_label,
		result += self.then_s.to_x86_asm(env)
		result += self.finally_s.to_x86_asm(env)
		result += condition_label,
		result += self.expression.to_x86_asm(env)
		result += \
		[
			'or eax, eax',
			'jnz %s' % loop_label,
		]
		return result

	def __str__(self):
		return 'while %s:\n%s\nfinally:\n%s\ndone' % (self.expression, self.then_s, self.finally_s)

class return_statement(statement):

	def __init__(self, expression, position):
		statement.__init__(self)
		self.expression = expression
		self.position = position
		self.function = None

	def bind_to_function(self, function):
		self.function = function

	def validate(self):
		if self.function is None:
			raise NotImplementedError()
		return_type = self.function.type.return_type
		if self.expression is None:
			if return_type != type.void_t:
				TypeMismatch(self.position, 'Incompatible types in return: no expression provided but <%s> expected' % return_type).warn()
				return False
			else:
				return True
		ok = self.expression.validate()
		if return_type == type.void_t:
			TypeMismatch(self.position, 'Incompatible types in return: an expression provided but no expression expected').warn()
			return False
		if return_type != self.expression.type:
			TypeMismatch(
				self.position,
				'Incompatible types in return: <%s> provided but <%s> expected' %
				(self.expression.type, return_type)).warn()
			return False
		return ok

	def get_var_refs(self):
		if self.expression is None:
			return ()
		else:
			return self.expression.get_var_refs()

	def check_var_usage(self, lsv, rsv):
		if self.expression is None:
			return True
		else:
			return self.expression.check_var_usage(lsv, rsv)

	def returns(self):
		'''Check if the function returns (in this statement). And yes, it does.'''
		return True

	def to_py(self):
		result = [(bp.SetLineno, self.y)]
		if self.expression is None:
			result += (bp.LOAD_CONST, None),
		else:
			result += self.expression.to_py()
		result += (bp.RETURN_VALUE, None),
		return result

	def to_x86_asm(self, env):
		result = []
		if self.expression is not None:
			result += self.expression.to_x86_asm(env);
		result += x86.Return(),
		return result

	def __str__(self):
		return 'return %s' % self.expression

from error import JtError

class MissingReturn(JtError):
	'''A function (sometimes) does not return.'''
	pass

class TypeMismatch(JtError):
	'''Some types does not match.'''
	pass

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

# vim:ts=4 sts=4 sw=4
