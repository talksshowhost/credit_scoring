FROM python:3.12.4

WORKDIR /server

COPY requirements.txt ./

RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY application.py model.pkl ./