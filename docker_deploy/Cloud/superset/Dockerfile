FROM apache/superset:latest

USER root
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     gcc python3-dev libpq-dev \
#     && pip install --no-cache-dir --upgrade psycopg2-binary redis \
#     && apt-get clean && rm -rf /var/lib/apt/lists/*

USER superset
# COPY superset_config.py /app/pythonpath/superset_config.py