.PHONY: help build test dist docs tags cookiecutter docker
SRC_DIRS = ./mishmash
TEST_DIR = ./tests
TEMP_DIR ?= ./tmp
CC_DIR = ${TEMP_DIR}/MishMash
NAME ?= Travis Shirk
EMAIL ?= travis@pobox.com
GITHUB_USER ?= nicfit
GITHUB_REPO ?= MishMash
PYPI_REPO = pypitest
PROJECT_NAME = $(shell python setup.py --name 2> /dev/null)
VERSION = $(shell python setup.py --version 2> /dev/null)
RELEASE_NAME = $(shell python setup.py --release-name 2> /dev/null)
CHANGELOG = HISTORY.rst
CHANGELOG_HEADER = v${VERSION} ($(shell date --iso-8601))$(if ${RELEASE_NAME}, : ${RELEASE_NAME},)

help:
	@echo "test - run tests quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "clean - remove all build, test, coverage and Python artifacts"
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-test - remove test and coverage artifacts"
	@echo "clean-docs - remove autogenerating doc artifacts"
	@echo "clean-patch - remove patch artifacts (.rej, .orig)"
	@echo "build - byte-compile python files and generate other build objects"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "test-all - run tests on every Python version with tox"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "test-all - run tests on various Python versions with tox"
	@echo "release - package and upload a release"
	@echo "          PYPI_REPO=[pypitest]|pypi"
	@echo "pre-release - check repo and show version, generate changelog, etc.
	@echo "dist - package"
	@echo "install - install the package to the active Python's site-packages"
	@echo "build - build package source files"
	@echo ""
	@echo "Options:"
	@echo "TEST_PDB - If defined PDB options are added when 'pytest' is invoked"
	@echo "BROWSER - HTML viewer used by docs-view/coverage-view"
	@echo "CC_MERGE - Set to no to disable cookiecutter merging."
	@echo "CC_OPTS - OVerrided the default options (--no-input) with your own."

build:
	python setup.py build

clean: clean-local clean-build clean-pyc clean-test clean-patch clean-docs
	rm -rf tags

clean-local:
	-rm requirements/extra_example.in

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +
	find . -name '__pycache__' -exec rm -fr {} +

clean-test:
	rm -fr .tox/
	rm -f .coverage
	rm -rf "${CC_DIR}"

clean-patch:
	find . -name '*.rej' -exec rm -f '{}' \;
	find . -name '*.orig' -exec rm -f '{}' \;

lint:
	flake8 $(SRC_DIRS)

_PYTEST_OPTS=
ifdef TEST_PDB
    _PDB_OPTS=--pdb -s
endif
test:
	pytest $(_PYTEST_OPTS) $(_PDB_OPTS) ${TEST_DIR}

test-all:
	tox

coverage:
	pytest --cov=./mishmash \
           --cov-report=html --cov-report term \
           --cov-config=setup.cfg ${TEST_DIR}

coverage-view: coverage
	${BROWSER} build/tests/coverage/index.html;\

docs:
	rm -f docs/mishmash.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ ${SRC_DIRS}
	$(MAKE) -C docs clean
	$(MAKE) -C docs html

docs-view: docs
	$(BROWSER) docs/_build/html/index.html

docs-dist: clean-docs docs
	test -d dist || mkdir dist
	cd docs/_build && \
	    tar czvf ../../dist/${PROJECT_NAME}-${VERSION}_docs.tar.gz html

clean-docs:
	$(MAKE) -C docs clean
	-rm README.html

# FIXME: never been tested
servedocs: docs
	watchmedo shell-command -p '*.rst' -c '$(MAKE) -C docs html' -R -D .

pre-release: lint test changelog pip-reqs
	@echo "VERSION: $(VERSION)"
	$(eval RELEASE_TAG = v${VERSION})
	@echo "RELEASE_TAG: $(RELEASE_TAG)"
	@echo "RELEASE_NAME: $(RELEASE_NAME)"
	check-manifest
	@if git tag -l | grep ${RELEASE_TAG} > /dev/null; then \
        echo "Version tag '${RELEASE_TAG}' already exists!"; \
        false; \
    fi
	IFS=$$'\n';\
	for auth in `git authors --list`; do \
		echo "Checking $$auth...";\
		grep "$$auth" AUTHORS.rst || echo "* $$auth" >> AUTHORS.rst;\
	done
	@test -n "${GITHUB_USER}" || (echo "GITHUB_USER not set, needed for github" && false)
	@test -n "${GITHUB_TOKEN}" || (echo "GITHUB_TOKEN not set, needed for github" && false)
	@github-release --version    # Just a exe existence check

