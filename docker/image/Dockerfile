FROM continuumio/miniconda3

RUN . /opt/conda/bin/activate base && \
    /opt/conda/bin/pip install --upgrade databrickslabs-jupyterlab==2.1.0-rc4 && \
    /opt/conda/bin/databrickslabs-jupyterlab -b && \
    echo "cleaning" && \
    npm install -g yarn && \
    yarn cache clean && \
    conda clean --all && \
    /opt/conda/bin/jupyter lab clean && \
    find / -type f -name '*.py[co]' -delete -o -type d -name __pycache__ -delete

ENV CONDA_DEFAULT_ENV=base

RUN useradd -ms /bin/bash dbuser && \
    mkdir -p /home/dbuser/.local/share/jupyter/ && \
    mkdir -p /home/dbuser/.jupyter/ && \
    chown -R dbuser:dbuser /home/dbuser/.jupyter && \
    chown -R dbuser:dbuser /home/dbuser/.local/

ADD --chown=dbuser:dbuser jupyter_notebook_config.py /home/dbuser/.jupyter/

USER dbuser