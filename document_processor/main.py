import os
import json
import fitz
import pandas as pd
from google.cloud import storage
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- 定数（環境変数から取得。未設定時は安全なデフォルトを採用） ---
PROJECT_ID = os.environ.get("GCP_PROJECT") or os.environ.get("GOOGLE_CLOUD_PROJECT")
REGION = os.environ.get("REGION", "us-central1")
OUTPUT_BUCKET = os.environ.get("OUTPUT_BUCKET_NAME")
EMBEDDING_MODEL_NAME = os.environ.get("EMBEDDING_MODEL_NAME", "text-embedding-004")


def build_text_splitter(chunk_size: int = 1000, chunk_overlap: int = 100):
    """デフォルトのテキストスプリッタを生成（テストで差し替えやすいよう関数化）。"""
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def process_document(
    event,
    context,
    *,
    storage_client: storage.Client | None = None,
    splitter=None,
    embedding_model=None,
    project_id: str | None = None,
    region: str | None = None,
    output_bucket: str | None = None,
    batch_size: int = 10,
):
    """
    GCS へのファイルアップロードをトリガーに実行されるメイン関数。
    依存（Storage クライアント、スプリッタ、埋め込みモデル）は引数で DI 可能にし、
    テストではモックを渡して I/O を避けられるようにしている。
    実際の Cloud Run 実行では引数を省略すれば従来通り動作する。
    """
    # 実行時コンテキストの解決
    project_id = project_id or PROJECT_ID
    region = region or REGION
    output_bucket = output_bucket or OUTPUT_BUCKET

    if storage_client is None:
        storage_client = storage.Client(project=project_id)

    # event から GCS オブジェクト情報を取得
    bucket_name = event.get("bucket") if isinstance(event, dict) else None
    file_name = event.get("name") if isinstance(event, dict) else None

    if not bucket_name or not file_name:
        print("[WARN] event に bucket / name が含まれていません。処理を中止します。")
        return

    # ソースを /tmp へダウンロード
    source_bucket = storage_client.bucket(bucket_name)
    source_blob = source_bucket.blob(file_name)
    temp_file_path = f"/tmp/{os.path.basename(file_name)}"
    source_blob.download_to_filename(temp_file_path)

    # テキスト抽出（拡張子で分岐）
    lower_name = file_name.lower()
    if lower_name.endswith(".pdf"):
        extracted_text = process_pdf(temp_file_path)
    elif lower_name.endswith(".csv"):
        extracted_text = process_csv(temp_file_path)
    else:
        print(f"サポート外のファイル形式です: {file_name}")
        return

    if not extracted_text:
        print("[INFO] 抽出テキストが空のため処理をスキップします。")
        return

    if not output_bucket:
        # 本番環境でも安全側に倒す（環境変数未設定時はアップロードしない）
        print("[WARN] OUTPUT_BUCKET_NAME が未設定のため、出力をスキップします。")
        return

    # スプリッタ生成（未指定ならデフォルト）
    splitter = splitter or build_text_splitter()

    print("テキストのチャンク化を開始...")
    chunks = splitter.split_text(extracted_text)
    print(f"{len(chunks)} 個のチャンクに分割しました。")

    # 埋め込みモデル生成（未指定なら Vertex AI を初期化）
    if embedding_model is None:
        aiplatform.init(project=project_id, location=region)
        embedding_model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_NAME)

    print("チャンクのベクトル化を開始...")
    all_embeddings = []
    for i in range(0, len(chunks), batch_size):
        batch_chunks = chunks[i : i + batch_size]
        embeddings_batch = embedding_model.get_embeddings(batch_chunks)
        all_embeddings.extend(embeddings_batch)
        print(f"{i + len(batch_chunks)} / {len(chunks)} 個のチャンクを処理しました...")

    # JSONL を生成し、出力バケットへ保存
    output_lines: list[str] = []
    for idx, chunk in enumerate(chunks):
        emb_obj = all_embeddings[idx]
        # 本番では .values を持つが、テストでは list で代用できるようフォールバック
        values = getattr(emb_obj, "values", emb_obj)
        output_lines.append(
            json.dumps(
                {
                    "source_file": file_name,
                    "chunk_id": idx,
                    "text_content": chunk,
                    "embedding": values,
                },
                ensure_ascii=False,
            )
        )

    output_blob_name = f"{file_name}.jsonl"
    output_bucket_ref = storage_client.bucket(output_bucket)
    output_blob = output_bucket_ref.blob(output_blob_name)
    output_blob.upload_from_string("\n".join(output_lines), content_type="application/jsonl")
    print(f"ベクトルデータ保存完了: gs://{output_bucket}/{output_blob_name}")


# 純粋関数：ここはユニットテストしやすい

def process_pdf(file_path: str) -> str:
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()
    return text


def process_csv(file_path: str) -> str:
    df = pd.read_csv(file_path)
    return df.to_string()