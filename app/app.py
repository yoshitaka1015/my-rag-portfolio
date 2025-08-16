import streamlit as st
import numpy as np
import json
from google.cloud import storage
import vertexai
from vertexai.language_models import TextEmbeddingModel
from vertexai.generative_models import GenerativeModel
import os

# -----------------------------------------------------------------------------
# 純粋関数（テストしやすいようにトップレベルに分離）
# -----------------------------------------------------------------------------

def find_similar_chunks(query_embedding, embeddings, texts, top_k=None):
    """コサイン類似度で類似チャンクを見つける（安全・非破壊・シンプル）

    仕様:
      - 入力は非破壊（コピーして扱う）
      - 形状が不正なら ValueError（E: 2次元, q: 1次元, 行数==テキスト数, 列数==クエリ次元）
      - コーパスが空なら []
      - top_k 未指定(None) は 3 件（ただしコーパス件数を上限）
      - top_k が整数でない/0以下は ValueError
      - NaN/Inf は 0 に置換
      - クエリがゼロベクトルなら ValueError
      - コーパス側のゼロベクトルは類似度 0 とみなす
    """
    import numpy as np

    # 非破壊コピー
    q = np.array(query_embedding, dtype=float, copy=True)
    E = np.array(embeddings, dtype=float, copy=True)
    T = list(texts)

    # 形状バリデーション（1行で集約）
    if not (E.ndim == 2 and q.ndim == 1 and E.shape[0] == len(T) and E.shape[1] == q.shape[0]):
        raise ValueError("invalid shapes")

    # 空コーパスは空配列を返す
    if len(T) == 0:
        return []

    # top_k の決定
    if top_k is None:
        k = min(3, len(T))
    else:
        try:
            k = int(top_k)
        except (TypeError, ValueError):
            raise ValueError("top_k must be an integer")
        if k <= 0:
            raise ValueError("top_k must be >= 1")
        k = min(k, len(T))

    # NaN/Inf を 0 に正規化
    q = np.nan_to_num(q, nan=0.0, posinf=0.0, neginf=0.0)
    E = np.nan_to_num(E, nan=0.0, posinf=0.0, neginf=0.0)

    # コサイン類似度計算（ゼロ割/ゼロノルム対策）
    qnorm = np.linalg.norm(q)
    if qnorm == 0.0:
        raise ValueError("query embedding has zero norm")

    Enorms = np.linalg.norm(E, axis=1)
    denom = Enorms * qnorm
    denom_safe = np.where(denom == 0.0, 1.0, denom)
    sims = (E @ q) / denom_safe
    sims = np.where(Enorms == 0.0, 0.0, sims)

    top_idx = np.argsort(-sims)[:k]
    return [T[i] for i in top_idx]


def build_prompt(query: str, similar_chunks: list[str]) -> str:
    """回答生成用のプロンプトを作る純粋関数"""
    context = "\n---\n".join(similar_chunks)
    return f"""
以下の情報を参考にして、質問に日本語で詳しく回答してください。

--- 情報 ---
{context}
--- 情報終わり ---

質問: {query}
""".strip()


def generate_answer(generative_model: GenerativeModel, prompt: str) -> str:
    """LLMにプロンプトを渡して回答テキストを返す純粋関数"""
    resp = generative_model.generate_content([prompt])
    return getattr(resp, "text", "").strip()

# -----------------------------------------------------------------------------
# Streamlitアプリケーションのメインロジック
# -----------------------------------------------------------------------------
def main():
    """
    Streamlitアプリのメイン関数。
    GCPへの接続やUIの描画など、副作用のある処理はすべてこの中に記述します。
    """
    # --- 1. 定数と設定 ---
    PROJECT_ID = os.environ.get("GCP_PROJECT", "serious-timer-467517-e1")
    REGION = os.environ.get("REGION", "us-central1")
    VECTOR_BUCKET_NAME = os.environ.get("VECTOR_BUCKET_NAME")
    EMBEDDING_MODEL_NAME = "text-embedding-004"
    LLM_MODEL_NAME = "gemini-1.5-pro"  # 安定版

    # --- 2. クライアントの初期化 ---
    try:
        vertexai.init(project=PROJECT_ID, location=REGION)
        storage_client = storage.Client()
        embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_NAME)
        generative_model = GenerativeModel(LLM_MODEL_NAME)
    except Exception as e:
        st.error(f"GCPクライアントの初期化に失敗しました: {e}")
        return

    # --- 3. データローダ（ネスト: 親スコープの依存をそのまま使う） ---
    @st.cache_data(show_spinner=False)
    def load_vectors_from_gcs():
        """GCSから全てのJSONLファイルを読み込み、ベクトルとテキストをロードする"""
        if not VECTOR_BUCKET_NAME:
            st.error("環境変数 VECTOR_BUCKET_NAME が設定されていません。")
            return None, None

        bucket = storage_client.bucket(VECTOR_BUCKET_NAME)
        blobs = list(bucket.list_blobs())

        if not blobs:
            return None, None

        all_chunks = []
        for blob in blobs:
            if blob.name.endswith(".jsonl"):
                content = blob.download_as_text()
                for line in content.strip().split("\n"):
                    if line:
                        all_chunks.append(json.loads(line))

        if not all_chunks:
            return None, None

        texts = [c["text_content"] for c in all_chunks]
        embeddings = np.array([c["embedding"] for c in all_chunks], dtype=float)
        embeddings = np.nan_to_num(embeddings, nan=0.0, posinf=0.0, neginf=0.0)
        return texts, embeddings

    # --- 4. UI ---
    st.set_page_config(page_title="RAG Portfolio", layout="wide")
    st.title("RAGシステム ポートフォリオ")

    with st.spinner("GCSから知識ベースを読み込み中..."):
        texts, embeddings = load_vectors_from_gcs()

    if embeddings is None:
        st.error("GCSバケットにベクトルデータが見つかりません。Cloud Functionでドキュメントを処理してください。")
        return

    st.success(f"{len(texts)}個のナレッジチャンクをGCSからロードしました。")

    query = st.text_input("ドキュメントに関する質問を入力してください:", key="query_input")
    if st.button("質問する", key="submit_button"):
        if not query:
            st.error("質問を入力してください。")
            return

        with st.spinner("回答を生成中です..."):
            try:
                # 埋め込み生成（NaN/Infを0に）
                q_emb = embedding_model.get_embeddings([query])[0].values
                q_emb = np.array(q_emb, dtype=float)
                q_emb = np.nan_to_num(q_emb, nan=0.0, posinf=0.0, neginf=0.0)

                # 類似チャンク抽出（デフォルト: 3件）
                similar = find_similar_chunks(q_emb, embeddings, texts, top_k=None)

                # 回答生成
                prompt = build_prompt(query, similar)
                answer = generate_answer(generative_model, prompt)

                st.subheader("🤖 回答:")
                st.write(answer or "(空の応答)")

                with st.expander("AIが参考にした情報源を表示"):
                    for chunk in similar:
                        st.info(chunk)

            except ValueError as ve:
                # 例: top_k < 0 / クエリゼロベクトル等
                st.error(f"入力エラー: {ve}")
            except Exception as e:
                st.error(f"処理中にエラーが発生しました: {e}")

# このファイルが "streamlit run app.py" で直接実行された時だけ、main()関数を呼び出す
if __name__ == "__main__":
    main()