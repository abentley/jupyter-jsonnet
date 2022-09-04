from unittest import (
    main,
    TestCase,
)

from jupyter_jsonnet.kernel import (
    JsonnetError,
    JsonnetExecutor,
)


class TestJsonnetExecutor(TestCase):

    def test_split_code(self):
        self.assertEqual(
            JsonnetExecutor.split_code(";"),
            (';', None))

        self.assertEqual(
            JsonnetExecutor.split_code("  ; "),
            ('  ;', None))

        self.assertEqual(
            JsonnetExecutor.split_code("foo; bar"),
            ('foo;', ' bar'))

        self.assertEqual(
            JsonnetExecutor.split_code('   '),
            ('', None))

        self.assertEqual(
            JsonnetExecutor.split_code('{}'),
            ('', '{}'))

    def test_get_offsets(self):
        executor = JsonnetExecutor(None)
        self.assertEqual(executor.get_current_offsets(), (0, 0))
        executor.history += 'local x=5;'
        self.assertEqual(executor.get_current_offsets(), (0, 10))
        executor.history += '\n'
        self.assertEqual(executor.get_current_offsets(), (1, 0))


class TestJsonnetError(TestCase):

    def test_str(self):
        orig = RuntimeError('STATIC ERROR: 1:1: Unknown variable: y\n')
        jupyter = JsonnetError(orig)
        self.assertEqual(str(jupyter), str(orig))

    def test_parse(self):
        result = JsonnetError.from_str(
            'RUNTIME ERROR: hunting the snark\n\tfoo.c:2:12-37\t\n'
        ).parse()[0]
        self.assertEqual((
            'RUNTIME ERROR', ': ', 'hunting the snark', '\n\t',
            'foo.c', ':', '', '2', ':', '12', '-', None, None, None, '37',
            '', '\t', None, '\n'
        ), result.groups())

    def test_parse_syntax(self):
        result = JsonnetError.from_str(
            'STATIC ERROR: 1:1: Unknown variable: y\n'
        ).parse()[0]
        self.assertEqual((
            'STATIC ERROR', ': ', None, None, None, None, '',
            '1', ':', '1', None, None, None, None, None, '',
            ': ', 'Unknown variable: y', '\n'
        ), result.groups())

    def test_parse_multiline(self):
        result = JsonnetError.from_str(
            'RUNTIME ERROR: hello\nworld\n\t(1:1)-(2:7)\t\n'
        ).parse()[0]
        self.assertEqual((
            'RUNTIME ERROR', ': ', 'hello\nworld', '\n\t',
            None, None, '(', '1', ':', '1', ')-', '(', '2', ':', '7',
            ')', '\t', None, '\n'
        ), result.groups())

    def test_rewrite(self):
        self.assertEqual(
            JsonnetError.from_str(
                'STATIC ERROR: 1:12: Unknown variable: y\n'
            ).rewrite(0, 0),
            'STATIC ERROR: 1:12: Unknown variable: y\n'
        )
        self.assertEqual(
            JsonnetError.from_str(
                'STATIC ERROR: 1:12: Unknown variable: y\n'
            ).rewrite(0, -9),
            'STATIC ERROR: 1:3: Unknown variable: y\n',
        )
        self.assertEqual(
            JsonnetError.from_str(
                'STATIC ERROR: 1:12-24: Unknown variable: y\n'
            ).rewrite(0, -9),
            'STATIC ERROR: 1:3-15: Unknown variable: y\n',
        )
        self.assertEqual(
            JsonnetError.from_str(
                'STATIC ERROR: 5:12-24: Unknown variable: y\n'
            ).rewrite(-3, -9),
            'STATIC ERROR: 2:3-15: Unknown variable: y\n',
        )

    def test_rewrite_multiline(self):
        self.assertEqual(
            JsonnetError.from_str(
                'RUNTIME ERROR: hello\nworld\n\t(5:10)-(6:7)\t\n'
            ).rewrite(-3, -9),
            'RUNTIME ERROR: hello\nworld\n\t(2:1)-(3:7)\t\n',
        )


if __name__ == '__main__':
    main()
