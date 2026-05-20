from backend.core.ingestion.chunking import chunk_text


def test_chunk_text_short():
    text = "Hello world"
    chunks = chunk_text(text, max_tokens=500)
    assert len(chunks) == 1
    assert chunks[0] == text


def test_chunk_text_empty():
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_text_long():
    text = " ".join(["word"] * 2000)
    chunks = chunk_text(text, max_tokens=100, overlap_fraction=0.1)

    assert len(chunks) > 1

    import tiktoken

    enc = tiktoken.get_encoding("cl100k_base")

    for i, chunk in enumerate(chunks):
        token_count = len(enc.encode(chunk))
        assert token_count <= 100, f"Chunk {i} has {token_count} tokens, exceeds 100"


def test_chunk_overlap():
    text = " ".join([f"word{i}" for i in range(500)])
    chunks = chunk_text(text, max_tokens=100, overlap_fraction=0.1)

    assert len(chunks) > 1

    import tiktoken

    enc = tiktoken.get_encoding("cl100k_base")

    overlap = int(100 * 0.1)
    stride = 100 - overlap

    tokens = enc.encode(text)
    expected_chunks = (len(tokens) + stride - 1) // stride
    assert len(chunks) == expected_chunks
