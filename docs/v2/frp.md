## Fast Reverse proxy configuration

### The tunneling service

- Create a small virtual Machine, e.g. on Amazon with Ubuntu server (docker needed). For a single user tunnel even a small `t2.nano` (2 core, 0.5 GB memory) is sufficient.
- Set the inbound security group to
    
    ```text
    Type        Protocol  Port range  Source      Description - optional
    Custom TCP  TCP       2200        0.0.0.0/0   -
    SSH         TCP         22        <HOME>/32   -
    Custom TCP  TCP       7500        <HOME>/32   -
    Custom TCP  TCP       2222        <HOME>/32   -
    ```
    
    - Port `22` is the usual port to configure the machine
    - Port `2200` is the port where the Databricks Spark driver will initiate the tunnel, hence open for all incoming connections (see token below!)
    - Port `2222` is the port where the client will open the other side of the tunnel
    - Port `7500` optional, if you want to access the fpr dashboard
    - `<HOME>` is the machine on which you work and on which later `jupyter lab` should run

- Associate an Elastic IP to the machine, e.g. `52.52.52.52`
- Download frp from [Releases](https://github.com/fatedier/frp/releases)
- Untar it and edit `frps.ini`:
    ```text
    [common]
    bind_port = 2200
    dashboard_port = 7500
    dashboard_user = admin
    dashboard_pwd = something-secret
    log_level = debug
    token = Z8YCh-some-more-chars-xnafS2
    ```
    Note the token: only clients knowing this token can now initiate a tunnel on this service

### The Databricks cluster init script.

- Create a cluster scoped initscript (use an appropriate path here) in a Databricks notebook:

    ```bash
    %fs mkdirs dbfs:/Users/you@acme.com/init
    ```

    ```bash
    dbutils.fs.put("dbfs:/Users/you@acme.com/init/frpc.sh", 
    """#!/bin/bash

    if [[ $DB_IS_DRIVER = "TRUE" ]]; then
    
        cd /usr/local
        wget -q https://github.com/fatedier/frp/releases/download/v0.34.3/frp_0.34.3_linux_amd64.tar.gz
        tar -zxvf frp_0.34.3_linux_amd64.tar.gz
        cd frp_0.34.3_linux_amd64

        cat << EOF > frpc.ini
    [common]
    server_addr = 52.52.52.52
    server_port = 2200
    token = Z8YCh-some-more-chars-xnafS2

    [ssh]
    type = tcp
    local_ip = 127.0.0.1
    local_port = 22
    remote_port = 2222
    EOF

        cat << EOF > /etc/systemd/system/frpc.service
    [Unit]
    Description=frp client
    Wants=network-online.target
    After=network.target network-online.target

    [Service]
    ExecStart=/usr/local/frp_0.34.3_linux_amd64/frpc -c /usr/local/frp_0.34.3_linux_amd64/frpc.ini

    [Install]
    WantedBy=multi-user.target
    EOF

        sudo systemctl daemon-reload && sudo systemctl start frpc.service

    fi
    """, overwrite=True)
    ```

    Note: `server_addr`, `server_port` and `token` under `[common]` need to be the same as in tunneling service config above.

- Add the init script to the cluster configuration and restart the Databricks cluster

### Usage with command line tool dj

```bash
export SSH_TUNNEL=52.52.52.52:2222
dj <profile> -k
```