# syntax=docker/dockerfile:1.4
# ============================================
# SciTeX Cloud - Development Image
# ============================================
# Optimized for cache efficiency and fast rebuilds

FROM python:3.11-slim

LABEL maintainer="ywatanabe@scitex.ai"
LABEL description="SciTeX Cloud - Development Environment"

# ============================================
# Environment Variables
# ============================================
# Set first - rarely changes

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=0 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# ============================================
# System Dependencies
# ============================================
# Ordered by update frequency (least to most)
# Large, stable packages first for maximum cache reuse

RUN apt-get update && apt-get install -y --no-install-recommends \
    # Core build tools (rarely change)
    build-essential \
    git \
    wget \
    curl \
    unzip \
    netcat-openbsd \
    openssh-client \
    jq \
    cron \
    # Useful CLI tools for development
    tree \
    htop \
    vim \
    nano \
    # Database (rarely change)
    libpq-dev \
    # LaTeX suite (large, rarely change - install early for caching)
    # Writer Dependencies
    texlive-latex-base \
    texlive-latex-extra \
    texlive-latex-recommended \
    texlive-fonts-recommended \
    texlive-fonts-extra \
    texlive-science \
    texlive-publishers \
    texlive-luatex \
    texlive-xetex \
    texlive-bibtex-extra \
    texlive-pictures \
    texlive-plain-generic \
    texlive-lang-european \
    texlive-lang-english \
    texlive-extra-utils \
    latexdiff \
    latexmk \
    chktex \
    ghostscript \
    poppler-utils \
    # Document conversion (markdown to PDF)
    pandoc \
    perl \
    parallel \
    # Image processing
    imagemagick \
    # Browser automation dependencies
    chromium \
    chromium-driver \
    fonts-liberation \
    # Microsoft core fonts (Arial, Times New Roman, etc.) for scientific figures
    fontconfig \
    # Playwright runtime dependencies
    libglib2.0-0t64 \
    libnspr4 \
    libnss3 \
    libdbus-1-3 \
    libatk1.0-0t64 \
    libatk-bridge2.0-0t64 \
    libcups2t64 \
    libxcb1 \
    libxkbcommon0 \
    libatspi2.0-0t64 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libcairo2 \
    libpango-1.0-0 \
    libasound2t64 \
    python3-bibtexparser \
    # Munge for SLURM authentication
    munge \
    && rm -rf /var/lib/apt/lists/*

# Install Microsoft core fonts (Arial, Times New Roman, Courier New, etc.)
# Required for high-quality scientific figures
# ttf-mscorefonts-installer requires contrib repository in Debian
RUN sed -i 's/main/main contrib/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && echo -e "ttf-mscorefonts-installer msttcorefonts/accepted-mscorefonts-eula select true" | debconf-set-selections \
    && apt-get install -y --no-install-recommends ttf-mscorefonts-installer \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

# ============================================
# SLURM Client (build from source to match host version)
# ============================================
# MUST match host SLURM version exactly for munge auth to work
# Host version: 24.05.5 - check with: sinfo --version
ARG SLURM_VERSION=24.05.5
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmunge-dev \
    libhwloc-dev \
    libhttp-parser-dev \
    libjson-c-dev \
    liblz4-dev \
    libyaml-dev \
    && rm -rf /var/lib/apt/lists/* \
    && curl -L -o /tmp/slurm-${SLURM_VERSION}.tar.bz2 \
        "https://download.schedmd.com/slurm/slurm-${SLURM_VERSION}.tar.bz2" \
    && cd /tmp && tar xjf slurm-${SLURM_VERSION}.tar.bz2 \
    && cd slurm-${SLURM_VERSION} \
    && ./configure --prefix=/usr --sysconfdir=/etc/slurm \
    && make -j$(nproc) \
    && make install \
    && cd / && rm -rf /tmp/slurm-* \
    && useradd -r -s /bin/false slurm

# ============================================
# Tool Installation
# ============================================
# Install external tools - cached unless versions change

# Install uv (fast package manager) — pinned version for reproducibility
ENV UV_VERSION=0.9.28
RUN curl -LsSf "https://github.com/astral-sh/uv/releases/download/${UV_VERSION}/uv-x86_64-unknown-linux-musl.tar.gz" \
        -o /tmp/uv.tar.gz \
    && tar -xzf /tmp/uv.tar.gz -C /tmp \
    && mv /tmp/uv-x86_64-unknown-linux-musl/uv /usr/local/bin/uv \
    && mv /tmp/uv-x86_64-unknown-linux-musl/uvx /usr/local/bin/uvx \
    && chmod 755 /usr/local/bin/uv /usr/local/bin/uvx \
    && rm -rf /tmp/uv.tar.gz /tmp/uv-x86_64-unknown-linux-musl \
    && uv --version

# Install yq (YAML parser for scitex.writer)
RUN YQ_VERSION=v4.44.3 && \
    YQ_BINARY=yq_linux_amd64 && \
    wget https://github.com/mikefarah/yq/releases/download/${YQ_VERSION}/${YQ_BINARY} -O /usr/local/bin/yq && \
    chmod +x /usr/local/bin/yq

# Install inotify-tools (lightweight file watcher for template hot reload)
RUN apt-get update && apt-get install -y --no-install-recommends inotify-tools && rm -rf /var/lib/apt/lists/*

# ============================================
# Whisper.cpp (Speech-to-Text)
# ============================================
# Baked into the image for consistency across dev / staging / production.
# cmake + ffmpeg are the only build-time additions; no runtime host dependency.
# Binary: /opt/whisper/bin/whisper-cli   Model: /opt/whisper/models/ggml-base.en.bin
ENV WHISPER_CLI=/opt/whisper/bin/whisper-cli \
    WHISPER_MODEL=/opt/whisper/models/ggml-base.en.bin
RUN apt-get update && apt-get install -y --no-install-recommends cmake ffmpeg \
    && rm -rf /var/lib/apt/lists/* \
    && git clone --depth 1 https://github.com/ggerganov/whisper.cpp.git /tmp/whisper.cpp \
    && cmake -S /tmp/whisper.cpp -B /tmp/whisper-build \
        -DCMAKE_BUILD_TYPE=Release \
        -DWHISPER_BUILD_SERVER=OFF \
        -DWHISPER_BUILD_EXAMPLES=ON \
        -DBUILD_SHARED_LIBS=OFF \
    && cmake --build /tmp/whisper-build --target whisper-cli -j$(nproc) \
    && mkdir -p /opt/whisper/bin /opt/whisper/models \
    && cp /tmp/whisper-build/bin/whisper-cli /opt/whisper/bin/whisper-cli \
    && wget -q -O /opt/whisper/models/ggml-tiny.en.bin \
        "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.en.bin" \
    && wget -q -O /opt/whisper/models/ggml-base.en.bin \
        "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.en.bin" \
    && rm -rf /tmp/whisper.cpp /tmp/whisper-build

# ============================================
# Apptainer/Singularity Installation
# ============================================
# Required for secure user terminal sessions (PTY runs inside container)
# Same architecture as production HPC environment
# Install from GitHub releases (works on Debian slim)
RUN APPTAINER_VERSION=1.3.4 && \
    apt-get update && apt-get install -y --no-install-recommends \
        uidmap \
        squashfs-tools \
        fuse2fs \
        fuse-overlayfs \
        libfuse3-dev \
        libseccomp2 \
        fakeroot \
        equivs \
    && rm -rf /var/lib/apt/lists/* \
    && curl -L -o /tmp/apptainer.deb \
        "https://github.com/apptainer/apptainer/releases/download/v${APPTAINER_VERSION}/apptainer_${APPTAINER_VERSION}_amd64.deb" \
    && echo -e "Creating libfuse3-3 compatibility package..." \
    && printf "Section: misc\nPriority: optional\nStandards-Version: 3.9.2\nPackage: libfuse3-3\nVersion: 3.17.2\nProvides: libfuse3-3\nDepends: libfuse3-4\nDescription: Compatibility package for libfuse3-3\n This is a transitional package for Debian Trixie.\n" > /tmp/libfuse3-3-compat \
    && equivs-build /tmp/libfuse3-3-compat \
    && dpkg -i libfuse3-3_3.17.2_all.deb \
    && rm libfuse3-3_3.17.2_all.deb /tmp/libfuse3-3-compat \
    && dpkg -i /tmp/apptainer.deb \
    && rm /tmp/apptainer.deb \
    && apptainer --version

# Install Node.js, Mermaid CLI, and TypeScript tools
RUN curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g @mermaid-js/mermaid-cli typescript && \
    rm -rf /var/lib/apt/lists/*

# Configure ImageMagick (remove PDF security restrictions)
RUN if [ -f /etc/ImageMagick-6/policy.xml ]; then \
        sed -i 's/<policy domain="coder" rights="none" pattern="PDF" \/>/<policy domain="coder" rights="read|write" pattern="PDF" \/>/g' /etc/ImageMagick-6/policy.xml; \
    elif [ -f /etc/ImageMagick-7/policy.xml ]; then \
        sed -i 's/<policy domain="coder" rights="none" pattern="PDF" \/>/<policy domain="coder" rights="read|write" pattern="PDF" \/>/g' /etc/ImageMagick-7/policy.xml; \
    else \
        echo -e "⚠️  ImageMagick policy.xml not found, skipping PDF policy update"; \
    fi

# ============================================
# Python Dependencies
# ============================================
# Copy pyproject.toml and src/ for dependency installation (cached layer)

# Copy project definition and minimal source for package install
COPY pyproject.toml ./
COPY src/ ./src/

# Install SciTeX Cloud Python dependencies with cache mount
# scitex is NOT installed here for dev — entrypoint.sh installs it in editable+upgrade
# mode from the mounted /scitex-python volume at container startup (-eU).
# This avoids sktime==0.8.1 build failures from PyPI while keeping deps fresh.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --system ".[django,test]"

# Install Playwright browsers (must persist in image for runtime use)
# Note: We already have chromium and dependencies installed above,
# so we skip install-deps which tries to install Ubuntu packages on Debian
RUN python -m playwright install chromium

# ============================================
# Node.js Dependencies
# ============================================
# Install Node dependencies BEFORE copying application code for better caching
# This layer is only invalidated when package.json/package-lock.json changes

COPY package.json package-lock.json* ./
RUN npm install

# ============================================
# Application Code
# ============================================
# Copy application last - changes most frequently

# Copy application code
COPY . .

# Copy dev-specific entrypoint and helper scripts
COPY deployment/docker/docker_dev/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && \
    chmod +x /app/deployment/docker/docker_dev/watch_templates.sh 2>/dev/null || true

# Create directories
RUN mkdir -p staticfiles media logs run .cache/containers

# ============================================
# Verification
# ============================================
# Verify installations - fails fast if something is wrong

RUN pdflatex --version && \
    bibtex --version && \
    latexdiff --version && \
    convert --version && \
    mmdc --version && \
    yq --version && \
    which srun && \
    echo -e "✅ All scitex.writer dependencies verified (SLURM client installed, config at runtime)"

# ============================================
# Runtime Configuration
# ============================================

HEALTHCHECK --interval=10s --timeout=3s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
# Use Daphne (ASGI server) for WebSocket support (PTY terminal, collaborative editing, etc.)
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]

# EOF
