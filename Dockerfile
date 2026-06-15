FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements-server.txt .
RUN pip install --no-cache-dir -r requirements-server.txt

# Copy project
COPY . .

# Pre-build the dashboard data from committed snapshots
RUN python outputs/dashboard/render.py

EXPOSE 8080

CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--timeout", "180", "--workers", "1", "server:app"]
