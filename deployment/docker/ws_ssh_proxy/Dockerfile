# WebSocket to SSH Proxy
# Bridges WebSocket connections to SSH gateway for external SSH access

FROM alpine:latest

# Install websocat
RUN apk add --no-cache curl \
    && WEBSOCAT_VERSION=1.13.0 \
    && curl -L -o /usr/local/bin/websocat \
        "https://github.com/vi/websocat/releases/download/v${WEBSOCAT_VERSION}/websocat.x86_64-unknown-linux-musl" \
    && chmod +x /usr/local/bin/websocat \
    && apk del curl

# Non-root user for security
RUN adduser -D -u 1000 wsproxy
USER wsproxy

EXPOSE 8022

# Bridge WebSocket to SSH gateway
# --binary: Binary mode for SSH protocol
# ws-l: WebSocket listen
# tcp: Forward to TCP (SSH)
CMD ["websocat", "--binary", "-E", "ws-l:0.0.0.0:8022", "tcp:django:2200"]
