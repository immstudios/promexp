FROM python:3.13-slim-trixie
# RUN apt-get update && apt-get install -y \
#     python3-pip \
#     python-is-python3 \
#     && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir --break-system-packages -e .
COPY promexp /app/promexp

CMD ["python", "-m", "promexp"]


