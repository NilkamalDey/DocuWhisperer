import time
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import WebDriverException
from webdriver_manager.chrome import ChromeDriverManager

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


def extract_page_content(driver, url):
    """
    Pull the rendered HTML from Selenium, strip out all text,
    then chunk into LangChain Documents.
    """
    soup = BeautifulSoup(driver.page_source, "html.parser")
    text = soup.get_text(separator="\n")
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_text(text)
    return [
        Document(page_content=chunk.strip(), metadata={"source": url})
        for chunk in chunks
        if chunk.strip()
    ]


def open_web_page(url, session_state, headless=True, timeout=20):
    """
    1) Launch Chrome
    2) Navigate to URL
    3) Wait for <body> to exist, for readyState=complete, and for some text
    4) Store driver & url in session_state for later finalization
    """
    options = Options()
    if headless:
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    # If Chrome/Chromium isn’t on your PATH, uncomment & point here:
    # options.binary_location = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
    except WebDriverException as e:
        return None, f"Could not start Chrome WebDriver: {e}"

    try:
        driver.get(url)

        # a) Wait for the body element to exist
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # b) Wait until all resources are loaded
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        # c) Wait for at least some text to appear (avoid empty JS loads)
        WebDriverWait(driver, timeout).until(
            lambda d: len(d.find_element(By.TAG_NAME, "body").text.strip()) > 20
        )

        # d) Last small pause for any late JS
        time.sleep(1)

        # Store for finalize step
        session_state["pending_web_url"] = url
        session_state["selenium_driver"] = driver

        return driver, None

    except Exception as e:
        driver.quit()
        return None, f"Failed to load web page: {e}"


# def finalize_web_page(session_state, store_chunks_in_faiss, save_web_urls):
#     """
#     1) Extract content from the stored driver
#     2) Chunk + store in FAISS
#     3) Persist URL list
#     4) Cleanup driver & session_state
#     """
#     # Ensure our seen‐URL list exists
#     session_state.setdefault("web_urls", [])
#
#     driver = session_state.get("selenium_driver")
#     url = session_state.get("pending_web_url")
#     if not driver or not url:
#         return "No pending web page or driver found."
#
#     try:
#         web_chunks = extract_page_content(driver, url)
#         if not web_chunks:
#             return "No content extracted from the web page after loading."
#
#         # 2) store in your vector index
#         store_chunks_in_faiss(web_chunks)
#
#         # 3) update + persist URL list
#         if url not in session_state["web_urls"]:
#             session_state["web_urls"].append(url)
#             save_web_urls(session_state["web_urls"])
#
#         return f"Added {len(web_chunks)} chunks from {url}. Index updated."
#
#     except Exception as e:
#         return f"Error extracting content: {e}"

# def finalize_web_page(session_state, store_chunks_in_faiss, save_web_urls):
#     driver = session_state.get("selenium_driver")
#     url = session_state.get("pending_web_url")
#     try:
#         web_chunks = extract_page_content(driver, url)
#         if not web_chunks:
#             return "Failed to extract any text from the page."
#
#         try:
#             store_chunks_in_faiss(web_chunks)
#         except Exception as e:
#             return f"Error storing chunks in FAISS: {e}"
#
#         session_state.setdefault("web_urls", [])
#         if url not in session_state["web_urls"]:
#             session_state["web_urls"].append(url)
#             try:
#                 save_web_urls(session_state["web_urls"])
#             except Exception as e:
#                 return f"Error saving URL list: {e}"
#
#         return f"Indexed {len(web_chunks)} chunks from {url}."
#     finally:
#         # Always clean up
#         if driver:
#             try:
#                 driver.quit()
#             except Exception:
#                 pass
#         session_state["selenium_driver"] = None
#         session_state["pending_web_url"] = None
#         session_state["show_reindex_msg"] = True

def finalize_web_page(session_state, save_web_urls, faiss_index_path):
    import os
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.vectorstores import FAISS

    driver = session_state.get("selenium_driver")
    url = session_state.get("pending_web_url")

    web_chunks = extract_page_content(driver, url)
    if not web_chunks:
        return "Failed to extract any text from the page."

    embeddings = OpenAIEmbeddings(
        model="text-embedding-ada-002_v2",
        openai_api_base=os.environ.get("OPENAI_BASE_URL"),
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
    if os.path.exists(faiss_index_path) and os.listdir(faiss_index_path):
        vs = FAISS.load_local(
            faiss_index_path,
            embeddings,
            allow_dangerous_deserialization=True,
        )
        vs.add_documents(web_chunks)
    else:
        vs = FAISS.from_documents(web_chunks, embeddings)
    vs.save_local(faiss_index_path)

    session_state.setdefault("web_urls", [])
    if url not in session_state["web_urls"]:
        session_state["web_urls"].append(url)
        save_web_urls(session_state["web_urls"])

    try:
        driver.quit()
    except Exception:
        pass
    session_state["selenium_driver"] = None
    session_state["pending_web_url"] = None
    # Appended directly into FAISS – no manual Re-index required
    session_state["show_reindex_msg"] = False

    return f"Appended {len(web_chunks)} chunks from {url} to FAISS index."