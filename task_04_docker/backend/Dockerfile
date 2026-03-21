FROM python:3.11-slim

WORKDIR /backend_app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt
 
COPY . .