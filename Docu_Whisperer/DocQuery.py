# Main Streamlit app, imports and uses the diffrent modules.
import os, tempfile, subprocess, platform, certifi
import httpx, io
import streamlit as st
import shutil
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS
from langchain.chains import RetrievalQA
import openai
from openai import OpenAI, DefaultHttpxClient
import os, subprocess, platform, sys, shutil
from utils import (
    DATA_FOLDER, save_web_urls, load_web_urls,
    is_valid_docx, is_valid_pdf, is_valid_url
)
from docx_loader import load_docx_chunks
from pdf_loader import load_pdf_chunks
from web_loader import open_web_page, finalize_web_page, extract_page_content

from env_setup import setup_environment, get_api_key
# Set tiktoken cache directory to a writable location
os.environ["TIKTOKEN_CACHE_DIR"] = "/tmp/tiktoken_cache"

FAISS_INDEX_PATH = "faiss_index"  # Use /tmp for FAISS index
setup_environment()
api_key = get_api_key()
api_base_url = "https://api.studio.genai"

OPENAI_API_KEY_VERIFY_SSL = False

#--- Environment Setup ---
ca_bundle_path = "/Users/nilkamal.dey/PyCharmMiscProject/DocuWhisperer/ca_bundle.pem"

if platform.system() == "Windows":
    subprocess.run([
        "powershell", "-Command",
        "Get-ChildItem Cert:\\LocalMachine\\Root, Cert:\\LocalMachine\\CA, Cert:\\CurrentUser\\Root | "
        "Where-Object { ! $_.PsIsContainer } | "
        "ForEach-Object { $_.Export([System.Security.Cryptography.X509Certificates.X509ContentType]::Cert) } | "
        f"Set-Content -Encoding ascii -Path {ca_bundle_path}"
    ], check=True)

elif platform.system() == "Darwin":
    subprocess.run(
        f"security find-certificate -a -p /Library/Keychains/System.keychain "
        f"/System/Library/Keychains/SystemRootCertificates.keychain "
        f"{os.path.expanduser('~/Library/Keychains/login.keychain-db')} > {ca_bundle_path}",
        shell=True, check=True
    )

elif platform.system() == "Linux":
    shutil.copyfile("/etc/ssl/certs/ca-certificates.crt", ca_bundle_path)

os.environ.update({
    "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY", ""),
    "OPENAI_BASE_URL": "https://api.studio.genai",
    "NO_PROXY": os.environ.get("NO_PROXY", "") + ("," if os.environ.get("NO_PROXY")),
    "REQUESTS_CA_BUNDLE": ca_bundle_path,
    # "SSL_CERT_FILE": ca_bundle_path
})

os.environ["OPENAI_BASE_URL"] = "https://api.studio.genai"
os.environ["NO_PROXY"] = os.environ.get("NO_PROXY", "") + ("," if os.environ.get("NO_PROXY"))

# --- Streamlit Page Configuration --- Custom CSS for UI ---
st.set_page_config(
    page_title="DocuWhisperer - Personal AI Chatbot",
    page_icon=":books:"
)
st.markdown("""
<style>
.tab-btn-green button {
    background-color: #5cb85c !important;
    color: white !important;
    border: none !important;
    font-weight: bold !important;
}
.tab-btn-default button {
    background-color: #f0f2f6 !important;
    color: #262730 !important;
    border: 1px solid #d3d3d3 !important;
    font-weight: normal !important;
}
.blink-green-red-bg {
  animation: blinker 1s linear infinite;
  color: #28a745;
  background-color: #d9534f;
  font-weight: bold;
  padding: 4px 12px;
  border-radius: 6px;
  display: inline-block;
}
@keyframes blinker {
  50% { opacity: 0; }
}
</style>
""", unsafe_allow_html=True)

# --- Streamlit UI State Initialization ---
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "Chat"
if "web_urls" not in st.session_state:
    st.session_state["web_urls"] = load_web_urls()
