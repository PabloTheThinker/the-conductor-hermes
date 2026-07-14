# Dockerfile for Ilo Prime Crucible Environment
#
# This is the minimal, hardened base image used for ephemeral Crucible containers.
# It contains only what is needed for deep simulation, self-cloning, and trace recording.
#
# Production notes:
# - Run as non-root
# - Read-only root filesystem (overridden only for /tmp)
# - No unnecessary packages
# - Future: add seccomp profile, AppArmor, and minimal LLM client libs only

FROM python:3.11-slim-bookworm

LABEL maintainer="Ilo Prime Engineering"
LABEL description="Ephemeral sandbox for Ilo Prime Noesis / Crucible self-simulation"

# Create non-root user
RUN groupadd -r crucible && useradd -r -g crucible crucible

# Install only essential runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy runtime bootstrap and minimal dependencies
# In a real build you would COPY the actual crucible_runtime package
COPY crucible_runtime/ /app/crucible_runtime/
COPY requirements-crucible.txt /app/

RUN pip install --no-cache-dir -r /app/requirements-crucible.txt

# Switch to non-root user
USER crucible

# Default entrypoint — the Crucible runtime bootstrap
ENTRYPOINT ["python", "-m", "crucible_runtime.bootstrap"]

# Healthcheck (optional but recommended for production)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys; sys.exit(0)" || exit 1

# Default command can be overridden by CrucibleManager
CMD ["--max-duration", "45"]