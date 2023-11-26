FROM node:lts-slim as  builder
COPY ./website /opt/website
WORKDIR /opt/website
RUN npm ci
RUN npm run build

FROM python:3.12.0-slim-bookworm

COPY main.py ./opt/app/main.py
COPY --from=builder /opt/website/build /opt/app/website/build
COPY requirements.txt /opt/app/requirements.txt

RUN apt update
RUN apt install -y build-essential
WORKDIR /opt/app
RUN pip install -r requirements.txt
EXPOSE 8000
CMD [ "python", "main.py" ]
