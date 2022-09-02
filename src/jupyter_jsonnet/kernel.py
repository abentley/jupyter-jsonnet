# Copyright Aaron Bentley 2022
# This software is licenced under the MIT license
# <LICENSE or http://opensource.org/licenses/MIT>

from dataclasses import dataclass
import json
from importlib import metadata

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

    def do_execute(self, code, silent, store_history, user_expressions,
                   allow_stdin):
        new_code = self.history + code
        statements, result = self.split_code(new_code)
        try:
            if result is None:
                new_code += 'null'
            output = evaluate_snippet('', new_code)
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


if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=JupyterKernel)
