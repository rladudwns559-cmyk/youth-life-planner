FROM node:24-bookworm-slim AS web
WORKDIR /build
RUN npm install --global pnpm@11.25.0
COPY frontend/package.json frontend/pnpm-lock.yaml frontend/pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile --ignore-scripts
COPY frontend/ ./
RUN pnpm run build

FROM python:3.12-slim-bookworm AS service
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    AIX_ENV=production WEB_BUILD_DIR=/app/web \
    ASSET_ALERTS_AUTO_REFRESH=1 ASSET_ALERTS_STATE_DIR=/var/data/asset-alerts
WORKDIR /app
RUN groupadd --gid 10001 aix && useradd --uid 10001 --gid 10001 --no-create-home aix
COPY requirements-web.txt ./
RUN pip install --no-cache-dir -r requirements-web.txt
COPY backend/ ./backend/
COPY data/synthetic/ ./data/synthetic/
COPY data/financial-products/ ./data/financial-products/
COPY data/asset-programs/ ./data/asset-programs/
COPY --from=web /build/dist/ ./web/
COPY deploy/start.py ./deploy/start.py
EXPOSE 10000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 CMD python -c "import os,urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.getenv('PORT','10000')+'/api/health',timeout=4)"
CMD ["python", "-B", "deploy/start.py"]
