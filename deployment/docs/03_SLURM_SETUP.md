# 03 - SLURM Setup

Host runs SLURM. Docker connects to it.

## Install (once)

```bash
cd deployment/slurm
sudo ./install-host.sh
make env=dev rebuild
```

## Fix Problems

```bash
sudo ./deployment/slurm/fix.sh
```

## Check Status

```bash
make env=dev status
```

## Files

```
deployment/slurm/
├── install-host.sh     # Install
├── fix.sh              # Fix problems
└── slurm-docker.conf   # Auto-generated
```
