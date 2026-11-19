FROM node:24-bookworm-slim AS web
WORKDIR /build
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.12-slim AS api
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 INSIGHTPORTAL_DATA_DIR=/data
WORKDIR /app
COPY requirements.txt ./
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home --uid 10001 portal \
    && install -d -o portal -g portal /data
COPY insightportal/ insightportal/
COPY contracts/ contracts/
COPY warehouse/ warehouse/
COPY --from=web /build/dist web/dist/
USER portal
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "insightportal.main:app", "--host", "0.0.0.0", "--port", "8000"]
