# tests/unit/document_processor/test_process_document.py
# 目的: DI設計の process_document を、外部I/Oを使わずにテストする。
# 方針: テスト内に最小限のフェイク（Storage/Embedder/Splitter）を定義し、イベントと環境を注入する。

from __future__ import annotations
import json
from pathlib import Path
import pytest
import document_processor.main as main

# =========================
# フェイク実装（最小限）
# =========================

class FakeBlob:
    """GCS Blob もどき：download は事前登録されたファイルからコピー、upload は文字列をメモリに保存。"""
    def __init__(self, client: "MemoryStorageClient", bucket: str, name: str):
        self.client = client
        self.bucket = bucket
        self.name = name

    def download_to_filename(self, dst_path: str) -> None:
        key = (self.bucket, self.name)
        src_path = self.client._seed_sources.get(key)
        if not src_path:
            raise FileNotFoundError(f"seed されていない: {key}")
        data = Path(src_path).read_bytes()
        Path(dst_path).write_bytes(data)

    def upload_from_string(self, data: str, content_type: str = "application/octet-stream") -> None:
        self.client._uploaded_objects[(self.bucket, self.name)] = {
            "content_type": content_type,
            "data": data,
        }


class FakeBucket:
    def __init__(self, client: "MemoryStorageClient", name: str):
        self.client = client
        self.name = name

    def blob(self, name: str) -> FakeBlob:
        return FakeBlob(self.client, self.name, name)


class MemoryStorageClient:
    """メモリ上に GCS っぽい振る舞いを再現。"""
    def __init__(self):
        # (bucket, name) -> 元ファイルパス（download 元）
        self._seed_sources: dict[tuple[str, str], str] = {}
        # (bucket, name) -> {"content_type": str, "data": str}
        self._uploaded_objects: dict[tuple[str, str], dict] = {}

    # 便利ヘルパ：ソースを登録（process_document が download するときの元データ）
    def seed_source_file(self, bucket: str, name: str, file_path: str) -> None:
        self._seed_sources[(bucket, name)] = file_path

    def bucket(self, name: str) -> FakeBucket:
        return FakeBucket(self, name)


class ConstantSplitter:
    """splitter.split_text(text) を常に固定チャンク列で返すシンプルなフェイク。"""
    def __init__(self, chunks: list[str]):
        self._chunks = list(chunks)

    def split_text(self, text: str) -> list[str]:
        return list(self._chunks)


class FakeEmbedder:
    """get_embeddings(chunks) -> list[list[float]] を返すだけのフェイク。"""
    def get_embeddings(self, chunks: list[str]) -> list[list[float]]:
        # 各チャンクに対して [len(chunk), 0.0] のような簡単なベクトルを返す
        return [[float(len(c)), 0.0] for c in chunks]


# =========================
# テスト
# =========================

def test_process_document_csv_to_jsonl(tmp_path: Path):
    """正常系: CSV を処理し、1つの JSONL を出力。行数=分割チャンク数。"""
    # GIVEN: 入力CSVファイルと、固定分割(60件)・埋め込みフェイク・メモリStorage
    src_bucket = "src-bkt"
    out_bucket = "out-bkt"
    src_name = "big.csv"

    # 実ファイル（ダウンロード元）を用意
    csv_path = tmp_path / src_name
    csv_path.write_text("col\n" + "A\n" * 3, encoding="utf-8")  # 中身は何でもOK（splitterが無視するため）

    storage = MemoryStorageClient()
    storage.seed_source_file(src_bucket, src_name, str(csv_path))

    # 固定60チャンクを返す splitter と、ダミー埋め込み
    splitter = ConstantSplitter(["CHUNK"] * 60)
    embedder = FakeEmbedder()

    event = {"bucket": src_bucket, "name": src_name}

    # WHEN: DIで依存を注入して実行
    main.process_document(
        event,
        context=None,
        storage_client=storage,
        splitter=splitter,
        embedding_model=embedder,
        project_id="dummy",
        region="us-central1",
        output_bucket=out_bucket,
        batch_size=25,  # バッチは埋め込み呼び出し単位にだけ効く（出力は1ファイル）
    )

    # THEN: 出力は out-bkt に "big.csv.jsonl" が1つ、60行のJSONL
    key = (out_bucket, "big.csv.jsonl")
    assert key in storage._uploaded_objects, "出力JSONLがアップロードされていません"
    uploaded = storage._uploaded_objects[key]["data"]
    lines = [ln for ln in uploaded.splitlines() if ln.strip()]
    assert len(lines) == 60, f"行数が想定と違います: {len(lines)}"

    # 各行は JSON で、期待キーが入っている
    rec0 = json.loads(lines[0])
    assert set(["source_file", "chunk_id", "text_content", "embedding"]).issubset(rec0.keys())


def test_process_document_unsupported_ext_returns(tmp_path: Path):
    """未サポート拡張子: 例外を投げずに return する（安全側の早期終了）。"""
    storage = MemoryStorageClient()
    splitter = ConstantSplitter(["X"])
    embedder = FakeEmbedder()

    # .txt はサポート外
    src_bucket = "src"
    src_name = "note.txt"
    p = tmp_path / src_name
    p.write_text("hello", encoding="utf-8")
    storage.seed_source_file(src_bucket, src_name, str(p))

    event = {"bucket": src_bucket, "name": src_name}

    # 例外が出ないこと、かつアップロードが発生しないことを確認
    main.process_document(
        event,
        context=None,
        storage_client=storage,
        splitter=splitter,
        embedding_model=embedder,
        project_id="dummy",
        region="us-central1",
        output_bucket="out",
    )
    assert ("out", "note.txt.jsonl") not in storage._uploaded_objects