pip-reqs:
	pip-compile requirements/*.in -o ./requirements.txt

changelog:
	last=`git tag -l --sort=version:refname | grep '^v[0-9]' | tail -n1`;\
	if ! grep "${CHANGELOG_HEADER}" ${CHANGELOG} > /dev/null; then \
		rm -f ${CHANGELOG}.new; \
		if test -n "$$last"; then \
			gitchangelog show --author-format=email $${last}..HEAD |\
			  sed "s|^%%version%% .*|${CHANGELOG_HEADER}|" |\
			  sed '/^.. :changelog:/ r/dev/stdin' ${CHANGELOG} \
			 > ${CHANGELOG}.new; \
		else \
			cat ${CHANGELOG} |\
			  sed "s/^%%version%% .*/${CHANGELOG_HEADER}/" \
			> ${CHANGELOG}.new;\
		fi; \
		mv ${CHANGELOG}.new ${CHANGELOG}; \
	fi

build-release: test-all dist

freeze-release:
	@# TODO: check for incoming
	@(git diff --quiet && git diff --quiet --staged) || \
        (printf "\n!!! Working repo has uncommited/unstaged changes. !!!\n" && \
         printf "\nCommit and try again.\n" && false)

tag-release:
	git tag -a $(RELEASE_TAG) -m "Release $(RELEASE_TAG)"
	git push --tags origin

release: pre-release freeze-release build-release tag-release upload-release

github-release:
	name="${RELEASE_TAG}"; \
    if test -n "${RELEASE_NAME}"; then \
        name="${RELEASE_TAG} (${RELEASE_NAME})"; \
    fi; \
    prerelease=""; \
    if echo "${RELEASE_TAG}" | grep '[^v0-9\.]'; then \
        prerelease="--pre-release"; \
    fi; \
    echo "NAME: $$name"; \
    echo "PRERELEASE: $$prerelease"; \
    github-release --verbose release --user "${GITHUB_USER}" \
                   --repo ${GITHUB_REPO} --tag ${RELEASE_TAG} \
                   --name "$${name}" $${prerelease}
	for file in $$(find dist -type f -exec basename {} \;) ; do \
        echo "FILE: $$file"; \
        github-release upload --user "${GITHUB_USER}" --repo ${GITHUB_REPO} \
                   --tag ${RELEASE_TAG} --name $${file} --file dist/$${file}; \
    done

web-release:
	@# Not implemented
	@true

upload-release: github-release pypi-release web-release

pypi-release:
	# FIXME: gotta skip docs, md5s, etc.
	find dist -type f -exec twine register -r ${PYPI_REPO} {} \;
	find dist -type f -exec twine upload -r ${PYPI_REPO} --skip-existing {} \;

sdist: build
	python setup.py sdist --formats=gztar,zip
	python setup.py bdist_egg
	python setup.py bdist_wheel

dist: clean sdist docs-dist
	@# The cd dist keeps the dist/ prefix out of the md5sum files
	cd dist && \
	for f in $$(ls); do \
		md5sum $${f} > $${f}.md5; \
	done
	ls -l dist

install: clean
	python setup.py install

tags:
	ctags -R ${SRC_DIRS}

README.html: README.rst
	rst2html5.py README.rst >| README.html
	if test -n "${BROWSER}"; then \
		${BROWSER} README.html;\
	fi

CC_MERGE ?= yes
CC_OPTS ?= --no-input
GIT_COMMIT_HOOK = .git/hooks/commit-msg
cookiecutter:
	rm -rf "${CC_DIR}"
	if test "${CC_MERGE}" == "no"; then \
		nicfit cookiecutter ${CC_OPTS} "${TEMP_DIR}"; \
		git -C "${CC_DIR}" diff; \
		git -C "${CC_DIR}" status -s -b; \
	else \
		nicfit cookiecutter --merge ${CC_OPTS} "${TEMP_DIR}" \
		       --extra-merge ${GIT_COMMIT_HOOK} ${GIT_COMMIT_HOOK};\
	fi


docker:
	docker build -f ./docker/Dockerfile.arch -t mishmash-arch docker/
	rm -rf docker/src && mkdir docker/src
	git ls-files -z | grep -vz docker/ | while IFS= read -r -d '' file; do \
		mkdir -p docker/src/`dirname $$file`;\
		cp "$$file" ./docker/src/$$file;\
	done
	VERSION=${VERSION} docker-compose -f ./docker/docker-compose.yml build

docker-run:
	VERSION=${VERSION} docker-compose -f ./docker/docker-compose.yml up -d
	docker logs dev-MishMash
	docker ps | grep -i --color mishmash

docker-publish: docker
	# TODO
