from mishmash.orm import (Artist, Album, Library, VARIOUS_ARTISTS_NAME,
                          MAIN_LIB_ID, NULL_LIB_ID)
from .factories import (EpFactory, LibraryFactory, LpFactory,
                        DirectoryStructure)

def _isInitialDb(db):
    return db.query(Artist).one().name == VARIOUS_ARTISTS_NAME

'''
def test_library():
    # TODO
    lib = LibraryFactory(name="I don't like you LIBRARY")\
          .addEp(artist="Mikal Cronin", title="Tide 7\"", num_tracks=2,
                 track_titles=("Tide", "You Gotta Have Someone"),
                 temp_dir=str(tmpdir))
    pass
'''

def test_lpSync(tmpdir, database, mishmash_cmd):
    db = database.SessionMaker()
    lib_count = db.query(Library).count()
    assert lib_count == 2

    lp = LpFactory(temp_dir=str(tmpdir))

    dir_struct = DirectoryStructure.PREFERRED
    dir_struct.apply(*[t._mp3_file for t in lp.tracks], root_dir=tmpdir)

    mishmash_cmd(["info"], db_url=database.url)
    assert _isInitialDb(db)
    mishmash_cmd(["sync", str(tmpdir)], db_url=database.url)

    assert db.query(Library).count() == lib_count

    assert db.query(Artist).filter_by(lib_id=MAIN_LIB_ID).count() == 1
    assert db.query(Artist).filter_by(lib_id=MAIN_LIB_ID,
                                      name=lp.artist).count() == 1

    assert db.query(Album).filter_by(lib_id=MAIN_LIB_ID).count() == 1
    assert db.query(Album).filter_by(lib_id=MAIN_LIB_ID,
                                     title=lp.title).count() == 1

    ep = db.query(Album).filter_by(lib_id=MAIN_LIB_ID, title=lp.name).one()
    assert ep.type == "lp"

    # TODO: validate tracks

def test_epSync(tmpdir, database, mishmash_cmd):
    db = database.SessionMaker()
    lib_count = db.query(Library).count()
    assert lib_count == 2

    ep = EpFactory(artist="Mikal Cronin", title="Tide 7\"", num_tracks=2,
                   track_titles=("Tide", "You Gotta Have Someone"),
                   temp_dir=str(tmpdir))

    dir_struct = DirectoryStructure.PREFERRED
    dir_struct.apply(*[t._mp3_file for t in ep.tracks], root_dir=tmpdir)

    mishmash_cmd(["info"], db_url=database.url)
    assert _isInitialDb(db)
    mishmash_cmd(["sync", str(tmpdir)], db_url=database.url)

    assert db.query(Library).count() == lib_count

    assert db.query(Artist).filter_by(lib_id=MAIN_LIB_ID).count() == 1
    assert db.query(Artist).filter_by(lib_id=MAIN_LIB_ID,
                                      name="Mikal Cronin").count() == 1

    assert db.query(Album).filter_by(lib_id=MAIN_LIB_ID).count() == 1
    assert db.query(Album).filter_by(lib_id=MAIN_LIB_ID,
                                     title='Tide 7"').count() == 1

    ep = db.query(Album).filter_by(lib_id=MAIN_LIB_ID, title='Tide 7"').one()
    assert ep.type == "ep"

    # TODO: validate tracks

