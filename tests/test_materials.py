from campusclaw.materials import split_content


def test_split_content_keeps_source_line_numbers():
    chunks = list(split_content("第一行\n第二行", max_chars=3))

    assert [chunk["chunk_index"] for chunk in chunks] == [0, 1]
    assert chunks[0]["start_line"] == 1
    assert chunks[0]["end_line"] == 1
    assert chunks[1]["start_line"] == 2
    assert chunks[1]["end_line"] == 2


def test_long_line_is_split_without_losing_text():
    content = "甲" * 25
    chunks = list(split_content(content, max_chars=10))

    assert "".join(str(chunk["content"]) for chunk in chunks) == content
    assert all(chunk["start_line"] == 1 and chunk["end_line"] == 1 for chunk in chunks)
