# -*- coding: utf-8 -*-

"""
test_mishmash
----------------------------------

Tests for `mishmash` module.
"""

import unittest

import mishmash


class TestMishmash(unittest.TestCase):

    def setUp(self):
        pass

    def test_metadata(self):
        assert(mishmash.__author__)
        assert(mishmash.__email__)
        assert(mishmash.__version__)
        assert(mishmash.__version_info__)
        assert(mishmash.__version_txt__)
        assert(mishmash.__release__)
        assert(mishmash.__web__)
        assert(mishmash.__years__)

    def tearDown(self):
        pass


if __name__ == '__main__':
    unittest.main()
