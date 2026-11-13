FROM python:3.12-slim AS builder
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /build
COPY requirements.lock .
RUN pip wheel --wheel-dir /wheels -r requirements.lock
COPY campusclaw ./campusclaw
ARG SOURCE_REVISION=worktree
RUN python -c 'import hashlib,json,pathlib; p=pathlib.Path("campusclaw"); files={str(f):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(p.rglob("*")) if f.is_file() and "__pycache__" not in f.parts and f.suffix!=".pyc"}; pathlib.Path("build-info.json").write_text(json.dumps({"source_revision":__import__("os").environ.get("SOURCE_REVISION","worktree"),"application_sha256":hashlib.sha256(json.dumps(files,sort_keys=True).encode()).hexdigest(),"files":files}))'
RUN python -m compileall -b -q --invalidation-mode checked-hash campusclaw \
    && find campusclaw -type f -name '*.py' -delete \
    && find campusclaw -type d -name __pycache__ -exec rm -rf {} +

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
ARG SOURCE_REVISION=worktree
LABEL org.opencontainers.image.revision=$SOURCE_REVISION
RUN useradd --create-home --uid 10001 campusclaw
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --no-index --find-links=/wheels /wheels/* && rm -rf /wheels
COPY --from=builder --chown=campusclaw:campusclaw /build/campusclaw ./campusclaw
COPY --from=builder /build/build-info.json /app/build-info.json
RUN mkdir -p /app/instance && chown campusclaw:campusclaw /app/instance
USER campusclaw
EXPOSE 8000
HEALTHCHECK --interval=5s --timeout=3s --start-period=10s --retries=5 \
 CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/ready', timeout=2)"]
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "campusclaw:create_app()"]
