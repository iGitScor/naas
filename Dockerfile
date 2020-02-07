FROM python:3.7
ADD . /code
WORKDIR /code

RUN apt-get update && apt-get install -y locales locales-all
RUN rm -rf /var/lib/apt/lists/* && locale-gen fr_FR.UTF-8

RUN pip install -r requirements.txt

ENV LANG fr_FR.UTF-8
ENV LANGUAGE fr_FR:fr
ENV LC_ALL fr_FR.UTF-8

CMD python app.py
