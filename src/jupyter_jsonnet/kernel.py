# Copyright Aaron Bentley 2022
# This software is licenced under the MIT license
# <LICENSE or http://opensource.org/licenses/MIT>

from contextlib import contextmanager
from dataclasses import dataclass
import json
from importlib import metadata
import re

from ipykernel.kernelbase import Kernel
from _jsonnet import evaluate_snippet


class JupyterException(RuntimeError):

    def __init__(self, real):
        self._real = real

    @classmethod
    def from_str(cls, str):
        return cls(RuntimeError(str))

    @property
    def args(self):
        return self._real.args

    @classmethod
    @contextmanager
    def reraise(cls):
        try:
            yield
        except RuntimeError as e:
            raise cls(e) from e

    def parse(self):
        return re.match(
            r'^(?P<type>[^:]+)'
            r'(: )(?:(?P<msg1>(?:.|\n)*)(\n\t))?'
            r'(?:(?P<filename>[^:]+)(:))?'
            r'(\(?)(?P<start_row>\d+)'
            r'(:)(?P<start_col>\d+)'
            r'(\)?-)?(?:(\()(?P<end_row>\d+)(:))?(?P<end_column>\d+)?(\)?)'
            r'(: |\t?)(?:(?P<msg2>.+))?(\n)$',
            str(self),
        )

    def rewrite(self, row_offset, column_offset):
        sections = self.parse()
        if sections is None:
            return str(self)
        groups = list(sections.groups())

        def do_offset(idx, offset):
            if groups[idx] is not None:
                groups[idx] = str(int(groups[idx]) + offset)
                return True
            return False
        do_offset(7, row_offset)
        do_offset(9, column_offset)
        if not do_offset(12, row_offset):
            do_offset(14, column_offset)
        return ''.join(g for g in groups if g is not None)


@dataclass
class JupyterError:

    exception: None
    execution_count: None

    @classmethod
    def with_offsets(cls, error, kernel, row, column):
        new_error = JupyterException.from_str(error.rewrite(-row, -column))
        return cls(new_error, kernel.execution_count)

    @property
    def error_content(self):
        return {
            'ename': 'RuntimeError',
            'evalue': str(self.exception),
            'traceback': str(self.exception).splitlines()
        }

    def result(self):
        result = {
            'execution_count': self.execution_count,
            'status': 'error',
        }
        result.update(self.error_content)
        return result



class JupyterKernel(Kernel):

    implementation = "jupyter-jsonnet"

    implementation_version = "0.1"

    language = "Jsonnet"

    language_version = metadata.version('jsonnet')
    language_info = {
        'name': 'Jsonnet',
        'mimetype': 'text/x-jsonnet',
        'file_extension': 'jsonnet',
    }
    banner = "Welcome to Jsonnet!"

    class ShellHandlers:

        def comm_open(stream, ident, parent):
            # ignore unknown message
            pass

        def comm_msg(stream, ident, parent):
            # ignore unknown message
            pass

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.history = ''
        self.shell_handlers.update({
            k: getattr(self.ShellHandlers, k) for k in dir(self.ShellHandlers)
        })

    @staticmethod
    def split_code(code):
        try:
            statements_end = code.rindex(';') + 1
        except ValueError:
            statements_end = 0
        statements = code[:statements_end]
        result = code[statements_end:]
        result = None if result.strip() == '' else result
        return statements, result

    def inner_execute(self, code):
        new_code = self.history + code
        statements, result = self.split_code(new_code)
        if result is None:
            new_code += 'null'
        with JupyterException.reraise():
            out = evaluate_snippet('', new_code)
        return out, statements, result

    def send_error_response(self, error):
        self.send_response(self.iopub_socket, 'error',
                           error.error_content)
    def do_execute(self, code, silent, store_history, user_expressions,
                   allow_stdin):
        try:
            output, statements, result = self.inner_execute(code)
            if result is None:
                if json.loads(output) is None:
                    output = ''
                else:
                    raise ValueError('Bad input')
        except JupyterException as e:
            row, column = self.get_current_offsets()
            jp_err = JupyterError.with_offsets(e, self, row, column)
            self.send_error_response(jp_err)
            return jp_err.result()
        else:
            if not silent:
                stream_content = {'name': 'stdout', 'text': output}
                self.send_response(self.iopub_socket, 'stream', stream_content)
            self.history = statements
            return {
                'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
            }

    def get_current_offsets(self):
        """Find current line/col offsets by forcing an error"""
        try:
            self.inner_execute("error 'foo'")
        except JupyterException as e:
            groups = e.parse()
        else:
            raise AssertionError('inner_execute failed to raise an exception.')
        if groups is None or groups.group('type') != 'RUNTIME ERROR':
            raise
        if groups.group('msg1') != 'foo':
            raise
        row_offset = int(groups.group('start_row')) - 1
        col_offset = int(groups.group('start_col')) - 1
        return row_offset, col_offset


if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=JupyterKernel)
