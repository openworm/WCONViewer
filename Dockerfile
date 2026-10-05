FROM python:3.13-slim

WORKDIR /app

RUN apt-get update
RUN apt-get install -y \
    ffmpeg   \
    && rm -rf /var/lib/apt/lists/*


COPY requirements.txt ./
RUN pip3 install  -r   requirements.txt
RUN pip3 install streamlit


COPY *.py ./
COPY examples/* ./examples/

EXPOSE 8501

HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]