FROM apache/airflow:2.9.3-python3.10

WORKDIR /app

USER root

RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
 && apt-get clean && rm -rf /var/lib/apt/lists/*

USER airflow

COPY requirements.txt  ./

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    which airflow && airflow version

COPY resources ./