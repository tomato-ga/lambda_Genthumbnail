FROM public.ecr.aws/lambda/python:3.12

RUN microdnf install -y tar gzip xz

RUN curl -O https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar -xJf ffmpeg-release-amd64-static.tar.xz && \
    mv ffmpeg-*/ffmpeg /usr/local/bin/ && \
    mv ffmpeg-*/ffprobe /usr/local/bin/ && \
    rm -rf ffmpeg-*

# 作業ディレクトリを設定
WORKDIR /var/task

# 必要なPythonライブラリをインストール
COPY requirements.txt .
RUN pip install -r requirements.txt


COPY app.py .

CMD ["app.lambda_handler"]