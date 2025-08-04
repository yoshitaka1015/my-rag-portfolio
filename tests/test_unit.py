# app/tests/test_unit.py

import numpy as np
from app.app import find_similar_chunks

def test_find_similar_chunks_returns_correct_order():
    """
    find_similar_chunks関数が、類似度の高い順に正しくチャンクを返すことをテストする。
    """
    # --- 準備 (Arrange) ---
    # テスト用のダミーデータを作成
    texts = ["猫についての文章", "犬についての文章", "鳥についての文章"]
    embeddings = np.array([
        [0.9, 0.1, 0.1],  # 猫
        [0.2, 0.8, 0.1],  # 犬
        [0.1, 0.1, 0.9],  # 鳥
    ])
    # 「猫」に最も近い質問ベクトルを模倣
    query_embedding = np.array([1.0, 0.0, 0.0])

    # --- 実行 (Act) ---
    # テスト対象の関数を実行
    result = find_similar_chunks(query_embedding, embeddings, texts, top_k=2)

    # --- 検証 (Assert) ---
    # 結果が期待通りか検証する
    assert len(result) == 2, "トップ2件が返されるべき"
    assert result[0] == "猫についての文章", "最も類似度が高いのは「猫」のはず"
    assert result[1] == "犬についての文章", "2番目に類似度が高いのは「犬」のはず"