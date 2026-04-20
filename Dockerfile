FROM continuumio/miniconda3
RUN apt-get update && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY env.yml ./
COPY requirements.txt ./

RUN conda env create -f env.yml
ENV PATH=/opt/conda/envs/env_astro_open/bin:$PATH
RUN echo "source activate env_astro_open" >> ~/.bashrc
RUN pip install --no-cache-dir -r requirements.txt
#RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates \
#      && EPHE_DIR=$(python -c "import os, jhora; print(os.path.join(os.path.dirname(jhora.__file__),'data','ephe'))") \
#      && git clone --depth 1 https://github.com/naturalstupid/pyjhora /tmp/pyjhora \
#      && cp /tmp/pyjhora/src/jhora/data/ephe/* "$EPHE_DIR/" \
#      && rm -rf /tmp/pyjhora /var/lib/apt/lists/*

COPY astro_open_processor.py wsgi.py start.sh ./
COPY logger ./logger
COPY helpers ./helpers

RUN chmod +x start.sh

EXPOSE 5002
ENV TZ=Asia/Kolkata
# Runtime config (override at `docker run`):
#   ALLOW_PUBLIC_ACCESS — "1" to disable the 127.0.0.1-only middleware
#   ENABLE_CORS         — "1" (default) to enable CORS via flask-cors
#   CORS_ORIGINS        — allowed origins list (default "*")
#   PORT                — listen port (default 5002)
ENV ALLOW_PUBLIC_ACCESS=0 \
    ENABLE_CORS=1 \
    CORS_ORIGINS=*
ARG configuration
ENV configuration=$configuration
ENTRYPOINT ["./start.sh"]
