"""Tests for executor.py — code execution sandbox."""
from executor import execute_code


class TestExecuteCodeOutput:
    """Test stdout capture from executed code."""

    def test_simple_print(self, mock_resolve):
        output, error = execute_code('print("hello")', mock_resolve)
        assert output == "hello\n"
        assert error is None

    def test_multiple_prints(self, mock_resolve):
        code = 'print("a")\nprint("b")\nprint("c")'
        output, error = execute_code(code, mock_resolve)
        assert output == "a\nb\nc\n"
        assert error is None

    def test_no_output(self, mock_resolve):
        output, error = execute_code("x = 1 + 1", mock_resolve)
        assert output == ""
        assert error is None

    def test_print_with_format(self, mock_resolve):
        output, error = execute_code('print(f"result: {2 + 3}")', mock_resolve)
        assert output == "result: 5\n"
        assert error is None


class TestExecuteCodeErrors:
    """Test error handling in executed code."""

    def test_syntax_error(self, mock_resolve):
        output, error = execute_code("def bad(", mock_resolve)
        assert error is not None
        assert "SyntaxError" in error

    def test_runtime_error(self, mock_resolve):
        output, error = execute_code("1 / 0", mock_resolve)
        assert error is not None
        assert "ZeroDivisionError" in error

    def test_name_error(self, mock_resolve):
        output, error = execute_code("print(undefined_var)", mock_resolve)
        assert error is not None
        assert "NameError" in error

    def test_error_still_captures_prior_output(self, mock_resolve):
        code = 'print("before")\n1/0'
        output, error = execute_code(code, mock_resolve)
        assert "before" in output
        assert error is not None
        assert "ZeroDivisionError" in error


class TestExecuteCodeResolveAccess:
    """Test that Resolve objects are accessible in executed code."""

    def test_resolve_object(self, mock_resolve):
        output, error = execute_code('print(resolve.GetVersionString())', mock_resolve)
        assert output == "19.1.2\n"
        assert error is None

    def test_project_object(self, mock_resolve):
        output, error = execute_code('print(project.GetName())', mock_resolve)
        assert output == "Test Project\n"
        assert error is None

    def test_timeline_object(self, mock_resolve):
        output, error = execute_code('print(timeline.GetName())', mock_resolve)
        assert output == "Main Timeline\n"
        assert error is None

    def test_media_pool_object(self, mock_resolve):
        code = 'clips = media_pool.GetRootFolder().GetClipList()\nprint(len(clips))'
        output, error = execute_code(code, mock_resolve)
        assert output == "3\n"
        assert error is None

    def test_project_manager_object(self, mock_resolve):
        output, error = execute_code(
            'print(project_manager.GetCurrentProject().GetName())', mock_resolve
        )
        assert output == "Test Project\n"
        assert error is None

    def test_no_project(self, mock_resolve_no_project):
        output, error = execute_code('print(project)', mock_resolve_no_project)
        assert output == "None\n"
        assert error is None

    def test_no_timeline(self, mock_resolve_no_timeline):
        output, error = execute_code('print(timeline)', mock_resolve_no_timeline)
        assert output == "None\n"
        assert error is None


class TestExecuteCodeBuiltins:
    """Test that allowed builtins work in sandbox."""

    def test_len(self, mock_resolve):
        output, error = execute_code('print(len([1,2,3]))', mock_resolve)
        assert output == "3\n"
        assert error is None

    def test_range(self, mock_resolve):
        output, error = execute_code('print(list(range(3)))', mock_resolve)
        assert output == "[0, 1, 2]\n"
        assert error is None

    def test_enumerate(self, mock_resolve):
        output, error = execute_code(
            'print(list(enumerate(["a","b"])))', mock_resolve
        )
        assert output == "[(0, 'a'), (1, 'b')]\n"
        assert error is None

    def test_sorted(self, mock_resolve):
        output, error = execute_code('print(sorted([3,1,2]))', mock_resolve)
        assert output == "[1, 2, 3]\n"
        assert error is None

    def test_type_conversions(self, mock_resolve):
        output, error = execute_code('print(int("42"), float("3.14"), str(99))', mock_resolve)
        assert output == "42 3.14 99\n"
        assert error is None

    def test_dict_and_list(self, mock_resolve):
        code = 'd = dict(a=1, b=2)\nprint(sorted(d.items()))'
        output, error = execute_code(code, mock_resolve)
        assert output == "[('a', 1), ('b', 2)]\n"
        assert error is None

    def test_exception_handling(self, mock_resolve):
        code = '''
try:
    x = 1 / 0
except ZeroDivisionError:
    print("caught")
'''
        output, error = execute_code(code, mock_resolve)
        assert output == "caught\n"
        assert error is None

    def test_time_module(self, mock_resolve):
        output, error = execute_code('print(type(time.time()).__name__)', mock_resolve)
        assert output == "float\n"
        assert error is None

    def test_os_module(self, mock_resolve):
        output, error = execute_code('print(os.path.join("a", "b"))', mock_resolve)
        assert error is None
        assert "a" in output and "b" in output


class TestExecuteCodeStdoutRestored:
    """Test that stdout is always restored even after errors."""

    def test_stdout_restored_after_success(self, mock_resolve):
        import sys
        original = sys.stdout
        execute_code('print("test")', mock_resolve)
        assert sys.stdout is original

    def test_stdout_restored_after_error(self, mock_resolve):
        import sys
        original = sys.stdout
        execute_code('raise ValueError("boom")', mock_resolve)
        assert sys.stdout is original

    def test_stdout_restored_after_syntax_error(self, mock_resolve):
        import sys
        original = sys.stdout
        execute_code('def bad(', mock_resolve)
        assert sys.stdout is original
