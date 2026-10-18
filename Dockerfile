FROM python:3.12.14-slim-bookworm@sha256:392307d22300de8b5986851a12d9176dfc0fc073e65bf6523ebd7dcbeb23564e AS dependencies
WORKDIR /app
RUN --mount=type=secret,id=proxy_ca \
    if [ -s /run/secrets/proxy_ca ]; then cp /run/secrets/proxy_ca /usr/local/share/ca-certificates/environment-proxy.crt; update-ca-certificates; fi \
    && sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get -o APT::Update::Error-Mode=any update && apt-get install -y --no-install-recommends \
    poppler-utils latexmk texlive-latex-recommended texlive-latex-extra \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir uv==0.12.23
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_CACHE_DIR=/opt/uv-cache \
    UV_NATIVE_TLS=true \
    OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    MPLCONFIGDIR=/tmp/weaponized-matplotlib XDG_CACHE_HOME=/tmp/weaponized-cache \
    SOURCE_DATE_EPOCH=1792281600
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-editable
FROM dependencies AS research
COPY . .
ENV PATH="/opt/venv/bin:${PATH}"
CMD ["python", "scripts/replicate.py", "--full"]
