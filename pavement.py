# -*- coding: utf-8 -*-
################################################################################
#  Copyright (C) 2013  Travis Shirk <travis@pobox.com>
#
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
################################################################################
from __future__ import print_function
import os
import re
from paver.easy import *
from paver.path import path
import paver.setuputils
import paver.doctools
paver.setuputils.install_distutils_tasks()
import setuptools
import setuptools.command
try:
    from sphinxcontrib import paverutils
except:
    paverutils = None

PROJECT = u"mishmash"
VERSION = "0.3.0-alpha"

LICENSE = open("COPYING", "r").read().strip('\n')
DESCRIPTION = "Music database using Python and SQLAlchemy"
LONG_DESCRIPTION = """
FIXME
"""
URL = "http://mishmash.nicfit.net"
AUTHOR = "Travis Shirk"
AUTHOR_EMAIL = "travis@pobox.com"
SRC_DIST_TGZ = "%s-%s.tgz" % (PROJECT, VERSION)
SRC_DIST_ZIP = "%s.zip" % os.path.splitext(SRC_DIST_TGZ)[0]
DOC_DIST = "%s_docs-%s.tgz" % (PROJECT, VERSION)
MD5_DIST = "%s.md5" % os.path.splitext(SRC_DIST_TGZ)[0]
DOC_BUILD_D = "docs/_build"

PACKAGE_DATA = paver.setuputils.find_package_data("src/mishmash",
                                                  package="mishmash",
                                                  only_in_packages=True,
                                                  )

from pip.req import parse_requirements
install_reqs = parse_requirements("requirements.txt")
DEPS = [str(ir.req) for ir in install_reqs]

options(
    minilib=Bunch(
        # XXX: the explicit inclusion of 'version' is a workaround for:
        # https://github.com/paver/paver/issues/112
        extra_files=['doctools', "version"]
    ),
    setup=Bunch(
        name=PROJECT, version=VERSION,
        description=DESCRIPTION, long_description=LONG_DESCRIPTION,
        author=AUTHOR, maintainer=AUTHOR,
        author_email=AUTHOR_EMAIL, maintainer_email=AUTHOR_EMAIL,
        url=URL,
        download_url="%s/releases/%s" % (URL, SRC_DIST_TGZ),
        license="GPL",
        package_dir={"": "src"},
        packages=setuptools.find_packages("src",
                                          exclude=["test", "test.*"]),
        zip_safe=False,
        classifiers = [
            'Environment :: Console',
            'Environment :: Web Environment',
            'Framework :: Pyramid',
            'Intended Audience :: End Users/Desktop',
            'Intended Audience :: Developers',
            'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
            'Operating System :: POSIX',
            'Programming Language :: Python',
            'Topic :: Database',
            'Topic :: Internet :: WWW/HTTP',
            'Topic :: Multimedia :: Sound/Audio',
            'Topic :: Software Development :: Libraries :: Python Modules',
            ],
        platforms=("Any",),
        keywords=("python", "sqlalchemy", "music", "database"),
        scripts=["bin/mishmash"],
        package_data=PACKAGE_DATA,
        entry_points="""\
        [paste.app_factory]
        main = mishmash.web:main
        """,
        install_requires=DEPS,
    ),

    sdist=Bunch(
        formats="gztar,zip",
        dist_dir="dist",
    ),

    sphinx=Bunch(
        docroot=os.path.split(DOC_BUILD_D)[0],
        builddir=os.path.split(DOC_BUILD_D)[1],
        builder='html',
        template_args = {},
    ),

    cog=Bunch(
        beginspec='{{{cog',
        endspec='}}}',
        endoutput='{{{end}}}',
        includedir=path(__file__).abspath().dirname(),
    ),

    test=Bunch(
        pdb=False,
        coverage=False,
    ),

    release=Bunch(
        test=False,
    ),

    run2to3=Bunch(
        modernize=False,
    ),
)


