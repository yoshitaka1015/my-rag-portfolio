# ベースとなる公式のPythonイメージを選択
FROM python:3.11-slim

# アプリケーションコードをコピーするための作業ディレクトリを作成
WORKDIR /app

# 最初にライブラリの定義ファイルだけをコピー
COPY requirements.txt .

# 必要なライブラリをインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションのコードを作業ディレクトリにコピー
COPY . .

# Cloud Runが指定するポート8080を公開
EXPOSE 8080

# コンテナが起動したときにStreamlitアプリを実行するコマンド
CMD ["streamlit", "run", "app.py", "--server.port=8080", "--server.address=0.0.0.0"]