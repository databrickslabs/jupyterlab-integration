@echo off
for /f "tokens=2,3 delims=:" %%a in ('conda info ^| findstr location') do (
  set CONDA_PATH=%%a:%%b
)
python %CONDA_PATH%\Scripts\databrickslabs-jupyterlab %*