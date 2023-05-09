# syntax=docker/dockerfile:1

#FROM pytorch/pytorch
FROM tiangolo/uwsgi-nginx-flask:python3.7

WORKDIR /intent-service
COPY ./requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .

EXPOSE 6004

ENV FLASK_APP=main.py

CMD ["python", "-u", "main.py"]
#CMD ["flask", "run", "-h 0.0.0.0", "-p 6001"]
