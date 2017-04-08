import datetime
import mishmash
from mishmash.orm import (Meta, Library,
                          NULL_LIB_ID, NULL_LIB_NAME,
                          MAIN_LIB_ID, MAIN_LIB_NAME)


def test_meta_table(session):
    metadata = session.query(Meta).one()
    assert metadata.version == mishmash.version
    assert metadata.last_sync is None


def test_meta_table_write(session):
    metadata = session.query(Meta).one()
    metadata.version = "1.2.3"
    t = datetime.datetime.utcnow()
    metadata.last_sync = t
    session.add(metadata)
    session.commit()

    metadata = session.query(Meta).one()
    assert metadata.version == "1.2.3"
    assert metadata.last_sync == t


def test_libraries_table(session):
    default_rows = session.query(Library).all()
    assert len(default_rows) == 2
    assert default_rows[0].id == NULL_LIB_ID
    assert default_rows[0].name == NULL_LIB_NAME
    assert default_rows[0].last_sync is None
    assert default_rows[1].id == MAIN_LIB_ID
    assert default_rows[1].name == MAIN_LIB_NAME
    assert default_rows[1].last_sync is None
