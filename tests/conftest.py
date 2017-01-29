# -*- coding: utf-8 -*-
import unittest
from pyramid import testing
import mishmash.database

settings = {
    'sqlalchemy.url': 'sqlite:///mishmash.test.db',
}
"""Bare minimum settings required for testing."""


class BaseTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        (cls.engine,
         cls.session) = mishmash.database.init(settings['sqlalchemy.url'],
                                               drop_all=True)

    @classmethod
    def tearDownClass(cls):
        cls.session.close()

    def setUp(self):
        request = testing.DummyRequest()
        self.config = testing.setUp(request=request)
        self.config.add_settings(settings)

    def tearDown(self):
        testing.tearDown()
