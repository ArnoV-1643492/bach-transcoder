# FROM python:3.8-alpine
FROM alpine:3.11

RUN apk update
RUN apk add ffmpeg=4.2.1
RUN apk add nginx
RUN apk add python3

ADD transcoder.py /usr/share/nginx/html/
ADD bbb_30fps.mpd /usr/share/nginx/html/

RUN pip3 install mpegdash
RUN pip3 install ffmpeg-python
RUN pip3 install isodate

EXPOSE 80
EXPOSE 443

CMD [ "python3", "./usr/share/nginx/html/transcoder.py" ]

RUN ls /usr/share/nginx/html/