if "pending_web_url" not in st.session_state:
    st.session_state["pending_web_url"] = None
if "selenium_driver" not in st.session_state:
    st.session_state["selenium_driver"] = None
if "show_reindex_msg" not in st.session_state:
    st.session_state["show_reindex_msg"] = False
if "file_uploader_key" not in st.session_state:
    st.session_state["file_uploader_key"] = 0
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# --- Tab Rendering ---
col1, col2 = st.columns(2)
with col1:
    chat_class = "tab-btn-green" if st.session_state["active_tab"] == "Chat" else "tab-btn-default"
    if st.button("Chat", key="tab_chat", use_container_width=True):
        st.session_state["active_tab"] = "Chat"
        st.rerun()
    st.markdown(f'<div class="{chat_class}" style="margin-top:-50px;height:0"></div>', unsafe_allow_html=True)
with col2:
    doc_class = "tab-btn-green" if st.session_state["active_tab"] == "Documents" else "tab-btn-default"
    if st.button("Documents", key="tab_docs", use_container_width=True):
        st.session_state["active_tab"] = "Documents"
        st.rerun()
    st.markdown(f'<div class="{doc_class}" style="margin-top:-50px;height:0"></div>', unsafe_allow_html=True)

st.markdown("---")

def get_doc_paths():
    docx_files = [f for f in os.listdir(DATA_FOLDER) if f.lower().endswith(".docx")]
    pdf_files = [f for f in os.listdir(DATA_FOLDER) if f.lower().endswith(".pdf")]
    docx_paths = [os.path.join(DATA_FOLDER, f) for f in docx_files if is_valid_docx(os.path.join(DATA_FOLDER, f))]
    pdf_paths = [os.path.join(DATA_FOLDER, f) for f in pdf_files if is_valid_pdf(os.path.join(DATA_FOLDER, f))]
    return docx_paths, pdf_paths

def get_all_doc_paths():
    docx_paths, pdf_paths = get_doc_paths()
    return docx_paths + pdf_paths

@st.cache_resource
def load_all_chunks():
    all_chunks = []
    for path in get_all_doc_paths():
        if path.lower().endswith(".docx"):
            all_chunks.extend(load_docx_chunks(path))
        elif path.lower().endswith(".pdf"):
            all_chunks.extend(load_pdf_chunks(path))
    return all_chunks

@st.cache_resource
def get_vector_store():
    embeddings = OpenAIEmbeddings(model="text-embedding-ada-002_v2", openai_api_base=api_base_url, api_key=api_key)
    if os.path.exists(FAISS_INDEX_PATH) and os.listdir(FAISS_INDEX_PATH):
        return FAISS.load_local(FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True)
    chunks = load_all_chunks()
    if chunks:
        vector_store = FAISS.from_documents(chunks, embeddings)
        try:
            vector_store.save_local(FAISS_INDEX_PATH)
        except Exception as e:
            st.error(f"Error saving FAISS index: {e}")
            return None
        return vector_store
    return None

def cleanup_selenium():
    driver = st.session_state.get("selenium_driver")
    if driver:
        try:
            driver.quit()
        except Exception:
            pass
        st.session_state["selenium_driver"] = None
        st.session_state["pending_web_url"] = None

cleanup_selenium()

