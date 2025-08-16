# tests/unit/test_find_similar_chunks.py

import numpy as np
import pytest
from app.app import find_similar_chunks


# GIVEN/WHEN/THEN: 類似度が高い順に返す
def test_find_similar_chunks_returns_correct_order():
    """GIVEN ベクトル群（猫/犬/鳥）。WHEN 猫に近いクエリ。THEN 猫→犬の順で返る。"""
    texts = ["猫についての文章", "犬についての文章", "鳥についての文章"]
    embeddings = np.array([
        [0.9, 0.1, 0.1],  # 猫
        [0.2, 0.8, 0.1],  # 犬
        [0.1, 0.1, 0.9],  # 鳥
    ])
    query_embedding = np.array([1.0, 0.0, 0.0])

    result = find_similar_chunks(query_embedding, embeddings, texts, top_k=2)

    assert len(result) == 2, "トップ2件が返されるべき"
    assert result[0] == "猫についての文章", "最も類似度が高いのは「猫」のはず"
    assert result[1] == "犬についての文章", "2番目に類似度が高いのは「犬」のはず"


# GIVEN/WHEN/THEN: top_k がコーパス数を超えていても安全に動く
def test_top_k_greater_than_corpus_is_clamped():
    """GIVEN 3件のコーパス。WHEN top_k=10。THEN 3件が返る。"""
    texts = ["A", "B", "C"]
    embeddings = np.eye(3)
    query_embedding = np.array([1.0, 0.0, 0.0])

    result = find_similar_chunks(query_embedding, embeddings, texts, top_k=10)

    assert len(result) == 3
    assert result[0] == "A"


# GIVEN/WHEN/THEN: top_k=1 で最上位のみ返す
def test_top_k_one_returns_single_result():
    """GIVEN 3件のコーパス。WHEN top_k=1。THEN 最上位1件のみ。"""
    texts = ["A", "B", "C"]
    embeddings = np.array([
        [0.9, 0.0, 0.0],
        [0.8, 0.0, 0.0],
        [0.1, 0.0, 0.0],
    ])
    query_embedding = np.array([1.0, 0.0, 0.0])

    result = find_similar_chunks(query_embedding, embeddings, texts, top_k=1)
    assert result == ["A"]


# GIVEN/WHEN/THEN: 空コーパスでは空リストを返す
def test_empty_corpus_returns_empty_list():
    """GIVEN 空のtextsとembeddings。WHEN 検索。THEN [] が返る。"""
    texts = []
    embeddings = np.empty((0, 3))
    query_embedding = np.array([1.0, 0.0, 0.0])

    result = find_similar_chunks(query_embedding, embeddings, texts, top_k=5)
    assert result == []


# GIVEN/WHEN/THEN: texts と embeddings の件数が不一致なら ValueError
def test_mismatched_lengths_raises():
    """GIVEN texts=2, embeddings=3。WHEN 検索。THEN ValueError。"""
    texts = ["A", "B"]
    embeddings = np.eye(3)
    query_embedding = np.array([1.0, 0.0, 0.0])

    with pytest.raises(ValueError):
        find_similar_chunks(query_embedding, embeddings, texts, top_k=2)


# GIVEN/WHEN/THEN: クエリと埋め込みの次元が不一致なら ValueError
def test_dimensionality_mismatch_raises():
    """GIVEN embeddings の次元=3、クエリ次元=2。WHEN 検索。THEN ValueError。"""
    texts = ["A", "B", "C"]
    embeddings = np.eye(3)
    query_embedding = np.array([1.0, 0.0])  # (2,)

    with pytest.raises(ValueError):
        find_similar_chunks(query_embedding, embeddings, texts, top_k=2)


# ＝＝＝ ここから追加（#2, #3, #4, #5, #10, #12） ＝＝＝

# #2 GIVEN/WHEN/THEN: top_k=0 / 負数はエラー
def test_top_k_zero_raises():
    """GIVEN 正常データ。WHEN top_k=0。THEN ValueError。"""
    texts = ["A", "B", "C"]
    embeddings = np.eye(3)
    query_embedding = np.array([1.0, 0.0, 0.0])

    with pytest.raises(ValueError):
        find_similar_chunks(query_embedding, embeddings, texts, top_k=0)


def test_top_k_negative_raises():
    """GIVEN 正常データ。WHEN top_k<0。THEN ValueError。"""
    texts = ["A", "B", "C"]
    embeddings = np.eye(3)
    query_embedding = np.array([1.0, 0.0, 0.0])

    with pytest.raises(ValueError):
        find_similar_chunks(query_embedding, embeddings, texts, top_k=-1)


