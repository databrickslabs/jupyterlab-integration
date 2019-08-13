check:
	dev_tools/check_versions $(ENV_FILE)

wheel:
	dev_tools/create-wheel.sh

envs:
	dev_tools/create-env-files.sh

build: envs wheel 

install: envs wheel
	pip install --upgrade .
	