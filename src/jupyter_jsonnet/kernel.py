# Copyright Aaron Bentley 2022
# This software is licenced under the MIT license
# <LICENSE or http://opensource.org/licenses/MIT>

import json
from importlib import metadata
import re

from ipykernel.kernelbase import Kernel
from _jsonnet import evaluate_snippet


def error_to_jupyter(error, execution_count):
    error_content = {
        'ename': 'RuntimeError',
        'evalue': error,
        'traceback': error.splitlines()
    }
    result = {
        'execution_count': execution_count,
        'status': 'error',
    }
    result.update(error_content)
    return error_content, result


class JsonnetError(RuntimeError):

    def __init__(self, real):
        self._real = real

    @classmethod
    def from_str(cls, str):
        return cls(RuntimeError(str))

    @property
    def args(self):
        return self._real.args

    def parse(self):
        """Parse the error message such that various pieces are separated

        Returns a re.Match object whose groups are contiguous and contain
        either strings or None.  Also the pattern's groupindex.
        """
        pattern = re.compile(
            r'^(?P<type>[^:]+)'
            r'(: )(?:(?P<msg1>(?:.|\n)*)(\n\t))?'
            r'(?:(?P<filename>[^:]+)(:))?'
            r'(\(?)(?P<start_row>\d+)'
            r'(:)(?P<start_col>\d+)'
            r'(\)?-)?(?:(\()(?P<end_row>\d+)(:))?(?P<end_column>\d+)?(\)?)'
            r'(: |\t?)(?:(?P<msg2>.+))?(\n)$',
        )
        return pattern.match(str(self)), pattern.groupindex

    def rewrite(self, row_offset, column_offset):
        sections, groupindex = self.parse()
        if sections is None:
            return str(self)
        groups = list(sections.groups())

        def do_offset(gname, offset):
            idx = groupindex[gname] - 1
            if groups[idx] is not None:
                groups[idx] = str(int(groups[idx]) + offset)
                return True
            return False
        do_offset('start_row', row_offset)
        do_offset('start_col', column_offset)
        if not do_offset('end_row', row_offset):
            do_offset('end_column', column_offset)
        return ''.join(g for g in groups if g is not None)

    def with_offsets(self, row, column):
        """Return a version of this error with the row_colmn text adjusted."""
        return JsonnetError.from_str(self.rewrite(row, column))


class ExecutorInputError(ValueError):
    """Raised when the executor finds an input error."""


class JsonnetExecutor:
    """An executor for Jsonnet that preserves past statements as history.

    This is concerned with Jsonnet and has no knowledge of Jupyter.
    """

    def __init__(self, stdout_callback):
        self.stdout_callback = stdout_callback
        self.history = ''
        self.import_paths = []

    @staticmethod
    def split_code(code):
        """Split top-level statements from top-level expression."""
        try:
            statements_end = code.rindex(';') + 1
        except ValueError:
            statements_end = 0
        statements = code[:statements_end]
        result = code[statements_end:]
        result = None if result.strip() == '' else result
        return statements, result

    def _evaluate_snippet(self, code):
        """Evaluate the supplied code.

        No history is considered.
        :raises: JsonnetError if the underlying code raises RuntimeError.
        """
        try:
            return evaluate_snippet('', code,
                                    import_callback=self.jsonnet_import)
        except RuntimeError as e:
            raise JsonnetError(e) from e

    def _jsonnet_type(self, code):
        """Evaluate the jsonnet type (not python type) of code.

        No history is considered (it must be already added).
        """
        new_code = "std.type(\n{}\n)".format(code)
        out = self._evaluate_snippet(new_code)
        return json.loads(out)

    def _execute(self, code):
        """Execute method that does not update history or write output.

        :raises: JsonnetError on error.
        """
        new_code = self.history + code
        statements, result = self.split_code(new_code)
        if result is None:
            new_code += 'null'
        out = self._evaluate_snippet(new_code)
        if result is None:
            if json.loads(out) is None:
                out = ''
            else:
                raise ValueError('Bad input')
        elif code.startswith('//jupyter: string'):
            out = json.loads(out)
            if not isinstance(out, str):
                raise ExecutorInputError(
                    'Cannot output as raw string: value type is {}.'.format(
                        self._jsonnet_type(new_code)
                    )
                )
        return out, statements

    def jsonnet_import(self, base, rel):
        raise ValueError('Imports are not permitted.')

    def execute(self, code, silent):
        """Execute code

        On success, history will be updated.
        On error, the error is rewritten to fix the line/column text, as if
        none of the history had been there.
        If silent is true, no output is written.
        """
        try:
            out, statements = self._execute(code)
        except JsonnetError as e:
            row, column = self.get_current_offsets()
            raise e.with_offsets(-row, -column) from e
        if not silent:
            self.stdout_callback(out)
        self.history = statements

    def get_current_offsets(self):
        """Find current line/col offsets by forcing an error"""
        try:
            self._execute("error 'foo'")
        except JsonnetError as e:
            groups, _ = e.parse()
        else:
            raise AssertionError('execute failed to raise an exception.')
        if groups is None or groups.group('type') != 'RUNTIME ERROR':
            raise
        if groups.group('msg1') != 'foo':
            raise
        row_offset = int(groups.group('start_row')) - 1
        col_offset = int(groups.group('start_col')) - 1
        return row_offset, col_offset


class JupyterKernel(Kernel):

    implementation = "jupyter-jsonnet"

    implementation_version = "0.4"

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
        self.shell_handlers.update({
            k: getattr(self.ShellHandlers, k) for k in dir(self.ShellHandlers)
        })
        self.executor = JsonnetExecutor(self.send_output_response)

    def send_error_response(self, error_content):
        self.send_response(self.iopub_socket, 'error',
                           error_content)

    def send_output_response(self, output):
        """Write the supplied output to the output stream.

        Used primarily as a callback.  Might make sense as a send generator.
        """
        stream_content = {'name': 'stdout', 'text': output}
        self.send_response(self.iopub_socket, 'stream', stream_content)

    def do_execute(self, code, silent, store_history, user_expressions,
                   allow_stdin):
        """Execute the supplied code and communicate the outcome."""
        try:
            self.executor.execute(code, silent)
        except (JsonnetError, ExecutorInputError) as e:
            error_content, result = error_to_jupyter(
                str(e),
                self.execution_count
            )
            self.send_response(self.iopub_socket, 'error', error_content)
            return result
        return {
            'status': 'ok',
            'execution_count': self.execution_count,
            'payload': [],
            'user_expressions': {},
        }


if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=JupyterKernel)
