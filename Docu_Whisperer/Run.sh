#!/bin/bash

export OPENAI_API_KEY=<Add your API key here>
export OPENAI_API_BASE="https://api.studio.genai.cba"

# Remove existing container (ignore error if not found)
docker rm -f DocuWisperer 2>/dev/null

# Build the Docker image (optional, if you need to rebuild)
docker build --no-cache -t docu-wisperer:latest .

# Now run your container
docker run -it \
  --name DocuWisperer \
  -p 8501:8501 \
  -v /Users/nilkamal.dey/PyCharmMiscProject/TestDocker:/app \
  --env-file /Users/nilkamal.dey/PyCharmMiscProject/TestDocker/.env \
  --entrypoint streamlit \
  docu-wisper:latest \
  run /app/DocQuery.py
