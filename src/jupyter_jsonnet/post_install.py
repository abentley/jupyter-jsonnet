from pathlib import Path
import json
from tempfile import TemporaryDirectory

from jupyter_client.kernelspec import KernelSpecManager


kernel_spec = {
    'argv': [
        'python3', '-m', 'jupyter_jsonnet.kernel', '-f', "{connection_file}",
    ],
    'display_name': 'Jsonnet',
}


def main():
    manager = KernelSpecManager()
    with TemporaryDirectory() as spec_dir:
        with (Path(spec_dir) / 'kernel.json').open('w') as f:
            json.dump(kernel_spec, f, indent=2, sort_keys=True)
        manager.install_kernel_spec(spec_dir, 'jsonnet', user=True)


if __name__ == '__main__':
    main()
