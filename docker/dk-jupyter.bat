docker run -it --rm ^
    -p 8888:8888 ^
    -v %CD%/kernels:/home/dbuser/.local/share/jupyter/kernels/ ^
    -v %HOMEDRIVE%%HOMEPATH%/.ssh/:/home/dbuser/.ssh ^
    -v %HOMEDRIVE%%HOMEPATH%/.databrickscfg:/home/dbuser/.databrickscfg ^
    -v %CD%:/home/dbuser/notebooks ^
    bwalter42/databrickslabs_jupyterlab:2.2.0-rc4 ^
    /opt/conda/bin/jupyter %*