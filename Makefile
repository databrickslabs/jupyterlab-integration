.PHONY: clean wheel envs install tests check_version dist check_dist upload_test upload dev_tools bump bump_ext

PYCACHE := $(shell find . -name '__pycache__')
EGGS := $(shell find . -name '*.egg-info')

clean:
	rm -fr build dist $(EGGS) $(PYCACHE)

wheel:
	dev_tools/create-wheel.sh

envs:
	dev_tools/create-env-files.sh

tests: 
	cd tests && python -m unittest

install: envs wheel
	pip install --upgrade .

# version command

bump:
ifdef part
ifdef version
	bumpversion --new-version $(version) $(part) && grep current .bumpversion.cfg
else
	bumpversion $(part) && grep current .bumpversion.cfg
endif
else
	echo "Provide part=major|minor|patch|release|build and optionally version=x.y.z..."
	exit 1
endif

bump_ext:
ifdef part
	$(eval cur_version=$(shell cd extensions/databrickslabs_jupyterlab_status/ && npm version $(part) --preid=rc))
else
ifdef version
	$(eval cur_version := $(shell cd extensions/databrickslabs_jupyterlab_status/ && npm version $(version)))
else
	@echo "Provide part=major|minor|patch|prerelease or version=x.y.z..."
	exit 1
endif
endif
	@echo "New version: $(cur_version:v%=%)"

# check dev tools

check_version:
ifdef env_file
	dev_tools/check_versions $(env_file)
else
	echo "Provide env_file=databrickslabs_jupyterlab/env_files/env..."
	exit 1
endif

dev_tools:
	pip install twine bumpversion yapf pylint

# pypi commands

dist: clean
	@python setup.py sdist bdist_wheel

check_dist:
	@twine check dist/*

upload_test: dist
	@twine upload --repository testpypi dist/*

upload: dist
	@twine upload dist/*
