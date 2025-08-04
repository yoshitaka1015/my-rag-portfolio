import streamlit as st
import numpy as np
import json
from google.cloud import storage
import vertexai
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel, Part

# -----------------------------------------------------------------------------
# ユニットテスト対象の純粋な関数
# (この関数はGCPに接続しないため、安全にテストできます)
# -----------------------------------------------------------------------------
def find_similar_chunks(query_embedding, embeddings, texts, top_k=5):
    """コサイン類似度で最も類似したチャンクを見つける"""
    # Numpyでコサイン類似度を計算
    dot_products = np.dot(embeddings, query_embedding)
    norms = np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
    similarities = dot_products / norms
    
    # 類似度が高い順にソートし、トップKのインデックスを取得
    top_k_indices = np.argsort(similarities)[-top_k:][::-1]
    
    return [texts[i] for i in top_k_indices]


# -----------------------------------------------------------------------------
# Streamlitアプリケーションのメインロジック
# -----------------------------------------------------------------------------
def main():
    """
    Streamlitアプリのメイン関数。
    GCPへの接続やUIの描画など、副作用のある処理はすべてこの中に記述します。
    """
    # --- 1. 定数と設定 ---
    PROJECT_ID = "serious-timer-467517-e1"
    REGION = "asia-northeast1"
    VECTOR_BUCKET_NAME = "bkt-serious-timer-467517-e1-rag-output"
    EMBEDDING_MODEL_NAME = "text-embedding-004"
    LLM_MODEL_NAME = "gemini-1.5-pro" # 最新の安定版モデルを使用

    # --- 2. クライアントの初期化 ---
    try:
        vertexai.init(project=PROJECT_ID, location=REGION)
        storage_client = storage.Client()
        embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_NAME)
        generative_model = GenerativeModel(LLM_MODEL_NAME)
    except Exception as e:
        st.error(f"GCPクライアントの初期化に失敗しました: {e}")
        return

    # --- 関数の定義 ---
    # @st.cache_data(show_spinner=False)
    def load_vectors_from_gcs():
        """GCSから全てのJSONLファイルを読み込み、ベクトルとテキストをロードする"""
        bucket = storage_client.bucket(VECTOR_BUCKET_NAME)
        blobs = list(bucket.list_blobs())
        
        if not blobs:
            return None, None
            
        all_chunks = []
        for blob in blobs:
            if blob.name.endswith('.jsonl'):
                content = blob.download_as_text()
                for line in content.strip().split('\n'):
                    if line:
                        all_chunks.append(json.loads(line))
        
        if not all_chunks:
            return None, None
            
        texts = [chunk['text_content'] for chunk in all_chunks]
        embeddings = np.array([chunk['embedding'] for chunk in all_chunks])