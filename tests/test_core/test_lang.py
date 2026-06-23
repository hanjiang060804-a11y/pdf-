from pdf_tra.core.lang import detect_language


def test_detect_language_empty_fallback():
    lang, label, fallback = detect_language("")
    assert lang == "English"
    assert label == "英语"
    assert fallback is True


def test_detect_language_english_sample():
    lang, label, fallback = detect_language(
        "This is a sample academic paper about machine learning and neural networks."
    )
    assert lang == "English"
    assert label == "英语"
    assert fallback is False


def test_detect_language_chinese_heuristic():
    lang, label, fallback = detect_language("这是一篇关于深度学习与自然语言处理的中文论文摘要。")
    assert lang == "Simplified Chinese"
    assert label == "简体中文"
    assert fallback is False


def test_detect_language_short_text_fallback():
    lang, label, fallback = detect_language("hi")
    assert lang == "English"
    assert fallback is True
