FROM python:3.11-slim

WORKDIR /telegram_bot

COPY requirements.txt /telegram_bot
RUN  pip install -r ./requirements.txt

COPY . /telegram_bot

CMD [ "python", "./main.py" ]
