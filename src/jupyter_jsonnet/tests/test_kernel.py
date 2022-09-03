from unittest import (
    main,
    TestCase,
)

from jupyter_jsonnet.kernel import (
    JupyterException,
    JupyterKernel,
)


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

    def test_get_offsets(self):
        kernel = JupyterKernel()
        self.assertEqual(kernel.get_current_offsets(), (0, 0))
        kernel.history += 'local x=5;'
        self.assertEqual(kernel.get_current_offsets(), (0, 10))
        kernel.history += '\n'
        self.assertEqual(kernel.get_current_offsets(), (1, 0))


class TestJupyterException(TestCase):

    def test_str(self):
        orig = RuntimeError('STATIC ERROR: 1:1: Unknown variable: y\n')
        jupyter = JupyterException(orig)
        self.assertEqual(str(jupyter), str(orig))

    def test_reraise(self):
        with self.assertRaisesRegex(JupyterException,
                                    'STATIC ERROR: 1:1: Unknown variable: y\n'):
            with JupyterException.reraise():
                raise RuntimeError('STATIC ERROR: 1:1: Unknown variable: y\n')

    def test_parse(self):
        result = JupyterException.from_str(
            'RUNTIME ERROR: hunting the snark\n\tfoo.c:2:12-37\t\n'
        ).parse()
        self.assertEqual((
            'RUNTIME ERROR', ': ', 'hunting the snark', '\n\t',
            'foo.c', ':', '2', None, None, ':', '12', '-', '37',
            '\t', None, '\n'
        ), result.groups())

    def test_parse_syntax(self):
        result = JupyterException.from_str(
            'STATIC ERROR: 1:1: Unknown variable: y\n'
        ).parse()
        self.assertEqual((
            'STATIC ERROR', ': ', None, None, None, None,
            '1', None, None, ':', '1', None, None,
            ': ', 'Unknown variable: y', '\n'
        ), result.groups())

    def test_rewrite(self):
        self.assertEqual(
            JupyterException.from_str(
                'STATIC ERROR: 1:12: Unknown variable: y\n'
            ).rewrite(0, 0),
            'STATIC ERROR: 1:12: Unknown variable: y\n'
        )
        self.assertEqual(
            JupyterException.from_str(
                'STATIC ERROR: 1:12: Unknown variable: y\n'
            ).rewrite(0, -9),
            'STATIC ERROR: 1:3: Unknown variable: y\n',
        )
        self.assertEqual(
            JupyterException.from_str(
                'STATIC ERROR: 1:12-24: Unknown variable: y\n'
            ).rewrite(0, -9),
            'STATIC ERROR: 1:3-15: Unknown variable: y\n',
        )


if __name__ == '__main__':
    main()
