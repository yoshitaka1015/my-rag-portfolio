import streamlit as st
import numpy as np
import json
from google.cloud import storage
import vertexai
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel, Part

# --- 1. 定数と設定 (GCPプロジェクトに合わせて変更してください) ---
PROJECT_ID = "serious-timer-467517-e1"       # あなたのGCPプロジェクトID
REGION = "asia-northeast1"                    # リージョン
VECTOR_BUCKET_NAME = "bkt-serious-timer-467517-e1-rag-output" # ベクトルを保存したGCSバケット名
EMBEDDING_MODEL_NAME = "text-embedding-004"
LLM_MODEL_NAME = "gemini-1.5-pro"

# --- 2. クライアントの初期化 ---
vertexai.init(project=PROJECT_ID, location=REGION)
storage_client = storage.Client()
embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_NAME)
generative_model = GenerativeModel(LLM_MODEL_NAME)


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
    
    return texts, embeddings

def find_similar_chunks(query_embedding, embeddings, texts, top_k=5):
    """コサイン類似度で最も類似したチャンクを見つける"""
    # Numpyでコサイン類似度を計算
    dot_products = np.dot(embeddings, query_embedding)
    norms = np.linalg.norm(embeddings, axis=1) * np.linalg.norm(query_embedding)
    similarities = dot_products / norms
    
    # 類似度が高い順にソートし、トップKのインデックスを取得
    top_k_indices = np.argsort(similarities)[-top_k:][::-1]
    
    return [texts[i] for i in top_k_indices]

def generate_answer(query, similar_chunks):
    """LLMを使って回答を生成する"""
    # 情報を一度変数に格納する
    context = "\n---\n".join(similar_chunks)

    prompt = f"""
    以下の情報を参考にして、質問に日本語で詳しく回答してください。

    --- 情報 ---
    {context}
    --- 情報終わり ---

    質問: {query}
    """
    
    response = generative_model.generate_content([prompt])
    return response.text

# --- 3. Streamlit UI ---

if __name__ == "__main__":
    st.set_page_config(page_title="RAG Portfolio", layout="wide")
    st.title("📄 RAGシステム ポートフォリオ")

    with st.spinner("GCSから知識ベースを読み込み中..."):
        texts, embeddings = load_vectors_from_gcs()

    if embeddings is None:
        st.error("GCSバケットにベクトルデータが見つかりません。Cloud Functionでドキュメントを処理してください。")
    else:
        st.success(f"{len(texts)}個のナレッジチャンクをGCSからロードしました。")

        query = st.text_input("ドキュメントに関する質問を入力してください:", key="query_input")

        if st.button("質問する", key="submit_button"):
            if query:
                with st.spinner("回答を生成中です..."):
                    query_embedding = embedding_model.get_embeddings([query])[0].values
                    similar_chunks = find_similar_chunks(query_embedding, embeddings, texts)
                    answer = generate_answer(query, similar_chunks)
                    
                    st.subheader("🤖 回答:")
                    st.write(answer)

                    with st.expander("AIが参考にした情報源を表示"):
                        for chunk in similar_chunks:
                            st.info(chunk)
            else:
                st.error("質問を入力してください。")