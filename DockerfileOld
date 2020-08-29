# FROM python:3.8-alpine
FROM alpine:3.11

RUN apk update
RUN apk add ffmpeg
RUN apk add nginx
RUN apk add openrc --no-cache
RUN apk add python3
RUN apk add py-pip

RUN mkdir -p /usr/share/nginx/html
COPY nginx.conf /etc/nginx/nginx.conf
# RUN rc-service nginx status
COPY client.html /usr/share/nginx/html/client.html

# Add all files and directories
ADD . /

RUN pip install mpegdash ffmpeg-python isodate urllib3 datetime Flask Flask-Cors mysql.connector.python

EXPOSE 80
# EXPOSE 443

CMD ["nginx", "-g", "daemon off;"]
CMD [ "python", "/comm_server.py" ]
CMD service nginx status
CMD service nginx restart
