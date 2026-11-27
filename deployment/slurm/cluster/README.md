# SciTeX SLURM cluster -- runbook

Built 2026-09-14 (card infra-slurm-cluster-login-01-compute-02-04-20260914). Slurm 23.11.4 (Ubuntu 24.04 packages), munge 0.5.15.

**This directory is the canonical copy** of the cluster config. The live copy of this runbook is
`/etc/scitex/slurm-README.md` on scitex-compute-01; `etc/` mirrors compute-01's `/etc/slurm/`
(`slurmdbd.conf` only as a password-free template). Edit here, then deploy:

    # on scitex-compute-01, from a checkout of this repo
    sudo install -m 0644 deployment/slurm/cluster/etc/{slurm,cgroup,gres}.conf /etc/slurm/
    sudo install -m 0644 deployment/slurm/cluster/README.md /etc/scitex/slurm-README.md
    sudo scontrol reconfigure                    # pushes to every configless worker
    # every node (controller: all five units; worker: munge + slurmd)
    sudo deployment/host-setup/systemd/install-slurm-resilience.sh
    # accounting host only: the loud health check + 10-minute timer
    sudo deployment/host-setup/systemd/install-slurm-accounting-check.sh

Drift check: `sha256sum /etc/slurm/slurm.conf deployment/slurm/cluster/etc/slurm.conf` must match.

## Incident 2026-10-02 .. 2026-11-26: accounting down for 8 weeks

- compute-01 rebooted 2026-10-02; slurmctld and slurmdbd started before the LAN address resolved, hit
  `fatal: slurm_init_msg_engine_port error Address family not supported by protocol` and stayed `failed`
  (stock units have no `Restart=`). MariaDB later exited (2026-10-23) and also stayed down.
- compute-02's root disk was migrated (~2026-10-03) without `/var/log/munge`, `/var/lib/slurm`, `/var/log/slurm`:
  munge and slurmd could not start.
- compute-03's slurmd exited when it booted while the controller was down; `/etc/slurm/slurm.conf` there was an
  empty directory (see gotchas), so host clients failed with "ClusterName needs to be specified".
- Every health check exited 0. sacct had recorded jobs only up to 2026-09.

Fixed 2026-11-27: `*-resilience.conf` drop-ins (restart forever, order after network/name resolution, recreate
missing dirs) on every node; `AccountingStoreFlags=job_comment` + `TrackWCKey=yes` (slurm.conf and slurmdbd.conf)
so `--comment`/`--wckey` (the project tag) reach sacct; `scitex-slurm-accounting-check.timer` fails loudly.

| node | role | CPUs | RAM (RealMemory) | GPU | NodeAddr |
|---|---|---|---|---|---|
| scitex-compute-01 | slurmctld + login + slurmd (Weight=100, 2 cores + 8 GiB reserved for logins) | 12 | 31000 | - | 192.168.11.171 |
| scitex-compute-02 | slurmd | 32 | 39000 | - | 192.168.11.172 |
| scitex-compute-03 | slurmd | 32 | 63000 | gtx1070:1 | 192.168.11.173 |
| scitex-compute-04 | slurmd | 32 | 94000 | gtx1070:1 | 192.168.11.174 |

Partition `compute` (default, MaxTime=INFINITE, DefMemPerCPU=2048).

## Files
- `/etc/slurm/{slurm,gres,cgroup}.conf` on compute-01 ONLY. Workers are configless: `/etc/default/slurmd` has
  `SLURMD_OPTIONS="--conf-server 192.168.11.171:6817"`; their cached copy is `/run/slurm/conf/`.
