from mishmash.orm import (Artist, Album, Library, VARIOUS_ARTISTS_NAME,
                          MAIN_LIB_ID, NULL_LIB_ID)
from .factories import (EpFactory, LibraryFactory, LpFactory,
                        DirectoryStructure)

def _isInitialDb(db):
    return db.query(Artist).one().name == VARIOUS_ARTISTS_NAME

'''
def test_library(tmpdir, database, mishmash_cmd):
    session = database.SessionMaker()
    assert _isInitialDb(session)

    lib = (LibraryFactory()
              .add(EpFactory())
              .add(LpFactory())
              .add(LpFactory())
              .add(EpFactory()))

    dir_struct = DirectoryStructure.PREFERRED
    for album in lib.albums():
        dir_struct.apply(*[t._mp3_file for t in album.tracks])
        
    #dir_struct.apply(*[t._mp3_file for t in [alb.tracks
    #                                            for alb in lib.albums()]],
    #                 root_dir=tmpdir)

    #mishmash_cmd(["sync", str(tmpdir)], db_url=database.url)
'''


def test_lpSync(tmpdir, database, mishmash_cmd):
    session = database.SessionMaker()
    lib_count = session.query(Library).count()
    assert lib_count == 2

    lp = LpFactory(temp_dir=str(tmpdir))

    dir_struct = DirectoryStructure.PREFERRED
    dir_struct.apply(*[t._mp3_file for t in lp.tracks], root_dir=tmpdir)

    mishmash_cmd(["info"], db_url=database.url)
    assert _isInitialDb(session)
    mishmash_cmd(["sync", str(tmpdir)], db_url=database.url)

    assert session.query(Library).count() == lib_count

    assert session.query(Artist).filter_by(lib_id=MAIN_LIB_ID).count() == 1
    assert (session.query(Artist).filter_by(lib_id=MAIN_LIB_ID,
                                            name=lp.artist).count() == 1 or
            session.query(Artist).filter_by(lib_id=MAIN_LIB_ID,
                                            name=lp.artist[0:30]).count() == 1
           )

    assert session.query(Album).filter_by(lib_id=MAIN_LIB_ID).count() == 1
    assert (session.query(Album).filter_by(lib_id=MAIN_LIB_ID,
                                           title=lp.title).count() == 1 or
            session.query(Artist).filter_by(lib_id=MAIN_LIB_ID,
                                            name=lp.artist[0:30]).count() == 1)

    lp = session.query(Album)\
                .filter((Library.id == MAIN_LIB_ID) &
                        ((Album.title == lp.title) |
                         (Album.title == lp.title[:30])))\
                .one()
    assert lp.type == "lp"

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
    assert ep.type in ("ep", None)

    # TODO: validate tracks

