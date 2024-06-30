FROM python:3.9-slim
WORKDIR /kpi_radio
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .
RUN wget "https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin"
EXPOSE 443
CMD ["python", "."]