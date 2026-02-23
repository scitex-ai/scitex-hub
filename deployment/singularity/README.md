# Apptainer (Singularity)

User code execution container.

## Build

```bash
cd deployment/singularity
sudo apptainer build scitex-cloud-shared-v0.1.0.sif scitex-cloud-shared-v0.1.0.def
```

## Test

```bash
apptainer exec scitex-cloud-shared-v0.1.0.sif python --version
```

## Run User Code

```bash
apptainer exec \
    --contain \
    --cleanenv \
    --bind /workspace:/workspace \
    scitex-cloud-shared-v0.1.0.sif \
    python /workspace/script.py
```

## With SLURM

```bash
srun apptainer exec scitex-cloud-shared-v0.1.0.sif python script.py
```
