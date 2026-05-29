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
# Source priority:
#   1. Gitea (git.xorwell.de:c/framework.trails) — authoritative, has the
#      latest commits including the security and versioning work. Requires
#      a read token, passed as a BuildKit secret named ``git_token`` so it
#      is never written to an image layer:
#
#          DOCKER_BUILDKIT=1 docker build \
#              --secret id=git_token,src=<(printf %s "$GIT_TOKEN") -t word-drift-on-trails .
#
#      On the deploy host the token already lives at ``/opt/dev/.gitea_token``
#      and is wired in via the docker-compose ``secrets:`` block.
#
#   2. github.com/XORwell/trails — public, frozen snapshot. Used as the
#      no-secret fallback. It may lag behind Gitea on the alpha branch, so
#      the ``TRAILS_PIN`` ref must exist there too if you build without the
#      token. No silent ``|| echo`` fallback — a missing Trails fails the
#      build loud.
#
# TRAILS_PIN is the exact git commit / tag / branch that word-drift is built
# against. It MUST match the range declared in trails_compat.py — when the
# trails_compat range moves, bump TRAILS_PIN to a Trails ref that satisfies
# the new range, then update TRAILS_TESTED_AGAINST in trails_compat.py once
# the test suite has been run against that ref. The runtime check in
# trails_compat.enforce() refuses to start the app in production if these
# drift apart, so an ops error here is loud and fail-fast.
ARG TRAILS_PIN=19b71d4
ARG TRAILS_GITEA_HOST=git.xorwell.de
ARG TRAILS_GITHUB_REF=git+https://github.com/XORwell/trails.git@${TRAILS_PIN}#subdirectory=python
RUN --mount=type=secret,id=git_token \
    TOKEN="$(cat /run/secrets/git_token 2>/dev/null || true)"; \
    if [ -n "$TOKEN" ]; then \
        pip install --no-cache-dir \
            "trails[http] @ git+https://oauth2:${TOKEN}@${TRAILS_GITEA_HOST}/c/framework.trails.git@${TRAILS_PIN}#subdirectory=python"; \
    else \
        pip install --no-cache-dir "trails[http] @ ${TRAILS_GITHUB_REF}"; \
    fi

COPY . .

ENV PORT=8080
ENV WORD_DRIFT_STORE=/data/wd-store
ENV TRAILS_ENV=production

VOLUME ["/data"]
EXPOSE 8080

CMD ["python", "app.py"]
