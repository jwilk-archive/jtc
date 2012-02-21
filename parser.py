# Copyright (c) 2007 Jakub Wilk <jwilk@jwilk.net>

'''Javalette parser.'''

import yacc
import syntax
import type
import expression

__all__ = ['Parser']

class Parser(object):

	def __init__(self, lexer):
		self.lexer = lexer
		self.tokens = lexer.tokens
		self.precedence = [('right', 'ELSE')]
		self.start = 'program'
		self.yacc = yacc.yacc(module = self, debug = 0)

	def parse(self):
		'''Build the syntax tree.'''
		return self.yacc.parse(lexer = self.lexer)

	def p_program(self, p):
		'program : fun_def_list'
		p[0] = syntax.program(p[1])

	def p_fun_def_list_empty(self, p):
		'fun_def_list :'
		p[0] = []

	def p_fun_def_list_nonempty(self, p):
		'fun_def_list : fun_def_list fun_def'
		p[0] = p[1]
		p[0] += p[2],

	def p_fun_def(self, p):
		'fun_def : type IDENT LPAREN arg_list RPAREN complex_i'
		p[0] = syntax.function(p[2], p[1], p[4], p[6], p.lexpos(2))

	def p_arg_list(self, p):
		'''
			arg_list : arg_list_empty
			         | arg_list_nonempty
		'''
		p[0] = p[1]

	def p_arg_list_empty(self, p):
		'arg_list_empty : '
		p[0] = []

	def p_arg(self, p):
		'arg : type IDENT'
		p[0] = syntax.variable(p[1], p[2], None, p.lexpos(2))

	def p_arg_list_single(self, p):
		'arg_list_nonempty : arg'
		p[0] = [p[1]]

	def p_arg_list_nonempty(self, p):
		'arg_list_nonempty : arg_list_nonempty COMMA arg'
		p[0] = p[1]
		p[0] += p[3],

	def p_instr(self, p):
		'''
			instr : complex_i 
			      | decl_i 
			      | cond_i 
			      | loop_i 
			      | return_i 
			      | expr_i
		'''
		p[0] = p[1]

	def p_complex_i(self, p):
		'complex_i : LBRACE i_list RBRACE'
		p[0] = syntax.block_statement(p[2])

	def p_i_list_empty(self, p):
		'i_list :'
		p[0] = []

	def p_i_list_nonempty(self, p):
		'i_list : i_list instr'
		p[0] = p[1]
		p[0] += p[2],

	def p_decl_i(self, p):
		'decl_i : type decl_list SEMICOLON'
		for var in p[2]:
			var.type = p[1]
		p[0] = syntax.declaration(p[2], p[2][0].position)

	def p_decl_list_single(self, p):
		'decl_list : decl'
		p[0] = [p[1]]

	def p_decl_list_multiple(self, p):
		'decl_list : decl_list COMMA decl'
		p[0] = p[1]
		p[0] += p[3],

	def p_decl(self, p):
		'decl : IDENT'
		p[0] = syntax.variable(None, p[1], None, p.lexpos(1))

	def p_decl_value(self, p):
		'decl : IDENT ASSIGN expr' 
		p[0] = syntax.variable(None, p[1], p[3], p.lexpos(1))

	def p_inc(self, p):
		'assign_e : IDENT INC'
		q = expression.reference(p[1], p.lexpos(1))
		p[0] = expression.assignment(q, expression.binary_operator('+', q, expression.const(1, type.int_t, p.lexpos(2)), p.lexpos(2)), p.lexpos(2))

	def p_dec(self, p):
		'assign_e : IDENT DEC'
		q = expression.reference(p[1], p.lexpos(1))
		p[0] = expression.assignment(q, expression.binary_operator('-', q, expression.const(1, type.int_t, p.lexpos(2)), p.lexpos(2)), p.lexpos(2))

	def p_if(self, p):
		'cond_i : IF LPAREN expr RPAREN instr else'
		p[0] = syntax.if_then_else(p[3], p[5], p[6], p.lexpos(1))

	def p_else(self, p):
		'else : ELSE instr'
		p[0] = p[2]

	def p_no_else(self, p):
		'else :'
		p[0] = []

	def p_while(self, p):
		'loop_i : WHILE LPAREN expr RPAREN instr'
		p[0] = syntax.while_loop(p[3], [], p[5], p.lexpos(1))

	def p_for(self, p):
		'loop_i : FOR LPAREN assign_e SEMICOLON expr SEMICOLON assign_e RPAREN instr'
		pre = syntax.evaluation(p[3])
		mid = p[5]
		post = syntax.evaluation(p[7])
		body = p[9]
		p[0] = syntax.block_statement([pre, syntax.while_loop(mid, post, body, p.lexpos(1))])

	def p_return_void(self, p):
		'return_i : RETURN SEMICOLON'
		p[0] = syntax.return_statement(None, p.lexpos(1))

	def p_return_value(self, p):
		'return_i : RETURN expr SEMICOLON'
		p[0] = syntax.return_statement(p[2], p.lexpos(1))

	def p_expr_i(self, p):
		'expr_i : expr SEMICOLON'
		p[0] = syntax.evaluation(p[1])

	def p_assign_e(self, p):
		'assign_e : IDENT ASSIGN expr'
		p[0] = expression.assignment(expression.reference(p[1], p.lexpos(1)), p[3], p.lexpos(2))

	def p_e_pass(self, p):
		'''
			expr : assign_e
			expr : or_e
			or_e : and_e
			and_e  : compare_e
			compare_e : rel_e
			rel_e : add_e
			add_e : mul_e
			mul_e : sa_e
			sa_e : prefix_e
			prefix_e : simple_e
		'''
		p[0] = p[1]

	def p_binary_e(self, p):
		'''
			or_e : or_e LOR and_e
			and_e : and_e LAND compare_e
			compare_e : compare_e EQUAL rel_e 
			          | compare_e NOTEQ rel_e
			rel_e : rel_e LT add_e 
			      | rel_e GT add_e 
			      | rel_e LE add_e 
			      | rel_e GE add_e
	    	add_e : add_e PLUS mul_e
	    	      | add_e MINUS mul_e
	    	mul_e : mul_e TIMES sa_e
	    	      | mul_e DIV sa_e
	    	      | mul_e MOD sa_e

		'''
		p[0] = expression.binary_operator(p[2], p[1], p[3], p.lexpos(2))

	def p_sa_e(self, p):
		'''
			sa_e : NOT sa_e 
			     | PLUS sa_e 
			     | MINUS sa_e
		'''
		p[0] = expression.unary_operator(p[1], p[2], p.lexpos(1))

	def p_cast_e(self, p):
		'sa_e : LPAREN type RPAREN sa_e'
		p[0] = expression.cast(operand = p[4], type = p[2], position = p.lexpos(1))

	def p_call_e(self, p):
		'prefix_e : IDENT LPAREN expr_list RPAREN'
		p[0] = expression.call(expression.reference(p[1], p.lexpos(1)), p[3], p.lexpos(1))

	def p_call_e_noargs(self, p):
		'prefix_e : IDENT LPAREN RPAREN'
		p[0] = expression.call(expression.reference(p[1], p.lexpos(1)), [], p.lexpos(1))

	def p_expr_list_single(self, p):
		'expr_list : expr'
		p[0] = [p[1]]

	def p_expr_list_multiple(self, p):
		'expr_list : expr_list COMMA expr'
		p[0] = p[1]
		p[0] += p[3],

	def p_ident_e(sellf, p):
		'simple_e : IDENT'
		p[0] = expression.reference(p[1], p.lexpos(1))

	def p_const_e(self, p):
		'simple_e : const'
		p[0] = p[1]

	def p_paren_e(self, p):
		'simple_e : LPAREN expr RPAREN'
		p[0] = p[2]

	def p_const_int(self, p):
		'const : INT'
		p[0] = expression.const(p[1], type.int_t, p.lexpos(1))
	
	def p_const_double(self, p):
		'const : DOUBLE'
		p[0] = expression.const(p[1], type.double_t, p.lexpos(1))
	
	def p_const_boolean(self, p):
		'const : BOOLEAN'
		p[0] = expression.const(p[1], type.boolean_t, p.lexpos(1))
	
	def p_const_string(self, p):
		'const : STRING'
		p[0] = expression.const(p[1], type.string_t, p.lexpos(1))

	def p_type(self, p):
		'type : TYPE'
		p[0] = type.simple_type(p[1])

	def p_error(self, token):
		from sys import stderr
		if token:
			raise ParseError(token.lexpos, 'Syntax error near ' + `token.value`)
		else:
			raise ParseError(None, 'Syntax error at the end of file')

from error import JtError

class ParseError(JtError):
	pass

# vim:ts=4 sw=4
