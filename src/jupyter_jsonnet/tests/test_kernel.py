from unittest import (
    main,
    TestCase,
)

from jupyter_jsonnet.kernel import JupyterKernel

class TestJupyterKernel(TestCase):

    def test_split_code(self):
        self.assertEqual(
            JupyterKernel.split_code(";"),
            (';', None))

        self.assertEqual(
            JupyterKernel.split_code("  ; "),
            ('  ;', None))

        self.assertEqual(
            JupyterKernel.split_code("foo; bar"),
            ('foo;', ' bar'))

        self.assertEqual(
            JupyterKernel.split_code('   '),
            ('   ', None))


if __name__ == '__main__':
    main()
