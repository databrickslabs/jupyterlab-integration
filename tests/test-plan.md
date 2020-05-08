## MacOS

- **Installation**

  ```text
                       M W
  Installation         Y _
  Bootstrap  (dj -b)   Y _
  SSH config (dj -s)   Y _
  ```

- **Infos**

  ```text
                              M W
  Show profiles     (dj -p)   Y _
  Show version      (dj -v)   Y _
  Library version   (dj -V)   Y _
  Show blacklist    (dj -B)   Y _
  Show whitelist    (dj -W)   Y _
  Download notebook (dj -n)   Y _
  ```

- **Kernel Specification AWS**

  - **DBRs**

    ```text
                                       5.5  5.5ML  6.3  6.3ML  6.5  6.5ML  7.0  7.0ML
                                       M W   M W   M W   M W   M W   M W   M W   M W
    ```

  - **Create Kernel Specification**

    ```text
    dj profile -k                      Y _   Y _   Y _    Y _  Y _   Y _   Y _   Y _
    dj profile -k -D                   Y _   Y _   Y _    Y _  Y _   Y _   Y _   Y _
    dj profile -k -N                   Y _   Y _   Y _    Y _  Y _   Y _   Y _   Y _
    dj profile -k -i CLUSTER_ID        Y _   Y _   Y _    Y _  Y _   Y _   Y _   Y _
    ```

  - **Mirror environment**

    ```text
    dj -m                              ___   ___   ___   ___   ___   ___   ___   ___
    ```

  - **Reconfigure Kernel**

    ```text
    dj profile -r -i CLUSTER_ID        Y _   Y _   Y _   Y _   Y _   Y _   Y _   Y _
    ```

- **Kernel Specification Azure**

  - **Create Kernel Specification**

    ```text
    dj profile -k -o ORG_ID            Y _   Y _   Y _   Y _   Y _   Y _   Y _   Y _
    dj profile-new -k -i CLUSTER_ID    Y _   Y _   Y _   Y _   Y _   Y _   Y _   Y _
    dj profile-new -r -i CLUSTER_ID    Y _   Y _   Y _   Y _   Y _   Y _   Y _   Y _
    dj profile-new -k                  Y _   Y _   Y _   Y _   Y _   Y _   Y _   Y _
    dj profile-new -k -D               Y _   Y _   Y _   Y _   Y _   Y _   Y _   Y _
    dj profile-new -k -N               Y _   Y _   Y _   Y _   Y _   Y _   Y _   Y _
    ```

  - **Mirror environment**

    ```text
    dj -m                              ___   ___   ___   ___   ___   ___   ___   ___
    ```

  - **Reconfigure Kernel**

    ```text
    dj profile -r -i CLUSTER_ID        Y _   Y _   Y _   Y _   Y _   Y _   Y _   Y _
    ```

- **Delete Kernel Specification**

    ```text
           M W
    dj -d  Y _
    ```
