.PHONY: clean-pyc clean-build clean-patch docs clean help lint test test-all \
        coverage docs release dist 

help:
	@echo "clean-build - remove build artifacts"
	@echo "clean-pyc - remove Python file artifacts"
	@echo "clean-patch - remove patch artifacts (.rej, .orig)"
	@echo "lint - check style with flake8"
	@echo "test - run tests quickly with the default Python"
	@echo "test-all - run tests on every Python version with tox"
	@echo "coverage - check code coverage quickly with the default Python"
	@echo "docs - generate Sphinx HTML documentation, including API docs"
	@echo "release - package and upload a release"
	@echo "dist - package"

clean: clean-build clean-pyc clean-patch
	rm -fr htmlcov/
	rm -rf tags

clean-build:
	rm -fr build/
	rm -fr dist/
	rm -fr *.egg-info

clean-pyc:
	find . -name '*.pyc' -exec rm -f {} +
	find . -name '*.pyo' -exec rm -f {} +
	find . -name '*~' -exec rm -f {} +

clean-patch:
	find . -name '*.rej' -exec rm -f '{}' \;
	find . -name '*.orig' -exec rm -f '{}' \;

lint:
	flake8 mishmash tests

test:
	python setup.py test

test-all:
	tox

coverage:
	coverage run --source mishmash setup.py test
	coverage report -m
	coverage html
	@echo "file://`pwd`/htmlcov/index.html"

docs:
	rm -f docs/mishmash.rst
	rm -f docs/modules.rst
	sphinx-apidoc -o docs/ mishmash
	$(MAKE) -C docs clean
	$(MAKE) -C docs html
	@echo "file://`pwd`/docs/_build/html/index.html"

release: clean
	python setup.py sdist upload
	python setup.py bdist_wheel upload

dist: clean
	python setup.py sdist
	python setup.py bdist_wheel
	ls -l dist
