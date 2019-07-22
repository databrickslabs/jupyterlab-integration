all:
	mkdir -p databricks_jupyterlab/lib
	rm -f databricks_jupyterlab/lib/*
	python3 setup.py bdist_wheel
	cp dist/databricks_jupyterlab-0.1.0-py3-none-any.whl databricks_jupyterlab/lib/
	pip install -v --upgrade .

dist: dist/databricks_jupyterlab-0.1.0-py3-none-any.whl
	tar -czv --exclude=./.git --exclude=install.sh -f ../remote-jupyter.tgz .
	cp ../remote-jupyter.tgz install.sh /Volumes/GoogleDrive/My\ Drive/Demos/Jupyter\ Lab\ Integration/package