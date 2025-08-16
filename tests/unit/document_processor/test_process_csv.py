# 純粋関数の正常系だけ確認（依存不要）

import pandas as pd
import document_processor.main as main

def test_process_csv_reads_text(tmp_path):
    # GIVEN: シンプルなCSV
    p = tmp_path / "sample.csv"
    pd.DataFrame({"col1": ["A", "B"], "num": [1, 2]}).to_csv(p, index=False)

    # WHEN: 文字列化
    text = main.process_csv(str(p))

    # THEN: ヘッダ/値が壊れず含まれる
    assert "col1" in text and "num" in text
    assert "A" in text and "B" in text
    assert "1" in text and "2" in text