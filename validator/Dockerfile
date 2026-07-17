# --- build the native Bliss tool -------------------------------------------
FROM debian:bookworm-slim AS bliss-build
RUN apt-get update && apt-get install -y --no-install-recommends \
        git g++ make ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN git clone --depth 1 https://github.com/digraphs/bliss /bliss \
    && make -C /bliss

# --- runtime ----------------------------------------------------------------
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --from=bliss-build /bliss/bliss /usr/local/bin/bliss
ENV BLISS_BIN=/usr/local/bin/bliss \
    PORTAL_DB=/data/portal.db

COPY er_validator ./er_validator

RUN mkdir /data
VOLUME /data

EXPOSE 8000
CMD ["uvicorn", "er_validator.api:app", "--host", "0.0.0.0", "--port", "8000"]
