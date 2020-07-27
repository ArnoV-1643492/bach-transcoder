# This server will handle all communication with clients
# It will directly access methods from the transcoder

from flask import Flask, request, make_response, jsonify, abort
from flask_cors import CORS
import json
import threading
from transcoder import startStream, Stream_Info
import DB_conn

# Define error class
class ServerExcpetion(Exception):
    pass


app = Flask(__name__)
CORS(app)


@app.route('/')
def hello():
    return 'Hello, World!'


# Initial request for video
@app.route('/media/', methods=['POST'])
def getMedia():
    try:
        # Get values
        data = request.get_json(force=True)
        MPD_URL = data["MPD_URL"]
        WANTED_WIDTH = data["WANTED_WIDTH"]
        WANTED_HEIGHT = data["WANTED_HEIGHT"]
        print(MPD_URL, WANTED_WIDTH, WANTED_HEIGHT)

        # Start thread
        streaminfo = Stream_Info()
        streaminfo.width = WANTED_WIDTH
        streaminfo.height = WANTED_HEIGHT
        mpd_available = threading.Event()
        thread = threading.Thread(target=startStream, args=(MPD_URL, streaminfo, mpd_available))
        print("Starting thread")
        thread.start()

        # wait here for the result to be available before continuing
        mpd_available.wait()

        response = make_response(json.dumps({"STREAM_AVAILABLE": True, "STREAM_INFO": {"LOCAL_MPD_URL": streaminfo.stream_name + "/" + streaminfo.mpd_url}}))
        response.headers['Content-Type'] = 'application/json'
        # response = make_response(streaminfo.mpd_url)
        # response.headers['Content-Type'] = 'text/xml'
        return response
    except Exception as err:
        print(err)
        abort(500)

# Requests response time of server
# Use database method
@app.route('/stats/responseTime', methods=['GET'])
def getResponseTime():
    try:
        responseTime = DB_conn.getFirstPeriodTime()
        response = make_response(json.dumps({"responseTime": responseTime}))
        response.headers['Content-type'] = 'application/json'
        return response
        
    except Exception as err:
        print(err)
        abort(500)

# Request stream progress
# Use database method
@app.route('/stats/streamData', methods=['GET'])
def getStreamData():
    try:
        streamData = DB_conn.getStreamsProgressData()
        response = make_response(json.dumps(streamData))
        response.headers['Content-type'] = 'application/json'
        return response
        
    except Exception as err:
        print(err)
        abort(500)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='5000')