# -*- coding: utf-8 -*-

"""
test_mishmash
----------------------------------

Tests for `mishmash` module.
"""

import mishmash
from . import BaseTestCase


class TestMishmash(BaseTestCase):

    def test_metadata(self):
        assert(mishmash.__author__)
        assert(mishmash.__email__)
        assert(mishmash.__version__)
        assert(mishmash.__version_info__)
        assert(type(mishmash.__version_info__) is tuple)
        assert(len(mishmash.__version_info__) == 3)
        assert(mishmash.__version_txt__)
        assert(mishmash.__release__)
        assert(mishmash.__web__)
        assert(mishmash.__years__)

    def test_log_import(self):
        import logging
        assert("log" in dir(mishmash))
        assert(isinstance(mishmash.log, logging.Logger))
