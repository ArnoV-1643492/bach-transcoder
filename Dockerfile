FROM python:3.8-alpine

ADD transcoder.py /home/

RUN apk update
RUN apk add ffmpeg

RUN pip install mpegdash
RUN pip install ffmpeg-python
RUN pip install isodate

CMD [ "python", "./home/transcoder.py" ]

RUN ls