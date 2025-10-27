# Handles loading and chunking .docx files
import os
from langchain_community.document_loaders import Docx2txtLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

def load_docx_chunks(path):
    loader = Docx2txtLoader(path)
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(documents)
    for chunk in chunks:
        doc_name = os.path.basename(path)
        page = chunk.metadata.get("page", "N/A")
        chunk.page_content = f"[{doc_name} - page {page}]\n{chunk.page_content}"
        chunk.metadata["doc_name"] = doc_name
    return [chunk for chunk in chunks if chunk.page_content.strip()]