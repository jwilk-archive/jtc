# encoding=UTF-8

# Copyright © 2012-2016 Jakub Wilk <jwilk@jwilk.net>
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

from nose.tools import assert_equal, assert_not_equal

try:
    from nose.tools import assert_multi_line_equal
except ImportError:
    assert_multi_line_equal = assert_equal

import os
import glob
import stat
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
        stderr = stderr.decode()
        assert_multi_line_equal(stderr, '')
        assert_equal(rc, 0)
        with open(input_filename, 'rb') as input_file:
            child = ipc.Popen(self.runner + [self.executable],
                stdin=input_file,
                stdout=ipc.PIPE,
                stderr=ipc.PIPE
            )
            stdout = child.stdout.read()
            stderr = child.stderr.read()
            rc = child.wait()
        stderr = stderr.decode()
        assert_multi_line_equal(stderr, '')
        assert_equal(rc, 0)
        with open(output_filename, 'rb') as output_file:
            expected_stdout = output_file.read()
        assert_equal(expected_stdout, stdout)

    def _test_bad(self, filename):
        base_name, _ = os.path.splitext(filename)
        error_filename = base_name + '.error'
        rc, stderr = self._compile(filename, output_filename=os.devnull)
        stderr = stderr.decode()
        assert_not_equal(rc, 0)
        with open(error_filename, 'r') as error_file:
            expected_stderr = error_file.read()
        assert_multi_line_equal(expected_stderr, stderr)

    def setup(self):
        fd, self.executable = tempfile.mkstemp(prefix='jtc-testsuite.')
        os.close(fd)
        os.chmod(self.executable, stat.S_IRWXU)

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

# vim:ts=4 sts=4 sw=4 et
