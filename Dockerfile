FROM ubuntu

RUN apt-get update
RUN apt-get install -y ffmpeg
RUN apt-get install -y nginx
# RUN apt-get install -y openrc --no-cache
RUN apt-get install -y python3
RUN apt-get install -y python3-pip
RUN apt-get install -y libpcre3 libpcre3-dev
# install GPAC
# RUN apt-get install -y gpac
RUN apt-get install -y build-essential pkg-config git
RUN apt-get install -y zlib1g-dev
# RUN git clone https://github.com/gpac/gpac gpac_public && cd gpac_public &&./configure --static-mp4box && make && make install
# RUN apt install -y dpkg
# RUN apt install -y curl && curl -O https://download.tsi.telecom-paristech.fr/gpac/legacy_builds/linux64/libgpac-dev/libgpac-dev_0.8.1-rev5-g9133f58d-legacy_amd64.deb && apt install -y ./libgpac-dev_0.8.1-rev5-g9133f58d-legacy_amd64.deb
# RUN apt-get install -y curl

RUN mkdir -p /usr/share/nginx/html/dash
COPY nginx.conf /etc/nginx/nginx.conf
#RUN rc-service nginx status
COPY client.html /usr/share/nginx/html/dash/client.html
RUN pip3 install mpegdash ffmpeg-python isodate urllib3 datetime Flask Flask-Cors mysql.connector.python uwsgi

#RUN useradd --no-create-home nginx

#RUN rm /etc/nginx/sites-enabled/default
#RUN rm -r /root/.cache

#COPY nginx.conf /etc/nginx/
ADD . /

RUN tar -xzvf gpac-0.8.0.tar.gz && cd gpac-0.8.0 --static-mp4box && ./configure && make && make install
RUN MP4Box -version
#RUN tar -xf ffmpeg-4.2.2-amd64-static.tar.xz && cd ffmpeg-4.2.2-amd64-static && ./configure && make && make install
#RUN ffmpeg -version
#COPY flask-site-nginx.conf /etc/nginx/conf.d/
#COPY uwsgi.ini /etc/uwsgi/
#COPY supervisord.conf /etc/

#COPY . /project

#WORKDIR /project

#RUN apt-get install -y subversion && svn co https://svn.code.sf.net/p/gpac/code/trunk/gpac gpac && cd gpac && chmod +x configure && ./configure && make && make install && cp bin/gcc/libgpac.so /usr/lib


EXPOSE 80
EXPOSE 5000

#CMD ["/usr/bin/supervisord"]
#CMD ["nginx", "-g", "daemon off;"]
#CMD [ "uwsgi", "-s", "/tmp/transcoder.sock", "--manage-script-name", "--http-socket", ":5000" , "--mount", "/transcoder=comm_server:app", "--enable-threads" ]
#CMD nginx -g daemon off; uwsgi -s /tmp.transcoder.sock --manage-script-name --mount /transcoder=comm_server:app --enable-threads

#ADD . /

# EXPOSE 443

# RUN uwsgi -s /tmp/transcoder.sock --manage-script-name --mount /transcoder=comm_server:app

#CMD [ "python3", "/comm_server.py", "&"]
#CMD ["nginx", "-g", "daemon off;"]
# COPY nginx.conf /etc/nginx/nginx.conf
RUN chmod +x ./start.sh
CMD ["./start.sh"]
#CMD service nginx status
#CMD service nginx restart
