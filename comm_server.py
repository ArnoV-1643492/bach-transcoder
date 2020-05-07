# This server will handle all communication with clients
# It will directly access methods from the transcoder

from flask import Flask, request, make_response, jsonify, abort
import json

# Define error class
class ServerExcpetion(Exception):
    pass


app = Flask(__name__)


@app.route('/')
def hello():
    return 'Hello, World!'


# Initial request for video
@app.route('/media/', methods=['GET'])
def getMedia():
    try:
        # Get values
        data = request.get_json(force=True)
        MPD_URL = data["MPD_URL"]
        WANTED_WIDTH = data["WANTED_WIDTH"]
        WANTED_HEIGHT = data["WANTED_HEIGHT"]
        print(MPD_URL, WANTED_WIDTH, WANTED_HEIGHT)

        response = make_response(MPD_URL)
        response.headers['Content-Type'] = 'text/xml'
        return response
    except:
        abort(500)


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port='5000')