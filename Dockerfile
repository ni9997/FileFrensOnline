FROM node:lts-slim as  builder
COPY ./website /opt/website
WORKDIR /opt/website
RUN npm ci
RUN npm run build

FROM python:3.12.0-slim-bookworm

COPY ./app/ ./opt/filefrens/app/
COPY --from=builder /opt/website/build /opt/filefrens/website/build
COPY requirements.txt /opt/filefrens/requirements.txt

RUN apt update
RUN apt install -y build-essential
WORKDIR /opt/filefrens
RUN pip install -r requirements.txt
EXPOSE 8000
CMD [ "uvicorn", "app.main:app",  "--host", "0.0.0.0", "--port", "8000" ]
