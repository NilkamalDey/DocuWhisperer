# Use a Debian base image
FROM applicationinfrastructure-public.docker.internal/library/python:3.11-slim-bookworm

WORKDIR /app

COPY . /app

# Do not store pip cache during install
RUN pip3 install --no-cache-dir --timeout=1500 -r /app/requirements.txt --index-url https://artifactory.internal/artifactory/api/pypi/pypi/simple

RUN pip3 install tiktoken \
 && mkdir -p /app/tiktoken_cache \
 && TIKTOKEN_CACHE_DIR=/app/tiktoken_cache python3 -c "import tiktoken; tiktoken.get_encoding('cl100k_base')"

ENV TIKTOKEN_CACHE_DIR=/app/tiktoken_cache
ENV PYTHONUNBUFFERED=1

EXPOSE 80
EXPOSE 443
# adding these ports for debugging, will remove later
EXPOSE 8080
EXPOSE 8501

ENTRYPOINT ["bash", "-c"]
CMD ["streamlit", "run", "DocQuery.py", "--server.port=8501", "--server.address=0.0.0.0"]
