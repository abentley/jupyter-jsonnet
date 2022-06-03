from dataclasses import dataclass

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
            'traceback': [str(self.exception).splitlines()]
        }

    def result(self):
        result = self.error_content + {
            'execution_count': self.kernel.execution_count,
            'status': 'error',
        }

    def send_response(self):
        self.kernel.send_response(self.kernel.iopub_socket, 'error', self.error_content)


class JupyterKernel(Kernel):

    implementation = "jupyter-jsonnet"

    implementation_version = "0.1"

    language = "Jsonnet"

    language_version = "1.0"
    language_info = {'mimetype': 'text/plain', 'name': 'Jsonnet'}
    banner = "Welcome to Jsonnet!"

    def do_execute(self, code, silent, store_history, user_expressions,
                   allow_stdin):
        try:
            result = evaluate_snippet('', code)
        except RuntimeError as e:
            jp_err = JupyterError(e, self)
            jp_err.send_response()
            return jp_err.result()
        else:
            if not silent:
                stream_content = {'name': 'stdout', 'text': result}
                self.send_response(self.iopub_socket, 'stream', stream_content)
            return {
                'status': 'ok',
                'execution_count': self.execution_count,
                'payload': [],
                'user_expressions': {},
            }


if __name__ == '__main__':
    from ipykernel.kernelapp import IPKernelApp
    IPKernelApp.launch_instance(kernel_class=JupyterKernel)