# #3 GIVEN/WHEN/THEN: 非破壊性（引数を変更しない）
def test_function_is_non_destructive():
    """GIVEN 入力。WHEN 実行。THEN texts/embeddings/query は変更されない。"""
    texts = ["A", "B", "C"]
    embeddings = np.array([
        [0.9, 0.0, 0.0],
        [0.8, 0.0, 0.0],
        [0.1, 0.0, 0.0],
    ])
    query_embedding = np.array([1.0, 0.0, 0.0])

    texts_before = list(texts)
    embeddings_before = embeddings.copy()
    query_before = query_embedding.copy()

    _ = find_similar_chunks(query_embedding, embeddings, texts, top_k=2)

    assert texts == texts_before
    assert np.array_equal(embeddings, embeddings_before)
    assert np.array_equal(query_embedding, query_before)


# #4 GIVEN/WHEN/THEN: NaN/Inf を含む埋め込みは 0 に置換され、計算が継続する
def test_nan_in_embeddings_is_sanitized():
    """GIVEN embeddings に NaN。WHEN 検索。THEN 例外にならず、正常に順位付けされる。"""
    texts = ["A", "B"]
    embeddings = np.array([
        [1.0, 0.0],
        [np.nan, 0.0],
    ])
    query_embedding = np.array([1.0, 0.0])

    result = find_similar_chunks(query_embedding, embeddings, texts, top_k=1)
    assert result == ["A"]  # NaN→0 に置換された行はゼロベクトル扱いで上位には来ない


def test_inf_in_embeddings_is_sanitized():
    """GIVEN embeddings に Inf。WHEN 検索。THEN 例外にならず、正常に順位付けされる。"""
    texts = ["A", "B"]
    embeddings = np.array([
        [1.0, 0.0],
        [np.inf, 0.0],
    ])
    query_embedding = np.array([1.0, 0.0])

    result = find_similar_chunks(query_embedding, embeddings, texts, top_k=1)
    assert result == ["A"]  # Inf→0 に置換された行はゼロベクトル扱いで上位には来ない


def test_nan_in_query_becomes_zero_and_raises():
    """GIVEN クエリに NaN（他成分は0）。WHEN 検索。THEN NaN→0 でゼロベクトルになり ValueError。"""
    texts = ["A", "B"]
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0]])
    query_embedding = np.array([np.nan, 0.0])

    with pytest.raises(ValueError):
        find_similar_chunks(query_embedding, embeddings, texts, top_k=2)


# #5 GIVEN/WHEN/THEN: ゼロベクトルクエリはエラー
def test_zero_vector_query_raises():
    """GIVEN クエリがゼロベクトル。WHEN 検索。THEN ValueError。"""
    texts = ["A", "B"]
    embeddings = np.array([[1.0, 0.0], [0.0, 1.0]])
    query_embedding = np.array([0.0, 0.0])

    with pytest.raises(ValueError):
        find_similar_chunks(query_embedding, embeddings, texts, top_k=2)


# #10 GIVEN/WHEN/THEN: top_k 未指定は 3 件（上限はコーパス件数）
def test_default_topk_returns_three_or_less():
    """GIVEN 4件のコーパス。WHEN top_k=None。THEN 3件が返る。"""
    texts = ["A", "B", "C", "D"]
    embeddings = np.eye(4)
    query_embedding = np.array([1.0, 0.0, 0.0, 0.0])

    result = find_similar_chunks(query_embedding, embeddings, texts)  # top_k=None
    assert len(result) == 3


def test_default_topk_capped_by_corpus_len():
    """GIVEN 2件のコーパス。WHEN top_k=None。THEN 2件が返る。"""
    texts = ["A", "B"]
    embeddings = np.eye(2)
    query_embedding = np.array([1.0, 0.0])

    result = find_similar_chunks(query_embedding, embeddings, texts)
    assert len(result) == 2


# #12 GIVEN/WHEN/THEN: Unicode/記号混在でも壊れない
def test_unicode_and_symbols_are_preserved():
    """GIVEN Unicode/記号混在の texts。WHEN 検索。THEN 文字列が壊れず返る。"""
    texts = ["税・控除🧾", "αβγ", "漢字🙂とEmoji🚀", "記号!@#￥%"]
    embeddings = np.array([
        [0.9, 0.0, 0.0],   # 税・控除🧾
        [0.7, 0.0, 0.0],   # αβγ
        [0.6, 0.0, 0.0],   # 漢字🙂とEmoji🚀
        [0.5, 0.0, 0.0],   # 記号...
    ])
    query_embedding = np.array([1.0, 0.0, 0.0])

    result = find_similar_chunks(query_embedding, embeddings, texts, top_k=3)

    # 返ってきたテキストがそのままの内容であること
    assert result[0] == "税・控除🧾"
    assert isinstance(result[0], str)
    assert "Emoji" in texts[2]