# --- Chat Tab Logic ---
if st.session_state["active_tab"] == "Chat":
    st.title("Personal AI Chatbot: Ask Questions About Your Documents")
    st.markdown(
        """
        Welcome to your personal AI chatbot!
        - **Ask questions** about your uploaded Word, PDF, and web documents.
        - The chatbot will search your indexed content and provide answers with sources.
        """
    )
    user_query = st.text_input("Enter your question:")
    vector_store = get_vector_store()
    # print(api_base_url)
    # print(api_key)
    if user_query:
        if vector_store is not None:
            llm = ChatOpenAI(
                model_name="gpt-4o_v2024-11-20_USEAST",
                openai_api_base=api_base_url,
                api_key=api_key,
                temperature=0.7
            )
            qa_chain = RetrievalQA.from_chain_type(
                llm=llm,
                chain_type="stuff",
                retriever=vector_store.as_retriever(search_kwargs={"k": 2}),
                return_source_documents=True
            )
            with st.spinner("Getting answer..."):
                result = qa_chain.invoke({"query": user_query})
                # Save conversation
                st.session_state["chat_history"].append({
                    "question": user_query,
                    "answer": result['result'],
                    "sources": result["source_documents"]
                })
                st.markdown(f"**Answer:**\n\n{result['result']}")
                with st.expander("Sources", expanded=False):
                    for doc in result["source_documents"]:
                        doc_name = doc.metadata.get("doc_name", "Unknown")
                        page = doc.metadata.get("page", "N/A")
                        st.markdown(f"- **{doc_name}** (page {page}): `{doc.page_content[:100]}...`")
        else:
            st.info("No documents or web pages indexed yet. Please add some before asking questions.")

    # Show chat history
    if st.session_state["chat_history"]:
        st.markdown("---")
        st.markdown("### Conversation History")
        for i, chat in enumerate(reversed(st.session_state["chat_history"])):
            st.markdown(f"**Q:** {chat['question']}")
            st.markdown(f"**A:** {chat['answer']}")
            with st.expander("Sources", expanded=False):
                for doc in chat["sources"]:
                    doc_name = doc.metadata.get("doc_name", "Unknown")
                    page = doc.metadata.get("page", "N/A")
                    st.markdown(f"- **{doc_name}** (page {page}): `{doc.page_content[:100]}...`")

