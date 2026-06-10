# Dockerfile for CONSTRUCT-AI FastAPI app
FROM python:3.11-slim

# 作業ディレクトリ
WORKDIR /app

# 依存関係をコピーしてインストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY . .

# ポート公開
EXPOSE 8080

# 起動コマンド
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]