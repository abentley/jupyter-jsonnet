# Copyright Aaron Bentley 2022
# This software is licenced under the MIT license
# <LICENSE or http://opensource.org/licenses/MIT>

from dataclasses import dataclass
import json
from importlib import metadata
import re

from ipykernel.kernelbase import Kernel
from _jsonnet import evaluate_snippet


@dataclass
class JupyterError:

    exception: None
    kernel: None

    @property
    def error_content(self):
        return {
            'ename': 'RuntimeError',
            'evalue': str(self.exception),
            'traceback': str(self.exception).splitlines()
        }

    def result(self):
        result = {
            'execution_count': self.kernel.execution_count,
            'status': 'error',
        }
        result.update(self.error_content)
        return result

    def send_response(self):
        self.kernel.send_response(self.kernel.iopub_socket, 'error',
                                  self.error_content)


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

    @staticmethod
    def parse_error(error):
        return re.match(
            r'^(?P<type>[^:]+)'
            r'(: )(?:(?P<msg1>.*)(\n\t))?'
            r'(?:([^:]+)(:))?(?P<start_row>\d+)(q)?(q)?(:)(?P<start_col>\d+)(-)?(\d+)?'
            r'(: |\t?)(?:(?P<msg2>.+))?(\n)$',
            error,
        )

    @classmethod
    def rewrite_error(cls, error, row_offset, column_offset):
        sections = cls.parse_error(error)
        if sections == None:
            return error
        groups = list(sections.groups())
        groups[10] = str(int(groups[10]) - column_offset)
        return ''.join(g for g in groups if g is not None)

    def inner_execute(self, code):
        new_code = self.history + code
        statements, result = self.split_code(new_code)
        if result is None:
            new_code += 'null'
        return evaluate_snippet('', new_code), statements, result

    def do_execute(self, code, silent, store_history, user_expressions,
                   allow_stdin):
        try:
            output, statements, result = self.inner_execute(code)
            if result is None:
                if json.loads(output) is None:
                    output = ''
                else:
                    raise ValueError('Bad input')
        except RuntimeError as e:
            jp_err = JupyterError(e, self)
            jp_err.send_response()
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
        except RuntimeError as e:
            groups = self.parse_error(str(e))
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