# --- Documents Tab Logic ---
if st.session_state["active_tab"] == "Documents":
    st.header("Document & Web Page Details")
    uploaded_files = st.file_uploader(
        "Upload Word (.docx) or PDF (.pdf) files",
        type=["docx", "pdf"],
        accept_multiple_files=True,
        key=st.session_state["file_uploader_key"]
    )
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_path = os.path.join(DATA_FOLDER, uploaded_file.name)
            with open(file_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
        st.session_state["show_reindex_msg"] = True
        st.success("Files uploaded. Please run re-indexing.")
        st.session_state["file_uploader_key"] += 1
        st.rerun()

    docx_paths, pdf_paths = get_doc_paths()
    docx_titles = [os.path.basename(p) for p in docx_paths]
    pdf_titles = [os.path.basename(p) for p in pdf_paths]
    web_titles = st.session_state.get("web_urls", [])

    st.markdown("**Word Documents (.docx):**")
    if docx_titles:
        for i, t in enumerate(docx_titles):
            col1, col2 = st.columns([7, 2])
            with col1:
                st.markdown(f"{i+1}. {t}")
            with col2:
                if st.button("Remove", key=f"remove_docx_{i}"):
                    os.remove(os.path.join(DATA_FOLDER, t))
                    st.session_state["show_reindex_msg"] = True
                    st.success("File removed. Please run re-indexing.")
                    st.rerun()
    else:
        st.markdown("_None_")

    st.markdown("**PDF Documents (.pdf):**")
    if pdf_titles:
        for i, t in enumerate(pdf_titles):
            col1, col2 = st.columns([7, 2])
            with col1:
                st.markdown(f"{i+1}. {t}")
            with col2:
                if st.button("Remove", key=f"remove_pdf_{i}"):
                    os.remove(os.path.join(DATA_FOLDER, t))
                    st.session_state["show_reindex_msg"] = True
                    st.success("File removed. Please run re-indexing.")
                    st.rerun()
    else:
        st.markdown("_None_")

    st.markdown("**Web Pages:**")
    if web_titles:
        for i, t in enumerate(web_titles):
            col1, col2 = st.columns([7, 2])
            with col1:
                st.markdown(f"{i+1}. {t}")
            with col2:
                if st.button("Remove", key=f"remove_web_{i}"):
                    st.session_state["web_urls"].pop(i)
                    save_web_urls(st.session_state["web_urls"])
                    st.session_state["show_reindex_msg"] = True
                    st.success("Web page removed. Please run re-indexing.")
                    st.rerun()
    else:
        st.markdown("_None_")

    # chunks = load_all_chunks()
    # vector_store = get_vector_store()
    # st.write(f"Total chunks: {len(chunks)}")

    vector_store = get_vector_store()
    if vector_store:
        try:
            total = int(vector_store.index.ntotal)
        except Exception:
            total = "Unknown"
        st.write(f"Total indexed chunks: {total}")
    else:
        st.write("Total indexed chunks: 0 (No documents indexed yet)")

    if vector_store is not None:
        st.success("FAISS index ready.")
    else:
        st.info("No documents indexed yet. Add files or web pages to get started.")

    # --- Documents Tab Logic ---
    if st.session_state["active_tab"] == "Documents":
        st.header("Document & Web Page Details")
        # ... your existing file uploaders, doc/pdf listing, etc. ...

        st.markdown("**Add a web page to your document index:**")
        web_url = st.text_input("Enter a web page URL:", value="", key="web_url_input")
        if st.button("Add Web Page", key="add_web_btn"):
            # 1) Validate URL
            if not is_valid_url(web_url):
                st.error("❌ Invalid URL, please enter a valid https://... address")
            elif web_url in st.session_state["web_urls"]:
                st.info("ℹ️ That URL is already indexed")
            else:
                with st.spinner("Loading and indexing web page…"):
                    driver, err = open_web_page(web_url, st.session_state, headless=True)
                    if err:
                        st.error(f"❌ Could not load page: {err}")
                    else:
                        try:
                            # a) Extract & chunk
                            chunks = extract_page_content(driver, web_url)
                            if not chunks:
                                raise ValueError("No text extracted from the page.")

                            # b) Load or create FAISS index
                            embeddings = OpenAIEmbeddings(
                                model="text-embedding-ada-002_v2",
                                openai_api_base=api_base_url,
                                api_key=api_key,
                            )
                            if os.path.exists(FAISS_INDEX_PATH) and os.listdir(FAISS_INDEX_PATH):
                                vs = FAISS.load_local(
                                    FAISS_INDEX_PATH,
                                    embeddings,
                                    allow_dangerous_deserialization=True,
                                )
                            else:
                                vs = FAISS.from_documents([], embeddings)

                            # c) Append & save
                            vs.add_documents(chunks)
                            vs.save_local(FAISS_INDEX_PATH)

                            # d) Persist URL
                            st.session_state["web_urls"].append(web_url)
                            save_web_urls(st.session_state["web_urls"])

                            # e) Cleanup Selenium
                            driver.quit()

                            # f) Clear cached FAISS store
                            get_vector_store.clear()

                            # g) Report success
                            st.success(f"✅ Indexed {len(chunks)} chunks from {web_url}")
                            if hasattr(st, "experimental_rerun"):
                                st.experimental_rerun()
                        except Exception as e:
                            try:
                                driver.quit()
                            except Exception:
                                pass
                            st.error(f"❌ Indexing failed: {e}")

    # Re-indexing button
    st.markdown("---")
    col_a, col_b = st.columns([2, 8])
    with col_a:
        if st.button("Re-index Documents"):
            if os.path.exists(FAISS_INDEX_PATH):
                shutil.rmtree(FAISS_INDEX_PATH)
            load_all_chunks.clear()
            get_vector_store.clear()
            st.session_state["show_reindex_msg"] = False
            st.success("Re-indexing triggered. The app will reload.")
            st.session_state["active_tab"] = "Documents"
            st.rerun()
    with col_b:
        if st.session_state.get("show_reindex_msg"):
            st.markdown('<span class="blink-green-red-bg">Please run Re-indexing!</span>', unsafe_allow_html=True)
