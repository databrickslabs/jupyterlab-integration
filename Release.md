# Release documentation

## Release process

- **Python package**

  - Run tests

    ```bash
    make tests
    ```

  - Commit changes

  - Bump version of databrickslabs_jupyterlab

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

  - Create distribution

    ```bash
    make dist
    ```

  - Create and tag release

    ```bash
    make release
    ```

  - Push repo and tag

    ```bash
    git push --no-verify
    git push origin --no-verify --tags
    ```

- **Labextension**

    For the time being this is a pure github provided tool and available from `npmjs.com`.

