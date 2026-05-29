# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# System deps: git to fetch Trails from source, curl for the healthcheck,
# ca-certificates + libssl for pyoxigraph's TLS.
RUN apt-get update && apt-get install -y --no-install-recommends \
    git curl libssl-dev ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Trails from the framework repo. The `trails` package lives in the
# `python/` subdirectory; the build backend is setuptools (pure Python — the
# kernel falls back to the pyoxigraph `_pybackend` store, so no Rust toolchain
# is needed).
#
# Two source paths:
#   1. Private mirror — set ``TRAILS_GIT_URL`` to a full ``git+https://…``
#      URL (without the ``oauth2:TOKEN@`` prefix; the build wires the
#      token in via the BuildKit secret named ``git_token``). The host,
#      org and repo path are deployment-specific and live OUT of this
#      file. Set TRAILS_GIT_URL and the ``git_token`` secret together; a
#      token alone with no URL falls back to the public mirror.
#   2. Public mirror at TRAILS_PUBLIC_REF (default github.com/XORwell/trails).
#      Used when neither TRAILS_GIT_URL nor the secret is provided.
#
# BuildKit secret usage (host-agnostic; the URL is provided at build time):
#
#       DOCKER_BUILDKIT=1 docker build \
#           --build-arg TRAILS_GIT_URL="git+https://YOUR.HOST/path/to/framework.trails.git" \
#           --secret id=git_token,src=<(printf %s "$GIT_TOKEN") -t word-drift-on-trails .
#
# TRAILS_PIN is the exact git commit / tag / branch that word-drift is built
# against. It MUST match the range declared in trails_compat.py. The runtime
# check in trails_compat.enforce() refuses to start the app in production if
# these drift apart, so an ops error here is loud and fail-fast.
ARG TRAILS_PIN=0f33c59
ARG TRAILS_GIT_URL=
ARG TRAILS_PUBLIC_REF=git+https://github.com/XORwell/trails.git@${TRAILS_PIN}#subdirectory=python
RUN --mount=type=secret,id=git_token \
    TOKEN="$(cat /run/secrets/git_token 2>/dev/null || true)"; \
    if [ -n "$TOKEN" ] && [ -n "${TRAILS_GIT_URL}" ]; then \
        # Pre-clone with full history so pip's checkout of an arbitrary
        # commit SHA succeeds (pip's git+https path uses a shallow clone
        # that breaks `git checkout <commit-on-non-tip>`). Install from the
        # local checkout's python/ subdir. Strip the leading "git+" so the
        # remainder is a plain git URL we can hand to `git clone`.
        TRAILS_CLONE_URL="${TRAILS_GIT_URL#git+}"; \
        TRAILS_CLONE_URL="$(echo "${TRAILS_CLONE_URL}" | sed -E "s#^(https?://)#\1oauth2:${TOKEN}@#")"; \
        git clone --depth 50 "${TRAILS_CLONE_URL}" /tmp/trails-src && \
        cd /tmp/trails-src && git checkout -q "${TRAILS_PIN}" && \
        pip install --no-cache-dir "trails[http] @ file:///tmp/trails-src/python" && \
        cd / && rm -rf /tmp/trails-src; \
    else \
        pip install --no-cache-dir "trails[http] @ ${TRAILS_PUBLIC_REF}"; \
    fi

COPY . .

ENV PORT=8080
ENV WORD_DRIFT_STORE=/data/wd-store
ENV TRAILS_ENV=production

VOLUME ["/data"]
EXPOSE 8080

CMD ["python", "app.py"]
