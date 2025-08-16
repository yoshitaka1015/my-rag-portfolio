# 純粋関数のPDF抽出（本番と同じ PyMuPDF 経路で検証）

from reportlab.pdfgen import canvas
import document_processor.main as main

def test_process_pdf_extracts_text(tmp_path):
    # GIVEN: "Hello PDF" を含むPDFを生成
    pdf = tmp_path / "hello.pdf"
    c = canvas.Canvas(str(pdf))
    c.drawString(100, 750, "Hello PDF")
    c.save()

    # WHEN: テキスト抽出
    text = main.process_pdf(str(pdf))

    # THEN: 期待の文字列が含まれる
    assert "Hello PDF" in text