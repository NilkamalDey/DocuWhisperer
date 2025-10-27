# Handles loading and chunking .pdf files
import os
import sys
import io
from pypdf import PdfReader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

class PyPDFLoader:
    def __init__(self, path):
        self.path = path
    def load(self):
        old_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            reader = PdfReader(self.path)
        finally:
            sys.stdout = old_stdout
        documents = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                documents.append(Document(
                    page_content=text,
                    metadata={"page": i + 1, "doc_name": os.path.basename(self.path)}
                ))
        return documents

def load_pdf_chunks(path):
    loader = PyPDFLoader(path)
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(documents)
    for chunk in chunks:
        doc_name = os.path.basename(path)
        page = chunk.metadata.get("page", "N/A")
        chunk.page_content = f"[{doc_name} - page {page}]\n{chunk.page_content}"
        chunk.metadata["doc_name"] = doc_name
    return [chunk for chunk in chunks if chunk.page_content.strip()]