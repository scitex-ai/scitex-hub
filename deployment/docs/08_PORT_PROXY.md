# 08 - Port Proxy

Access localhost services through SciTeX web interface.

## URL Pattern

```
http://localhost:8000/{username}/{project}/?port={port}
```

## Allowed Ports

10000 - 20000

## Example

```bash
# Start TensorBoard
tensorboard --logdir=./logs --port=16006

# Access via
http://localhost:8000/test-user/my-project/?port=16006
```

## Supported Services

- TensorBoard
- Jupyter
- MLflow
- Any HTTP service

## Config

`apps/project_app/utils/port_proxy.py`
