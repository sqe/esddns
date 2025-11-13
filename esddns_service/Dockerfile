FROM python:3.12

RUN mkdir /esddns
COPY . esddns/
WORKDIR /esddns

RUN pip install --upgrade pip
RUN pip3 install -r requirements.txt

EXPOSE 51339
ENV FLASK_APP=esddns_service/esddns_endpoint.py
ENTRYPOINT [ "flask", "run", "--host=0.0.0.0", "--port=51339" ]