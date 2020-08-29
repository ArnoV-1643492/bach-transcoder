#!/usr/bin/env bash
service nginx start
uwsgi -s /tmp/transcoder.sock --manage-script-name --http-socket :5000 --mount /transcoder=comm_server:app --enable-threads