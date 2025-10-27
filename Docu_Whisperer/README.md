# DocuWhisperer - Your personal GenAI RAG chatbot 

DocuWhisperer is a private AI chatbot that lets you securely upload, index, and query your own documents (PDF, Word, and web pages) using Retrieval-Augmented Generation (RAG) and GenAI Studio APIs. All data stays local for privacy.

<div style="border: 3px solid #ff0000; display: inline-block;">
  <img width="774" height="524" alt="image" src="https://github.com/user-attachments/assets/de816dfa-0cab-4a48-b5bb-f92f4748fa5c" />
</div>

## Project Structure
DocuWhisperer/ 
     ├── DocQuery.py # Main Streamlit app 
     ├── docx_loader.py # .docx chunking 
     ├── pdf_loader.py # .pdf chunking 
     ├── web_loader.py # Web page loading & chunking 
     ├── env_setup.py # Environment and API key setup
     ├── requirements.txt # Python dependencies 
     ├── Dockerfile # Docker build file 
     ├── Run.sh # Shell script for Docker run 
     ├── README.md 
     ├── data/
        └── Docx & PDF Files 
     ├── web_urls.json # JSON file with web URLs to scrape
    
```

## Setup Instructions

1.  **Clone this repository (if applicable):**
    ```bash
    git clone <repository_url>
    cd DocuWhisperer
    ```
    or download the repository as a ZIP file and extract it.

2.  **Create a Python Virtual Environment (Recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows: .\venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Obtain API Keys from GenAI Studio:**
    Please set your API key as environment variables:
    ```bash
    export OPENAI_API_KEY='your_openai_api_key'
    # Or other relevant API keys
    ```

## Running the Demos

To run all the demonstration scripts, execute the main Python file:

```bash
streamlit run DocQuery.py
```


This will start a Streamlit application where you can interact with the various RAG examples.

## Usage
- Upload Documents: Use the Documents tab to upload \.docx or \.pdf files\.
- Add Web Pages: Enter a URL to index a web page\.
- Re-index: Click "Re-index Documents" after adding or removing files/pages\.
- Chat: Switch to the Chat tab to ask questions about your indexed content\.


## Docker Setup (WIP)
bash Run.sh