@task
@no_help
def info_module():
    '''Convert src/mishmash//info.py.in to src/mishmash//info.py'''
    src = path("./src/mishmash//info.py.in")
    target = path("./src/mishmash//info.py")
    if target.exists() and not src.exists():
        return
    elif not src.exists():
        raise Exception("Missing src/mishmash//info.py.in")
    elif not target.exists() or src.ctime > target.ctime:
        src_file = src.open("r")
        target_file = target.open("w")

        src_data = re.sub("@PROJECT@", PROJECT, src_file.read())
        src_data = re.sub("@VERSION@", VERSION.split('-')[0], src_data)
        src_data = re.sub("@AUTHOR@", AUTHOR, src_data)
        src_data = re.sub("@URL@", URL, src_data)
        if '-' in VERSION:
            src_data = re.sub("@RELEASE@", VERSION.split('-')[1], src_data)
        else:
            src_data = re.sub("@RELEASE@", "final", src_data)

        target_file.write(src_data)
        target_file.close()


@task
@needs("info_module",
       "generate_setup",
       "minilib",
       "setuptools.command.build")
def build():
    '''Build the code'''
    pass


@task
#@needs("test_clean")
def clean():
    '''Cleans mostly everything'''
    path("build").rmtree()

    for p in path(".").glob("*.pyc"):
        p.remove()
    for d in [path("./src")]:
        for f in d.walk(pattern="*.pyc"):
            f.remove()
    try:
        from paver.doctools import uncog
        #uncog()
    except ImportError:
        pass


"""
@task
def docs_clean(options):
    '''Clean docs'''
    for d in ["html", "doctrees"]:
        path("%s/%s" % (DOC_BUILD_D, d)).rmtree()

    try:
        from paver.doctools import uncog
        uncog()
    except ImportError:
        pass
"""


@task
@needs("distclean",
       #"docs_clean",
       #"tox_clean",
      )
def maintainer_clean():
    path("paver-minilib.zip").remove()
    path("setup.py").remove()
    path("src/mishmash//info.py").remove()


@task
@needs("clean")
def distclean():
    '''Like 'clean' but also everything else'''
    path("tags").remove()
    path("dist").rmtree()
    path("src/mishmash.egg-info").rmtree()
    for f in path(".").walk(pattern="*.orig"):
        f.remove()
    path(".ropeproject").rmtree()


"""
@task
@needs("cog")
def docs(options):
    '''Sphinx documenation'''
    if not paverutils:
        raise RuntimeError("Sphinxcontib.paverutils needed to make docs")
    sh("sphinx-apidoc -o ./docs/api ./src/eyed3/")
    paverutils.html(options)
    print("Docs: file://%s/%s/%s/html/index.html" %
          (os.getcwd(), options.docroot, options.builddir))
"""


@task
@needs("distclean",
       "info_module",
       "generate_setup",
       "minilib",
       "setuptools.command.sdist",
       )
def sdist(options):
    '''Make a source distribution'''
    cwd = os.getcwd()
    try:
        name = os.path.splitext(SRC_DIST_TGZ)[0]
        os.chdir(options.sdist.dist_dir)
        # Caller of sdist can select the type of output, so existence checks...
        if os.path.exists("%s.tar.gz" % name):
            # Rename to .tgz
            sh("mv %s.tar.gz %s" % (os.path.splitext(SRC_DIST_TGZ)[0],
                                    SRC_DIST_TGZ))
            sh("md5sum %s >> %s" % (SRC_DIST_TGZ, MD5_DIST))
        if os.path.exists(SRC_DIST_ZIP):
            sh("md5sum %s >> %s" % (SRC_DIST_ZIP, MD5_DIST))
    finally:
        os.chdir(cwd)


"""
@task
def tox(options):
    sh("tox")


@task
def tox_clean(options):
    sh("rm -rf .tox")
"""


@task
def changelog():
    '''Update changelog, and commit it'''
    sh("hg log --style=changelog . >| ChangeLog")


