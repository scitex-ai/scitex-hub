# 05 - Apptainer

Container for user code execution.

## Build

```bash
cd deployment/singularity
sudo apptainer build scitex-user-workspace.sif scitex-user-workspace.def
```

## Run

```bash
apptainer exec scitex-user-workspace.sif python script.py
```

## With SLURM

```bash
srun apptainer exec container.sif python script.py
```

## Definition

`deployment/singularity/scitex-user-workspace.def`
