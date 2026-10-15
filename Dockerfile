FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements-app.txt .

RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install \
    --retries 10 \
    --timeout 300 \
    --index-url https://pypi.org/simple \
    -r requirements-app.txt

COPY . .

EXPOSE 8501

CMD ["python", "-m", "streamlit", "run", "app/main.py", "--server.address=0.0.0.0", "--server.port=8501", "--server.headless=true"]