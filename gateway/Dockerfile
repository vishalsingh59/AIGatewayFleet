FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY gateway /app/gateway
COPY shared /app/shared
COPY ci /app/ci

EXPOSE 8080

ENV GATEWAY_BIND_HOST=0.0.0.0
ENV GATEWAY_PORT=8080

CMD ["./gateway/run_gateway.sh", "local", "start", "gateway-1", "true"]
