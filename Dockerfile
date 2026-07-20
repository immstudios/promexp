FROM python:3.13-slim-trixie

WORKDIR /app
COPY pyproject.toml .
RUN pip install --no-cache-dir --break-system-packages -e .
COPY promexp /app/promexp

CMD ["python", "-m", "promexp"]


