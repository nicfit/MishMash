# -*- coding: utf-8 -*-
import pytest
from mishmash.config import DEFAULT_CONFIG, Config


def test_Config_nofile():
    c = Config(None)
    assert c.filename is None
    with pytest.raises(Exception):
        assert c.db_url is None
    with pytest.raises(Exception):
        assert c.music_libs is None
