FROM continuumio/miniconda3

RUN /opt/conda/bin/pip install --upgrade databrickslabs-jupyterlab==2.0.0-rc2

RUN . /opt/conda/bin/activate base && \
    /opt/conda/bin/databrickslabs-jupyterlab -b

ENV CONDA_DEFAULT_ENV=base

RUN useradd -ms /bin/bash dbuser

RUN mkdir -p /home/dbuser/.local/share/jupyter/ && \
    mkdir -p /home/dbuser/.jupyter/

ADD jupyter_notebook_config.py /home/dbuser/.jupyter/

RUN chown -R dbuser:dbuser /home/dbuser/.jupyter && \
    chown -R dbuser:dbuser /home/dbuser/.local/

USER dbuser