@task
@no_help
def tags():
    '''ctags for development'''
    path("tags").remove()
    sh("ctags -R --exclude='tmp/*' --exclude='build/*'")


"""
@task
@needs("build")
@cmdopts([("pdb", "",
           u"Run with all output and launch pdb for errors and failures"),
          ("coverage", "", u"Run tests with coverage analysis"),
         ])
def test(options):
    '''Runs all tests'''
    if options.test and options.test.pdb:
        debug_opts = "--pdb --pdb-failures -s"
    else:
        debug_opts = ""

    if options.test and options.test.coverage:
        coverage_opts = (
            "--cover-erase --with-coverage --cover-tests --cover-inclusive "
            "--cover-package=eyed3 --cover-branches --cover-html "
            "--cover-html-dir=build/test/coverage src/test")
    else:
        coverage_opts = ""

    sh("nosetests --verbosity=1 --detailed-errors "
       "%(debug_opts)s %(coverage_opts)s" %
       {"debug_opts": debug_opts, "coverage_opts": coverage_opts})

    if coverage_opts:
        print("Coverage Report: file://%s/build/test/coverage/index.html" %
              os.getcwd())


@task
def test_clean():
    '''Clean tests'''
    path("built/test/html").rmtree()
    path(".coverage").remove()


@task
@needs("sdist")
def test_dist():
    '''Makes a dist package, unpacks it, and tests it.'''
    cwd = os.getcwd()
    pkg_d = os.path.splitext(SRC_DIST_TGZ)[0]
    try:
        os.chdir("./dist")
        sh("tar xzf %s" % SRC_DIST_TGZ)

        os.chdir(pkg_d)
        # Copy tests into src pkg
        sh("cp -r ../../src/test ./src")
        sh("python setup.py build")
        sh("python setup.py test")

        os.chdir("..")
        path(pkg_d).rmtree()
    finally:
        os.chdir(cwd)
"""


"""
@task
@needs("docs")
def docdist():
    path("./dist").exists() or os.mkdir("./dist")
    cwd = os.getcwd()
    try:
        os.chdir(DOC_BUILD_D)
        sh("tar czvf ../../dist/%s html" % DOC_DIST)
        os.chdir("%s/dist" % cwd)
        sh("md5sum %s >> %s" % (DOC_DIST, MD5_DIST))
    finally:
        os.chdir(cwd)

    pass


@task
@cmdopts([("test", "",
           u"Run in a mode where commits, pushes, etc. are performed"),
         ])
def release(options):
    from paver.doctools import uncog

    testing = options.release.test

    # Ensure we're on stable branch
    sh("test $(hg branch) = 'stable'")

    if not prompt("Is version *%s* correct?" % VERSION):
        print("Fix VERSION")
        return

    if not prompt("Is docs/changelog.rst up to date?"):
        print("Update changlelog")
        return

    print("Checking for clean working copy")
    if not testing:
        sh('test -z "$(hg status --modified --added --removed --deleted)"')
        sh("hg outgoing | grep 'no changes found'")
        sh("hg incoming | grep 'no changes found'")

    changelog()
    if prompt("Commit ChangeLog?") and not testing:
        sh("hg commit -m 'prep for release'")

    test()
    tox()

    sdist()
    docdist()
    uncog()
    test_dist()

    if prompt("Tag release 'v%s'?" % VERSION) and not testing:
        sh("hg tag v%s" % VERSION)
        # non-zero returned for success, it appears, ignore. but why not above?
        sh("hg commit -m 'tagged release'", ignore_error=True)

    if prompt("Push for release?") and not testing:
        sh("hg push --rev .")
"""


def prompt(prompt):
    print(prompt + ' ', end='')
    resp = raw_input()
    return True if resp in ["y", "yes"] else False


