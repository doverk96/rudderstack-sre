FROM python:3.8-alpine⁠

WORKDIR /app

COPY *.py requirements.txt ./

RUN pip install -r requirements.txt

ENTRYPOINT ["python"]

CMD ["webhook_server.py"]