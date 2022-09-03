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
            ('', None))

        self.assertEqual(
            JupyterKernel.split_code('{}'),
            ('', '{}'))

    def test_rewrite_error(self):
        self.assertEqual(
            JupyterKernel.rewrite_error(
                'STATIC ERROR: 1:12: Unknown variable: y\n', 0, 0
            ), 'STATIC ERROR: 1:12: Unknown variable: y\n'
        )
        self.assertEqual(
            JupyterKernel.rewrite_error(
                'STATIC ERROR: 1:12: Unknown variable: y\n', 0, -9
            ), 'STATIC ERROR: 1:3: Unknown variable: y\n',
        )
        self.assertEqual(
            JupyterKernel.rewrite_error(
                'STATIC ERROR: 2:12: Unknown variable: y', 0, -9
            ), 'STATIC ERROR: 2:12: Unknown variable: y'
        )
        self.assertEqual(
            JupyterKernel.rewrite_error(
                'STATIC ERROR: 2:12: Unknown variable: y', 0, -9
            ), 'STATIC ERROR: 2:12: Unknown variable: y'
        )

    def test_parse_error(self):
        result = JupyterKernel.parse_error(
            'RUNTIME ERROR: hunting the snark\n\tfoo.c:2:12-37\t\n'
        )
        self.assertEqual((
            'RUNTIME ERROR', ': ', 'hunting the snark', '\n\t',
            'foo.c', ':', '2', None, None, ':', '12', '-', '37',
            '\t', None, '\n'
        ), result.groups())

    def test_parse_error_syntax(self):
        result = JupyterKernel.parse_error(
            'STATIC ERROR: 1:1: Unknown variable: y\n'
        )
        self.assertEqual((
            'STATIC ERROR', ': ', None, None, None, None,
            '1', None, None, ':', '1', None, None,
            ': ', 'Unknown variable: y', '\n'
        ), result.groups())

    def test_get_offsets(self):
        kernel = JupyterKernel()
        self.assertEqual(kernel.get_current_offsets(), (0, 0))
        kernel.history += 'local x=5;'
        self.assertEqual(kernel.get_current_offsets(), (0, 10))
        kernel.history += '\n'
        self.assertEqual(kernel.get_current_offsets(), (1, 0))


if __name__ == '__main__':
    main()
