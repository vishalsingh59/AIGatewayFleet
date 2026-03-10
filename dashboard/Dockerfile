FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY dashboard /app/dashboard
COPY shared /app/shared

EXPOSE 9000

ENV DASHBOARD_BIND_HOST=0.0.0.0
ENV DASHBOARD_PORT=9000

CMD ["./dashboard/run_dashboard.sh", "local", "start"]
