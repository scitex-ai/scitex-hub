# 05 - Apptainer

Container for user code execution.

## Build

```bash
cd deployment/singularity
sudo apptainer build scitex-cloud-shared-v0.1.0.sif scitex-cloud-shared-v0.1.0.def
```

## Run

```bash
apptainer exec scitex-cloud-shared-v0.1.0.sif python script.py
```

## With SLURM

```bash
srun apptainer exec container.sif python script.py
```

## Definition

`deployment/singularity/scitex-cloud-shared-v0.1.0.def`
