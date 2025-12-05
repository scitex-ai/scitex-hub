# Port Proxy Feature

## Overview

The port proxy feature allows users to access services running on localhost ports through the SciTeX Cloud web interface. This enables seamless integration of development tools like TensorBoard, Jupyter notebooks, MLflow, and other HTTP-based services without requiring additional port forwarding or network configuration.

## Usage

### Accessing a Service

To access a service running on a specific port:

```
http://localhost:8000/{username}/{project}/?port={port_number}
```

**Example:**
```
http://localhost:8000/test-user/my-project/?port=16006
```

### Port Range

For security reasons, only ports in the range **10000-20000** are allowed.

Attempting to access ports outside this range will result in an error message.

### Starting Your Service

Users must manually start their services on an allowed port. Here are common examples:

#### TensorBoard
```bash
tensorboard --logdir=./logs --port=16006 --bind_all
```

#### Jupyter Notebook
```bash
jupyter notebook --port=15888 --ip=127.0.0.1 --no-browser
```

#### Python HTTP Server (for testing)
```bash
python3 -m http.server 15000
```

#### MLflow UI
```bash
mlflow ui --port=15555 --host=127.0.0.1
```

#### Custom Flask/FastAPI Applications
```python
# Flask
app.run(host='127.0.0.1', port=15000)

# FastAPI
uvicorn main:app --host 127.0.0.1 --port 15000
```

## Technical Details

### How It Works

1. User accesses `/{username}/{project}/?port=XXXXX`
2. Django's `project_detail` view detects the `port` parameter
3. Request is passed to `PortProxyManager`
4. Port is validated (must be in 10000-20000 range)
5. HTTP request is proxied to `http://127.0.0.1:XXXXX{request_path}`
6. Response is streamed back to the user's browser

### Security Considerations

- **Port Range Restriction**: Only ports 10000-20000 are accessible to prevent access to system services
- **Project Access Control**: Users must have view access to the project to use the proxy (enforced by `@project_access_required` decorator)
- **Localhost Only**: Proxy only connects to 127.0.0.1, not external hosts
- **Same Request Method**: Proxy forwards the same HTTP method (GET, POST, etc.) as the original request

### Supported Features

- ✅ All HTTP methods (GET, POST, PUT, DELETE, PATCH, etc.)
- ✅ Streaming responses (for real-time data like TensorBoard)
- ✅ Request/response headers forwarding
- ✅ Query parameters (except `port` which is stripped)
- ✅ POST data and request body
- ✅ WebSocket support (for services that use it)
- ✅ Redirects (followed automatically)

### Error Handling

The proxy provides clear error messages for common issues:

#### Service Not Running
```
Failed to connect to service on port 15000.
Is the service running? Try: python3 -m http.server 15000
```

#### Port Out of Range
```
Port 5000 is outside allowed range (10000-20000)
```

#### Invalid Port Parameter
```
Invalid port parameter: abc
```

## Troubleshooting

### "Failed to connect to service"

**Cause:** The service is not running on the specified port.

**Solution:**
1. Start your service on the port you're trying to access
2. Verify the service is running: `curl http://127.0.0.1:{port}`
3. Check that the service is bound to 127.0.0.1 or 0.0.0.0

### "Port X is outside allowed range"

**Cause:** You're trying to access a port outside 10000-20000.

**Solution:** Start your service on a port within the allowed range (10000-20000).

### "404 Not Found" from the service

**Cause:** The service received the request but the path doesn't exist.

**Solution:** The proxy forwards the full request path. Some services may need path configuration:
- TensorBoard: Use `--path_prefix=/` if needed
- Jupyter: Use `--NotebookApp.base_url=/` if needed

## Implementation Details

### File Locations

- **Proxy Manager**: `apps/project_app/utils/port_proxy.py`
- **View Integration**: `apps/project_app/views/project_views.py` (lines 179-201)
- **URL Pattern**: Uses existing `/{username}/{project}/` route with `?port=` parameter

### Configuration

Currently, the port range is hardcoded in `PortProxyManager`:

```python
MIN_PORT = 10000
MAX_PORT = 20000
```

To change the allowed port range, modify these constants in `apps/project_app/utils/port_proxy.py`.

## Future Enhancements

Potential improvements (not currently implemented):

- [ ] UI to show running services/ports
- [ ] Service health checks
- [ ] Port reservation/allocation system
- [ ] WebSocket proxy improvements
- [ ] Configurable port ranges per user/project
- [ ] Service templates (one-click TensorBoard, Jupyter, etc.)

## Related Documentation

- Project Access Control: See `apps/project_app/decorators.py`
- Project Views: See `apps/project_app/views/project_views.py`
- User Workspaces: See workspace documentation for how services run in user environments
