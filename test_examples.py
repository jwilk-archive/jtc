# encoding=UTF-8
# Copyright © 2012 Jakub Wilk <jwilk@jwilk.net>

from nose.tools import assert_equal, assert_not_equal

import os
import glob
import tempfile
import subprocess as ipc

class test_examples:

	abstract = True
	python = os.getenv('PYTHON') or 'python'

	def _compile(self, filename, output_filename=None):
		if output_filename is None:
			output_filename = self.executable
		child = ipc.Popen(
			[self.python, './jtc'] + self.jtc_args + [filename, '-o', self.executable],
			stderr=ipc.PIPE
		)
		stderr = child.stderr.read()
		rc = child.wait()
		return rc, stderr

	def _test_good(self, filename):
		base_name, _ = os.path.splitext(filename)
		input_filename = base_name + '.input'
		if not os.path.exists(input_filename):
			input_filename = os.devnull
		output_filename = base_name + '.output'
		rc, stderr = self._compile(filename)
		assert_equal(stderr, '')
		assert_equal(rc, 0)
		with open(input_filename, 'r') as input_file:
			child = ipc.Popen(self.runner + [self.executable],
				stdin=input_file,
				stdout=ipc.PIPE,
				stderr=ipc.PIPE
			)
			stdout = child.stdout.read()
			stderr = child.stderr.read()
			rc = child.wait()
		assert_equal(stderr, '')
		assert_equal(rc, 0)
		with open(output_filename, 'r') as output_file:
			expected_stdout = output_file.read()
		assert_equal(stdout, expected_stdout)

	def _test_bad(self, filename):
		base_name, _ = os.path.splitext(filename)
		error_filename = base_name + '.error'
		rc, stderr = self._compile(filename, output_filename=os.devnull)
		assert_not_equal(rc, 0)
		with open(error_filename, 'r') as error_file:
			expected_stderr = error_file.read()
		assert_equal(stderr, expected_stderr)

	def setup(self):
		fd, self.executable = tempfile.mkstemp(prefix='jtc-testsuite.')
		os.close(fd)
		os.chmod(self.executable, 0700)

	def teardown(self):
		os.unlink(self.executable)

	def test_good(self):
		if self.abstract:
			return
		for file in glob.glob('examples/good/*.jl'):
			yield self._test_good, file

	def test_bad(self):
		if self.abstract:
			return
		for file in glob.glob('examples/bad/*.jl'):
			yield self._test_bad, file

class test_x86(test_examples):

	abstract = False
	jtc_args = ['-X']
	runner = []

class test_python(test_examples):

	abstract = False
	jtc_args = ['-P']
	runner = [test_examples.python]

# vim:ts=4 sw=4
