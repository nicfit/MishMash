# -*- coding: utf-8 -*-
import mishmash
"""
test_mishmash
----------------------------------

Tests for `mishmash` module.
"""


def test_metadata():
    assert mishmash.version
    assert mishmash.__about__.project_name
    assert mishmash.__about__.version
    assert mishmash.__about__.version_info
    assert mishmash.__about__.author
    assert mishmash.__about__.author_email
    assert mishmash.__about__.years


def test_database_fixture(database):
    assert database.url
    assert database.engine
    assert database.SessionMaker


def test_session_fixture(session):
    assert session
