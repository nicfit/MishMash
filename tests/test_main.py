from unittest.mock import Mock
from mishmash.__main__ import MishMash


def test_main_noargs():
    app = MishMash()
    app.arg_parser.print_help = Mock()

    retval = app._run([])

    app.arg_parser.print_help.assert_called()
    assert retval == 1