"""
def cog_pluginHelp(name):
    from string import Template
    import argparse
    import eyed3.plugins

    substs = {}
    template = Template(
'''
*$summary*

Names
-----
$name $altnames

Description
-----------
$description

Options
-------
.. code-block:: text

$options

''')

    plugin = eyed3.plugins.load(name)
    substs["name"] = plugin.NAMES[0]
    if len(plugin.NAMES) > 1:
        substs["altnames"] = "(aliases: %s)" % ", ".join(plugin.NAMES[1:])
    else:
        substs["altnames"] = ""
    substs["summary"] = plugin.SUMMARY
    substs["description"] = plugin.DESCRIPTION if plugin.DESCRIPTION else u""

    arg_parser = argparse.ArgumentParser()
    _ = plugin(arg_parser)

    buffer = u""
    found_opts = False
    for line in arg_parser.format_help().splitlines(True):
        if not found_opts:
            if (line.lstrip().startswith('-') and
                    not line.lstrip().startswith("-h")):
                buffer += (" " * 2) + line
                found_opts = True
        else:
            if buffer == '\n':
                buffer += line
            else:
                buffer += (" " * 2) + line
    if buffer.strip():
        substs["options"] = buffer
    else:
        substs["options"] = u"  No extra options supported"

    return template.substitute(substs)
__builtins__["cog_pluginHelp"] = cog_pluginHelp


# XXX: modified from paver.doctools._runcog to add includers
def _runcog(options, uncog=False):
    '''Common function for the cog and runcog tasks.'''

    info_module()

    import cogapp
    options.order('cog', 'sphinx', add_rest=True)
    c = cogapp.Cog()
    if uncog:
        c.options.bNoGenerate = True
    c.options.bReplace = True
    c.options.bDeleteCode = options.get("delete_code", False)
    includedir = options.get('includedir', None)
    if includedir:
        markers = options.get("include_markers")

        include = Includer(includedir, cog=c,
                           include_markers=options.get("include_markers"))
        # load cog's namespace with our convenience functions.
        c.options.defines['include'] = include
        c.options.defines['sh'] = _cogsh(c)

        cli_includer = CliExample(includedir, cog=c, include_markers=markers)
        c.options.defines["cli_example"] = cli_includer

    c.options.defines.update(options.get("defines", {}))

    c.sBeginSpec = options.get('beginspec', '[[[cog')
    c.sEndSpec = options.get('endspec', ']]]')
    c.sEndOutput = options.get('endoutput', '[[[end]]]')

    basedir = options.get('basedir', None)
    if basedir is None:
        basedir = path(options.get('docroot', "docs")) / \
                  options.get('sourcedir', "")
    basedir = path(basedir)

    pattern = options.get("pattern", "*.rst")
    if pattern:
        files = basedir.walkfiles(pattern)
    else:
        files = basedir.walkfiles()
    for f in files:
        dry("cog %s" % f, c.processOneFile, f)

from paver.doctools import Includer, _cogsh


class CliExample(Includer):
    def __call__(self, fn, section=None, lang="bash"):
        # Resetting self.cog to get a string back from Includer.__call__
        cog = self.cog
        self.cog = None
        raw = Includer.__call__(self, fn, section=section)
        self.cog = cog

        self.cog.cogmodule.out(u"\n.. code-block:: %s\n\n" % lang)
        for line in raw.splitlines(True):
            if line.strip() == "":
                self.cog.cogmodule.out(line)
            else:
                cmd = line.strip()
                cmd_line = ""
                if not cmd.startswith('#'):
                    cmd_line = "$ %s\n" % cmd
                else:
                    cmd_line = cmd + '\n'

                cmd_line = (' ' * 2) + cmd_line
                self.cog.cogmodule.out(cmd_line)
                output = sh(cmd, capture=True)
                if output:
                    self.cog.cogmodule.out("\n")
                for ol in output.splitlines(True):
                    self.cog.cogmodule.out(' ' * 2 + ol)
                if output:
                    self.cog.cogmodule.out("\n")


@task
def cog(options):
    '''Run cog on all docs'''
    _runcog(options)
"""
