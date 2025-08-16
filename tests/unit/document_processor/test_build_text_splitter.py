# tests/unit/document_processor/test_build_text_splitter.py
import pytest

import document_processor.main as main


def test_build_text_splitter_returns_configured_splitter():
    # GIVEN: chunk_size=50, chunk_overlap=7 でスプリッタを生成
    splitter = main.build_text_splitter(chunk_size=50, chunk_overlap=7)

    # THEN: 代表メソッドが呼べる & 実際の分割が size に収まる（属性名に依存しない堅牢な確認）
    assert hasattr(splitter, "split_text") and callable(splitter.split_text)
    sample = "".join(chr(97 + (i % 26)) for i in range(200))  # a..z を繰り返す200文字
    chunks = splitter.split_text(sample)
    assert len(chunks) > 0
    assert all(1 <= len(c) <= 50 for c in chunks)


def test_build_text_splitter_splits_text_with_overlap():
    # GIVEN: シンプルな英字10文字（区切り記号なし）と size=4 / overlap=1 の設定
    text = "abcdefghij"
    splitter = main.build_text_splitter(chunk_size=4, chunk_overlap=1)

    # WHEN: 分割を実行
    chunks = splitter.split_text(text)

    # THEN: 期待する分割（4文字・1文字重なり）= ["abcd","defg","ghij"]
    assert chunks == ["abcd", "defg", "ghij"]


@pytest.mark.parametrize("size,overlap", [(4, 4), (10, 10)])
def test_build_text_splitter_overlap_equal_is_allowed(size, overlap):
    # GIVEN/WHEN: overlap == size はライブラリ仕様上は許容される（例外は出ない）
    splitter = main.build_text_splitter(chunk_size=size, chunk_overlap=overlap)
    text = "abcdefghijklmno"
    chunks = splitter.split_text(text)

    # THEN: 分割は成功し、各チャンク長は上限 size を超えない（空文字も不可）
    assert len(chunks) > 0
    assert all(1 <= len(c) <= size for c in chunks)


@pytest.mark.parametrize("size,overlap", [(4, 5), (10, 12)])
def test_build_text_splitter_overlap_greater_raises(size, overlap):
    # GIVEN/WHEN/THEN: overlap > size の場合はコンストラクタで ValueError
    with pytest.raises(ValueError):
        main.build_text_splitter(chunk_size=size, chunk_overlap=overlap)


def test_build_text_splitter_limits_chunk_length():
    # GIVEN: 長文を与え、size=7 / overlap=2 で生成
    text = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    splitter = main.build_text_splitter(chunk_size=7, chunk_overlap=2)

    # WHEN: 分割
    chunks = splitter.split_text(text)

    # THEN: 各チャンク長が chunk_size を超えない／空文字列が含まれない
    assert len(chunks) > 0
    assert all(1 <= len(c) <= 7 for c in chunks)