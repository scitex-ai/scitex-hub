<!-- ---
!-- Timestamp: 2025-11-27 05:19:51
!-- Author: ywatanabe
!-- File: /ssh:ug:/home/ywatanabe/proj/scitex-cloud/deployment/slurm/README.md
!-- --- -->

# SLURM

Host runs SLURM. Docker connects to it.

## Install (once)

```bash
sudo ./install-host.sh
make env=dev rebuild
```

## Fix Problems

```bash
sudo ./fix.sh
```

## Check Status

```bash
make env=dev status
```

# Fix host config

``` bash
sed -i 's/SlurmctldHost=DXP480TPLUS-994/SlurmctldHost=host.docker.internal/' slurm-docker-nas.conf
```



# Restart SLURM
``` bash
sudo systemctl restart slurmctld slurmd
sleep 2
sudo scontrol update nodename=DXP480TPLUS-994 state=idle
```

<!-- EOF -->