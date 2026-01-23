# Apptainer (Singularity)

User code execution container.

## Build

```bash
cd deployment/singularity
sudo apptainer build scitex-user-workspace.sif scitex-user-workspace.def
```

## Test

```bash
apptainer exec scitex-user-workspace.sif python --version
```

## Run User Code

```bash
apptainer exec \
    --contain \
    --cleanenv \
    --bind /workspace:/workspace \
    scitex-user-workspace.sif \
    python /workspace/script.py
```

## With SLURM

```bash
srun apptainer exec scitex-user-workspace.sif python script.py
```
