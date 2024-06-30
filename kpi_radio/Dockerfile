FROM python:3.9-slim
WORKDIR /kpi_radio
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
EXPOSE 443
WORKDIR /
RUN apt-get update &&  \
    apt-get install -y curl &&  \
    curl -LJO "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"
CMD ["python", "-m", "kpi_radio"]