.PHONY: clean wheel install tests check_version dist check_dist upload_test upload dev_tools bump bump_ext release

NO_COLOR = \x1b[0m
OK_COLOR = \x1b[32;01m
ERROR_COLOR = \x1b[31;01m

PYCACHE := $(shell find . -name '__pycache__')
EGGS := $(wildcard '*.egg-info')
CURRENT_VERSION := $(shell awk '/current_version/ {print $$3}' .bumpversion.cfg)

clean:
	@echo "$(OK_COLOR)=> Cleaning$(NO_COLOR)"
	@rm -fr build dist $(EGGS) $(PYCACHE) databrickslabs_jupyterlab/lib/* databrickslabs_jupyterlab/env_files/*

# Tests

tests: 
	cd tests && python -m unittest

# Version commands

bump:
ifdef part
ifdef version
	bumpversion --new-version $(version) $(part) && grep current .bumpversion.cfg
else
	bumpversion $(part) && grep current .bumpversion.cfg
endif
else
	@echo "$(ERROR_COLOR)Provide part=major|minor|patch|release|build and optionally version=x.y.z...$(NO_COLOR)"
	exit 1
endif

bump_ext:
ifdef part
	$(eval cur_version=$(shell cd extensions/databrickslabs_jupyterlab_status/ && npm version $(part) --preid=rc))
else
ifdef version
	$(eval cur_version := $(shell cd extensions/databrickslabs_jupyterlab_status/ && npm version $(version)))
else
	@echo "$(ERROR_COLOR)Provide part=major|minor|patch|prerelease or version=x.y.z...$(NO_COLOR)"
	exit 1
endif
endif
	@echo "$(OK_COLOR)=> New version: $(cur_version:v%=%)$(NO_COLOR)"

# Dist commands

dist: clean
	@echo "$(OK_COLOR)=> Creating Wheel$(NO_COLOR)"
	@mkdir -p databrickslabs_jupyterlab/lib
	@python setup.py sdist bdist_wheel
	@echo "$(OK_COLOR)=> Copying wheel into distributions$(NO_COLOR)"
	@cp dist/databrickslabs_jupyterlab-*-py3-none-any.whl databrickslabs_jupyterlab/lib/
	@cp env.yml labextensions.txt "databrickslabs_jupyterlab/lib/"

release:
	git add .
	git status
	git commit -m "Latest release: $(CURRENT_VERSION)"
	git tag -a v$(CURRENT_VERSION) -m "Latest release: $(CURRENT_VERSION)"

install:
	@echo "$(OK_COLOR)=> Installing databrickslabs_jupyterlab$(NO_COLOR)"
	@pip install --upgrade .

check_dist:
	@twine check dist/*

upload: dist
	@twine upload dist/*

# dev tools

check_version:
ifdef env_file
	dev_tools/check_versions $(env_file)
else
	@echo "$(ERROR_COLOR)Provide env_file=databrickslabs_jupyterlab/env_files/env...$(NO_COLOR)"
	exit 1
endif

dev_tools:
	pip install twine bumpversion yapf pylint

