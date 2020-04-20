FROM python:3.6-slim

WORKDIR /var/safebot

ARG TOKEN

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY safebot.py .

RUN sed -i "s/TOKEN/$TOKEN/" safebot.py && sed -i "s/127\.0\.0\.1/safecoin/g" safebot.py

CMD [ "python","safebot.py" ]