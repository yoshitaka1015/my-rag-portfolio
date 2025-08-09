import os
import fitz
import pandas as pd
from google.cloud import storage
from google.cloud import aiplatform
from vertexai.language_models import TextEmbeddingModel

import json
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- 定数 ---
PROJECT_ID = os.environ.get('GCP_PROJECT')
REGION = "us-central1"
OUTPUT_BUCKET = os.environ.get('OUTPUT_BUCKET_NAME')
EMBEDDING_MODEL_NAME = "text-embedding-004"

# --- グローバルスコープで初期化しても問題ないもの ---
aiplatform.init(project=PROJECT_ID, location=REGION)
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
)

def process_document(event, context):
    """GCSへのファイルアップロードをトリガーに実行されるメイン関数"""
    # --- クライアントは関数の中で初期化する ---
    storage_client = storage.Client()

    bucket_name = event['bucket']
    file_name = event['name']
    
    # ... (以降のコードは変更なし) ...
    source_bucket = storage_client.bucket(bucket_name)
    source_blob = source_bucket.blob(file_name)
    temp_file_path = f"/tmp/{file_name.split('/')[-1]}"
    source_blob.download_to_filename(temp_file_path)

    extracted_text = ""
    if file_name.lower().endswith('.pdf'):
        extracted_text = process_pdf(temp_file_path)
    elif file_name.lower().endswith('.csv'):
        extracted_text = process_csv(temp_file_path)
    else:
        print(f"サポート外のファイル形式です: {file_name}")
        return

    if extracted_text and OUTPUT_BUCKET:
        # 1. テキストをチャンクに分割
        print("テキストのチャンク化を開始...")
        chunks = text_splitter.split_text(extracted_text)
        print(f"{len(chunks)}個のチャンクに分割しました。")

        # 2. 各チャンクをベクトル化
        print("チャンクのベクトル化を開始...")
        model = TextEmbeddingModel.from_pretrained(EMBEDDING_MODEL_NAME)

        all_embeddings = []
        batch_size = 10  # 一度にAPIに送るチャンクの数
        
        for i in range(0, len(chunks), batch_size):
            batch_chunks = chunks[i:i + batch_size]
            embeddings_batch = model.get_embeddings(batch_chunks)
            all_embeddings.extend(embeddings_batch)
            print(f"{i + len(batch_chunks)} / {len(chunks)} 個のチャンクを処理しました...")

        # 以前のembeddings変数を、新しいall_embeddingsに置き換える
        embeddings = all_embeddings
        
        # 3. チャンクとベクトルをペアにしてJSONL形式で保存
        output_lines = []
        for i, chunk in enumerate(chunks):
            output_data = {
                "source_file": file_name,
                "chunk_id": i,
                "text_content": chunk,
                "embedding": embeddings[i].values
            }
            output_lines.append(json.dumps(output_data))

        output_blob_name = f"{file_name}.jsonl"
        output_bucket = storage_client.bucket(OUTPUT_BUCKET)
        output_blob = output_bucket.blob(output_blob_name)
        output_blob.upload_from_string(
            "\n".join(output_lines), 
            content_type="application/jsonl"
        )
        print(f"ベクトルデータ保存完了: gs://{OUTPUT_BUCKET}/{output_blob_name}")

def process_pdf(file_path):
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()
    return text

def process_csv(file_path):
    df = pd.read_csv(file_path)
    return df.to_string()