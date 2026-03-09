from history_rag.ingest.parser import Document


def _split_sentences(text: str) -> list[str]:
    """Split classical Chinese text into sentences by punctuation."""
    sentences = []
    current = []
    for char in text:
        current.append(char)
        if char in "。！？；":
            sentences.append("".join(current))
            current = []
    if current:
        sentences.append("".join(current))
    return sentences


def chunk_documents(
    documents: list[Document],
    max_chars: int = 500,
    overlap_sentences: int = 2,
    min_chars: int = 30,
) -> list[Document]:
    """Chunk documents with classical Chinese aware splitting.

    Strategy:
    - Paragraphs <= max_chars: keep as-is
    - Paragraphs > max_chars: split on sentence boundaries with overlap
    - Very short paragraphs (< min_chars, non-header): merge with next
    """
    # First pass: merge very short paragraphs
    merged = []
    buffer = None

    for doc in documents:
        if buffer is not None:
            # Merge short doc into buffer
            merged_doc = Document(
                text=buffer.text + doc.text,
                source=doc.source,
                chapter=doc.chapter,
                section=doc.section or buffer.section,
                citation=doc.citation or buffer.citation,
                chunk_id=buffer.chunk_id,
                translation=(buffer.translation + doc.translation)
                if buffer.translation and doc.translation
                else "",
            )
            if len(merged_doc.text) < min_chars:
                buffer = merged_doc
            else:
                merged.append(merged_doc)
                buffer = None
        elif len(doc.text) < min_chars:
            buffer = doc
        else:
            merged.append(doc)

    if buffer is not None:
        merged.append(buffer)

    # Second pass: split long paragraphs
    chunked = []
    for doc in merged:
        if len(doc.text) <= max_chars:
            chunked.append(doc)
            continue

        sentences = _split_sentences(doc.text)
        current_chunk: list[str] = []
        current_len = 0

        for sent in sentences:
            if current_len + len(sent) > max_chars and current_chunk:
                # Emit chunk
                chunk_text = "".join(current_chunk)
                chunked.append(Document(
                    text=chunk_text,
                    source=doc.source,
                    chapter=doc.chapter,
                    section=doc.section,
                    citation=doc.citation,
                    chunk_id=f"{doc.chunk_id}_c{len(chunked)}",
                    translation="",
                ))
                # Keep overlap
                current_chunk = current_chunk[-overlap_sentences:]
                current_len = sum(len(s) for s in current_chunk)

            current_chunk.append(sent)
            current_len += len(sent)

        if current_chunk:
            chunk_text = "".join(current_chunk)
            chunked.append(Document(
                text=chunk_text,
                source=doc.source,
                chapter=doc.chapter,
                section=doc.section,
                citation=doc.citation,
                chunk_id=f"{doc.chunk_id}_c{len(chunked)}",
                translation="",
            ))

    # Re-assign unique chunk IDs
    for i, doc in enumerate(chunked):
        doc.chunk_id = f"{doc.source}_{i:06d}"

    return chunked
