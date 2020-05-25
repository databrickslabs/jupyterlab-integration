# Release documentation

## Release process

### 1 Tests

- On Macos set limits:

  ```bash
  $ sudo launchctl limit maxfiles 65536 200000
  ```
- On Windows one needs `OpenSSH 8` for the tests:

  ```bash
  C:\>choco install openssh

  set SSH=C:\Program Files\OpenSSH-Win64\ssh.exe
  
  C:\> cmd /c ""%SSH%"" -V
  OpenSSH_for_Windows_8.0p1, LibreSSL 2.6.5
  ``` 

  Note: This assumes that [https://chocolatey.org](https://chocolatey.org) is installed

- Copy `config-template.yaml` to `config.yaml` and edit it accordingly

- Depending on whether test should be run against AWS or Azure, set one of

  ```bash
  $ export CLOUD=aws
  $ export CLOUD=azure
  ```

  or under Windows one of

  ```cmd
  C:\>set CLOUD=aws
  C:\>set CLOUD=azure
  ```


- Start clusters

  ```bash
  python 00-create-clusters.py
  ```

  or restart clusters:

  ```bash
  python 01-restart-clusters.py
  ```

- Create secret scope and key for tests (if not already exists)

  ```bash
  python 05-create-secret-scope.py
  ```

- Execute tests
  Note: For dev tests (the current version is not published to pypi), enable `03-install-wheel_test.py`, i.e. comment the skip marks decorating the test.
  
  Execute the tests

  ```bash
  pytest -v -o log_cli=true
  ```

- Remove clusters

  ```bash
  python 99-destroy-clusters.py
  ```

### 2 Labextension

In case the jupyter labextions has been changed:

1. Commit changes

2. Bump version of *databrickslabs_jupyterlab_statusbar*

    - A new release candidate with rc0

      ```bash
      make bump_ext part=premajor|preminor|prepatch
      ```

    - A new build

      ```bash
      make bump_ext part=prerelease
      ```

    - A new release without release candidate

      ```bash
      make bump_ext version=major.minor.patch
      ```

3. Deploy to npmjs.com

    ```bash
    make upload_ext
    ```

4. Process with **Python package** since labextensions.txt is changed!

### 3 Python package

In case the jupyter labextions and/or the python code has been changed:

1. Run tests

    ```bash
    make tests
    ```

2. Clean environment

    ```bash
    make clean    # delete all temp files
    make prepare  # commit deletions
    ```

3. Bump version of databrickslabs_jupyterlab

    - A new release candidate with rc0

      ```bash
      make bump part=major|minor|patch
      ```

    - A new build

      ```bash
      make bump part=build
      ```

    - A new release

      ```bash
      make bump part=release
      ```

    - A new release without release candidate

      ```bash
      make bump part=major|minor|patch version=major.minor.patch
      ```

4. Create distribution

    ```bash
    make dist
    ```

5. Create and tag release

    ```bash
    make release
    ```

6. Deploy to pypi

    ```bash
    make upload
    ```

### 4 Docker image

1. Create docker image

    ```bash
    make docker
    ```

2. Publish image

    ```bash
    make upload_docker
    ```

### 5 Push changes

1. Push repo and tag

    ```bash
    git push --no-verify
    git push origin --no-verify --tags
    ```