- `/etc/munge/munge.key` (0400 munge:munge) -- same key on every node; master copy on compute-01.
- Logs: `/var/log/slurm/slurmctld.log`, `/var/log/slurm/slurmd.log`, `/var/log/slurm/slurmdbd.log`, job completions `/var/log/slurm/jobcomp.log` (compute-01).
- Accounting: slurmdbd (port 6819) + MariaDB `slurm_acct_db` on compute-01 (bound to 127.0.0.1). `/etc/slurm/slurmdbd.conf` is 0600 slurm:slurm and
  holds the DB password -- never cat it. AccountingStorageTRES adds gres/gpu. Jobs on ALL nodes (01 included) are billed.
  sacctmgr: cluster `scitex`, account `scitex`; add each new user: `sudo sacctmgr -i add user <u> DefaultAccount=scitex`.
- System users with FIXED ids on every node: slurm 64030, munge 64031 (create these before installing packages on a new node).
- Backups of the pre-install state: `/root/backup-slurm-<ts>/` on each node; `slurm.conf.bak-*` next to slurm.conf.
- Login-node metering: `/etc/systemd/system/user-.slice.d/40-scitex-accounting.conf` (applied).
  Proposed per-user caps: `/etc/scitex/50-scitex-limits.conf.proposed` (NOT applied).

## Health
    sinfo -N -o '%N %t %c %m %w %G %E'
    scontrol show node scitex-compute-02
    srun -N4 hostname
    munge -n | ssh scitex-compute-02 unmunge     # key check
    scitex-check-slurm-accounting                # exit 1 + daemon.crit log when jobs would not be metered
    systemctl status scitex-slurm-accounting-check.timer   # runs it every 10 min (compute-01)

## Billing / metering
    # per-user CPU / GPU / mem allocation (billable) for jobs on every node
    sacct -a -X -S 2026-09-01 -o JobID,User,NodeList,AllocTRES%50,Elapsed,State --parsable2
    # measured usage per step
    sacct -a -S 2026-09-01 -o JobID,User,TRESUsageInTot%60 --parsable2
    # per-project attribution: the Hub tags jobs --comment=project:<id> --wckey=p<id>
    sacct -a -X -P -S 2026-11-01 -o JobID,User,Account,WCKey,Comment,Elapsed,TotalCPU,AllocTRES
    sreport -t hours cluster UserUtilizationByAccount start=2026-09-01
    # direct login-node usage on compute-01 (outside Slurm): per-user systemd slice counters
    systemctl show user-<uid>.slice -p CPUUsageNSec -p MemoryCurrent -p IOReadBytes -p IOWriteBytes
Billable = sum over jobs of AllocTRES x Elapsed (cpu-seconds, gpu-seconds, GB-seconds) + login-node slice CPU deltas.
Slice counters reset when a user's last session ends, so sample every 60 s and bill deltas.

## Restart
    # controller (compute-01); running jobs survive
    sudo systemctl restart slurmctld
    # after editing slurm.conf / gres.conf / cgroup.conf: push to all slurmds (configless)
    sudo scontrol reconfigure
    # a worker
    ssh scitex-compute-0N sudo systemctl restart slurmd
    # node-list or port changes need slurmctld restart AND every slurmd restarted

## Drain / resume
    sudo scontrol update NodeName=scitex-compute-03 State=DRAIN Reason='maintenance <who> <why>'
    squeue -w scitex-compute-03            # wait until empty (DRAINED)
    sudo scontrol update NodeName=scitex-compute-03 State=RESUME

## Add a node (e.g. scitex-compute-05, Ubuntu 24.04)
1. `sudo groupadd -r -g 64031 munge && sudo useradd -r -u 64031 -g munge -d /nonexistent -s /usr/sbin/nologin munge`
   `sudo groupadd -r -g 64030 slurm && sudo useradd -r -u 64030 -g slurm -d /nonexistent -s /usr/sbin/nologin slurm`
2. `sudo apt-get install -y munge slurmd slurm-client` (same 23.11 series as the controller).
3. Copy the key without printing it:
   `ssh scitex-compute-01 sudo cat /etc/munge/munge.key | ssh scitex-compute-05 'sudo install -o munge -g munge -m0400 /dev/stdin /etc/munge/munge.key'`
   then `sudo systemctl restart munge`.
