# syntax=docker/dockerfile:1
#
# Single-container image: builds the React dashboard, installs the Coral CLI,
# and serves the FastAPI backend + built frontend on one port. Works on any
# Docker host (Render, Railway, Fly.io, a VM). Vercel/Netlify cannot run this
# image because the backend shells out to the Coral CLI (not serverless).

# ---- Stage 1: build the frontend -------------------------------------------
FROM node:20-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# ---- Stage 2: python runtime + Coral CLI -----------------------------------
FROM python:3.11-slim AS runtime

# curl/bash are needed to install the Coral CLI; ca-certificates for HTTPS.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates bash \
    && rm -rf /var/lib/apt/lists/*

# Install the Coral CLI (lands in /root/.local/bin). If the install host is
# unreachable at build time the image still boots; data queries then return a
# clear 502 until Coral is available.
RUN curl -fsSL https://install.withcoral.com | bash || true
ENV PATH="/root/.local/bin:${PATH}"
ENV CORAL_BIN="coral"

WORKDIR /app

# Install the Python package (editable so config.project_root() resolves to
# /app and the bundled frontend/dist + sources are found at runtime).
COPY pyproject.toml README.md ./
COPY src/ ./src/
COPY sources/ ./sources/
RUN pip install --no-cache-dir -e .

# Bring in the built dashboard from stage 1.
COPY --from=frontend /app/frontend/dist ./frontend/dist

# Persist users/orgs/sessions outside the image — mount a volume at /app/data.
RUN mkdir -p /app/data
ENV AUTH_DB_PATH=/app/data/auth.db
ENV DEVSECOPS_AUTH_ENABLED=1
ENV PORT=8000

EXPOSE 8000

# Shell form so $PORT (set by Render/Railway/Fly) is expanded at runtime.
CMD devsecops-coral serve --host 0.0.0.0 --port ${PORT}
