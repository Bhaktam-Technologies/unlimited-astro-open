FROM continuumio/miniconda3
RUN apt update

WORKDIR /app

COPY env.yml ./
COPY astro_open_processor.py ./
COPY wsgi.py ./
COPY start.sh ./
COPY logger ./logger
COPY helpers ./helpers
COPY requirements.txt ./

RUN chmod +x start.sh
RUN conda env create -f env.yml

RUN echo "source activate env_astro_open" >> ~/.bashrc
ENV PATH /opt/conda/envs/env_astro_open/bin:$PATH

RUN pip install -r requirements.txt

EXPOSE 5002
ENV TZ=Asia/Calcutta
ARG configuration
ENV configuration $configuration
ENTRYPOINT ["./start.sh"]