4. `echo 'SLURMD_OPTIONS="--conf-server 192.168.11.171:6817"' | sudo tee /etc/default/slurmd`
5. Run `slurmd -C` on the new node; add a `NodeName=... NodeAddr=<LAN IP> ... Weight=10` line (RealMemory ~2% below the
   reported value; `Gres=gpu:<type>:N` + a gres.conf line if it has GPUs) and add it to the partition `Nodes=`.
6. On compute-01: `sudo systemctl restart slurmctld`; then restart slurmd on EVERY node; then `sudo systemctl enable --now slurmd` on the new one.
7. User accounts (same uid/gid as on the login node) must exist on the new node before user jobs can run there.

## Notes / gotchas
- /etc/hosts on 01/03/04 maps scitex-compute-0N to tailnet 100.64.x addresses; slurm uses the LAN NodeAddr explicitly.
- Without slurmdbd, the main scheduler held new batch jobs as PENDING(InvalidAccount) until backfill ran (~30 s). With slurmdbd, jobs start within 2-4 s.
- A worker that hosts Hub containers (compute-03) MUST have `/etc/slurm/slurm.conf` as a regular FILE: the Hub
  compose files bind-mount it, and when the host path is missing Docker creates an EMPTY DIRECTORY there
  (compute-03, 2026-08-20) that breaks every host SLURM client, or a recreate of the container fails outright
  (2026-11-26: removing the empty dir took the hub-dev celery containers down for minutes). Before touching any
  host path, list every container that binds it: `docker ps -aq | xargs docker inspect -f '{{.Name}} {{.Mounts}}'`.
  The file must never go stale either (host clients read it before the configless cache), so it is kept equal to
  `/run/slurm/conf/` by the mirror, which rewrites the files in place on every cache refresh (enabled on
  compute-03 2026-11-27; backup of the old empty dir: `/root/backup-slurm-slurmconf-dir-20261126T204941Z/`):

      sudo install -m 0644 deployment/host-setup/systemd/scitex-slurm-conf-mirror.{path,service} /etc/systemd/system/
      sudo systemctl daemon-reload && sudo systemctl enable --now scitex-slurm-conf-mirror.path
      sudo systemctl start scitex-slurm-conf-mirror.service

  and then RECREATE the container (`docker compose up -d --force-recreate <service>`): a container created over
  the directory cannot restart onto a file.
- Jobs shorter than `JobAcctGatherFrequency` (30 s) can under-report MaxRSS (sampled at the end only);
  AllocTRES x Elapsed (the billable quantity) is exact.
- Ubuntu's 23.11 build ships no gpu_nvml plugin, so GPUs are static in gres.conf (File=/dev/nvidia0).
- Root can submit on a user's behalf: `sudo sbatch --uid=<uid> --gid=<gid> ...` (job runs as that uid). Plain root submissions run as root.

## Compute-side isolation design (operator decision 2026-09-14; NOT yet implemented)
- One shared SSHFS NAS account is fine. Today the NAS mounts are `fuse.sshfs allow_other` without `default_permissions`, and
  nas-01/nas-02 roots are 0777: ANY local uid can read and write ALL data. Harmless while ywatanabe is the only user; must be
  closed before ordinary user accounts exist on these nodes.
- Gate: remount the NAS under a root-owned 0750 parent (e.g. /mnt/nas/scitex-nas-0N, group `scitex-storage` = root + service
  accounts) and point /storage/{warm,cool,cold} there. Ordinary users are not in the group, so they cannot traverse.
- Each user maps to exactly one directory `/storage/cool/users/<user>`. A job's Apptainer container runs with `--containall`
  and binds ONLY that directory (as $HOME) plus a per-job /scratch dir; the bind is set up by a root-run prolog
  (or by the hub's root submitter) so the user never needs a path into /storage.
- Public projects: bound read-only (`--bind src:dst:ro`); cloning goes through the Git service, never the filesystem.
- Staging: prolog copies inputs /storage/cool/users/<user> -> /scratch/jobs/<jobid> (0700 user), epilog copies results back
  and removes the job dir.
