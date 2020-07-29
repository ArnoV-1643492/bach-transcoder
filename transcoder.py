from mpegdash.parser import MPEGDASHParser
import urllib
import ffmpeg
import isodate
import datetime
import math
import os
import subprocess
import threading
import json
import DB_conn
from datetime import datetime
# from h26x_extractor import h26x_parser

# get current directory
dir_path = os.path.dirname(os.path.realpath(__file__))
print("------------------------------------------------")
print(dir_path)
print("------------------------------------------------")
# change working directory
rootDir = "/usr/share/nginx/html/"
os.chdir(rootDir)

# This is where the information of the currently stored streams is kept
streamMapName = "streamMap.json"

# Indicates how many segments will be used in the first period
segmentsFirstPeriod = 2
# Indicates how many segments will be used for the other periods
segmentsInPeriod = 4

# THREAD LOCK
lock = threading.Lock()

# Server load limit
maxLoad = 0
currentLoad = 0

# mpd_url = 'https://dash.akamaized.net/akamai/bbb_30fps/bbb_30fps.mpd'
# mpd_url = 'https://bitmovin-a.akamaihd.net/content/MI201109210084_1/mpds/f08e80da-bf1d-4e3d-8899-f0f6155f6efa.mpd'

class Stream_Info:
    mpd_url = ""
    stream_id = 0
    stream_name = ""
    width = 0
    height = 0


# Increases the number of transcoding threads currently running by 1
def increaseLoadCounter():
    with lock:
        global currentLoad 
        currentLoad= currentLoad + 1


# Decrease the number of transcoding threds currently running by 1
def decreaseLoadCounter():
    with lock:
        global currentLoad
        currentLoad = currentLoad - 1


# Add a new stream to the stream map
# periodBase name is the first part of the name of the concatenated periods
# periodNameEnd is the part of the name that comes after the index of the period
# THREAD LOCK
def addStreamMap(streamDir, mpd_url, periodBaseName, periodNameEnd, MPDName, stream_name, representationWidth, representationHeight, numberOfSegments):
    with lock:
        mapData = {}
        mapData["streamList"] = []
        try:
            with open(rootDir + streamMapName) as map:
                mapData = json.load(map)
        except IOError:
            print("stream map does not exist, file will be created")

        # Create JSON object
        stream = {}
        stream["streamDir"] = streamDir
        stream["periodBaseName"] = periodBaseName
        stream["periodNameEnd"] = periodNameEnd
        stream["mpd_url"] = mpd_url
        stream["MPDName"] = MPDName
        stream["stream_name"] = stream_name
        stream["numberOfSegments"] = numberOfSegments

        # Add the current representation to the stream as well
        representation = {}
        representation["width"] = representationWidth
        representation["heigth"] = representationHeight
        stream["representations"] = []
        stream["representations"].append(representation)

        mapData["streamList"].append(stream)

        # Write to file
        with open(rootDir + streamMapName, 'w+') as outfile:
            json.dump(mapData, outfile)

# Add a representation to the stream map for an existing stream
# THREAD LOCK
def addRepresentationToStreamMap(mpd_url, representationWidth, representationHeight):
    with lock:
        with open(rootDir + streamMapName) as map:
            mapData = json.load(map)

        # Loop through all streams to find the correct stream
        for i in range(0,len(mapData["streamList"])):
            # Stream found
            if mapData["streamList"][i]["mpd_url"] == mpd_url:
                # stream found, add representation
                representation = {}
                representation["width"] = representationWidth
                representation["heigth"] = representationHeight
                mapData["streamList"][i]["representations"].append(representation)

        # Write to file
        with open(rootDir + streamMapName, 'w+') as outfile:
            json.dump(mapData, outfile)


# Checks if the given stream already exists locally, returns bool
# THREAD LOCK
def streamInMap(mpd_url):
    with lock:
        try:
            with open(rootDir + streamMapName) as map:
                mapData = json.load(map)
                for stream in mapData["streamList"]:
                    # Stream found
                    if stream["mpd_url"] == mpd_url:
                        return True
                # Stream not found
                return False
        except IOError:
            # Map does not yet exist, there are no streams locally
            return False


# Returns the number of segments in stream
# THREAD LOCK
def getNumberOfSegments(mpd_url):
    with lock:
        try:
            with open(rootDir + streamMapName) as map:
                mapData = json.load(map)
                for stream in mapData["streamList"]:
                    # Stream found
                    if stream["mpd_url"] == mpd_url:
                        return stream["numberOfSegments"]
                return 0
        except IOError:
            # Map does not yet exist, there are no streams locally
            return 0


# If a stream already exists, the return for the parent thread will be created
# THREAD LOCK
def returnExistingStream(mpd_url, streaminfo, mpd_available):
    with lock:
        with open(rootDir + streamMapName) as map:
            mapData = json.load(map)
            for stream in mapData["streamList"]:
                # Stream found
                if stream["mpd_url"] == mpd_url:
                    streaminfo.stream_name = stream["stream_name"]
                    streaminfo.mpd_url = stream["MPDName"]
                    mpd_available.set()


# If cached stream is lower resolution than requested stream, return false
# Otherwise, return true
def isCachedStreamHigher(mpd_url, streaminfo):
    requestedRes = int(streaminfo.width) * int(streaminfo.height)
    with lock:
        with open(rootDir + streamMapName) as map:
            mapData = json.load(map)
            for stream in mapData["streamList"]:
                if stream["mpd_url"] == mpd_url:
                    # Stream found
                    # Loop through representations until higher one is found
                    for rep in stream["representations"]:
                        repRes = int(rep["width"]) * int(rep["heigth"])
                        if requestedRes <= repRes:
                            # Resolution is good enough
                            return True
            
            # loop ended, no suitable representation found
            return False


# If cached stream has the same resolution as the requested resolution, return True
def isCachedEqual(mpd_url, streaminfo):
    with lock:
        with open(rootDir + streamMapName) as map:
            mapData = json.load(map)
            for stream in mapData["streamList"]:
                if stream["mpd_url"] == mpd_url:
                    # Stream found
                    # Loop through representations same one is found
                    for rep in stream["representations"]:
                        if rep["width"] == streaminfo.width and rep["heigth"] == streaminfo.height:
                            # Resolution is the same
                            return True
            
            # loop ended, no suitable representation found
            return False


# Scale the segment to a different resolution
def scaleSegment(inputSeg, outputSeg, output_width, output_height):
    input_args = {
        "hwaccel": "nvdec",
        "vcodec": "h264_cuvid",
        "c:v": "h264_cuvid",
        "analyzeduration": "2147483647",
        "probesize": "2147483647"
    }
    stream = ffmpeg.input(inputSeg, **input_args)
    stream = ffmpeg.filter(stream, 'scale', width=output_width, height=output_height)
    stream = ffmpeg.output(stream, outputSeg)
    compileStr = ffmpeg.compile(stream)
    print(compileStr)
    ffmpeg.run(stream)
    print(outputSeg)
    # out = subprocess.run(["ffmpeg","-y","-i",inputSeg,"-vf", "scale=480:360", "-f","mp4","-movflags", "frag_keyframe+omit_tfhd_offset+empty_moov", outputSeg])



# Concatenate a segment to the initial segment
def catSegment(segment, outputName):
    with open(segment, "rb") as segmentFile, open(outputName, "ab") as outputFile:
        outputFile.write(segmentFile.read())


# Copy data from one file to another
def copySegment(orig, dest):
    with open(orig, "rb") as origFile, open(dest, "ab") as outputFile:
        outputFile.write(origFile.read())


# Gets period video as input and creates a DASH period using MP4Box
def makePeriod(periodName, MPDName, segmentSize, fragmentSize):
    # Run MP4Box
    #  "-url-template", wtih segmentSize 1000 for segmentTemplate instead of segmentlist
    # , "-segment-timeline" , "-segment-name", "\"$RepresentationID$_$Number$$Init=i$\"",
    # subprocess.run(["MP4Box", "-dash", str(segmentSize), "-rap", "-segment-timeline", "-frag", str(fragmentSize), "-out", MPDName, periodName])
    subprocess.run(["MP4Box", "-dash", str(segmentSize), "-rap", "-frag", str(fragmentSize), "-segment-timeline", "-out", MPDName, periodName, periodName])
    # subprocess.run(["MP4Box", "-dash", str(segmentSize), "-rap", "-frag-rap", "-bs-switching", "inband", "-out", MPDName, periodName, "-url-template"])


# Create the new MPD file
def createMPD(MPDName):
    with open(MPDName, "ab") as MPD:
        return


# Add new Period to MPD
# THREAD LOCK
def addPeriodToMPD(MPDName, periodMPDName, periodNumber):
    with lock:
        #with open(MPDName, "ab") as MPD, open(periodMPDName, "rb") as periodMPDName:
        # Add period
        MPD_parse = MPEGDASHParser.parse(MPDName)
        Period_parse = MPEGDASHParser.parse(periodMPDName)
        # Give new id to period
        Period_parse.periods[0].id = periodNumber
        '''period_duration = Period_parse.periods[0].duration
        durationHMS = isodate.parse_duration(period_duration)
        durationS = durationHMS.total_seconds()
        durationS = durationS * 2
        newduartion = datetime.timedelta(seconds=durationS)
        Period_parse.periods[0].duration = newduartion'''

        # Remove all exess representations from Period MPD
        if (len(Period_parse.periods[0].adaptation_sets[0].representations) > 1):
            for i in range(1, len(Period_parse.periods[0].adaptation_sets[0].representations)):
                del Period_parse.periods[0].adaptation_sets[0].representations[i]
        # Change representation id of the only representation left in Period MPD
        Period_parse.periods[0].adaptation_sets[0].representations[0].id = 1

        MPD_parse.periods.append(Period_parse.periods[0])

        # Write new verion of MPD
        MPEGDASHParser.write(MPD_parse, MPDName)

# THREAD LOCK
def addRepresentationToMPD(MPDName, periodMPDName, periodNumber):
    with lock:
        MPD_parse = MPEGDASHParser.parse(MPDName)
        Period_parse = MPEGDASHParser.parse(periodMPDName)
        # Remove all exess representations from Period MPD
        if (len(Period_parse.periods[0].adaptation_sets[0].representations) > 1):
            for i in range(1, len(Period_parse.periods[0].adaptation_sets[0].representations)):
                del Period_parse.periods[0].adaptation_sets[0].representations[i]
        # Count number of representations already in final MPD
        numberOfReps = len(MPD_parse.periods[periodNumber].adaptation_sets[0].representations)
        # Change representation id of the only representation left in Period MPD
        Period_parse.periods[0].adaptation_sets[0].representations[0].id = numberOfReps + 1
        # Add the representation to the final MPD
        MPD_parse.periods[periodNumber].adaptation_sets[0].representations.append(Period_parse.periods[0].adaptation_sets[0].representations[0])

        # Write new verion of MPD
        MPEGDASHParser.write(MPD_parse, MPDName)


# Copy one MPD into antoher MPD (used for the first MPD generation)
# THREAD LOCK
def copyMPD(MPDName, periodMPDName, MPDuration, periodNumber):
    with lock:
        #with open(MPDName, "ab") as MPD, open(periodMPDName, "rb") as period:
        #    MPD.write(period.read())
        
        # Change duration
        MPD_parse = MPEGDASHParser.parse(periodMPDName)
        # Give new id to period
        MPD_parse.periods[0].id = periodNumber
        MPD_parse.media_presentation_duration = MPDuration
        # Change MPD to dynamic
        MPD_parse.type = "dynamic"
        MPD_parse.minimum_update_period="PT0H0M1.00S"
        MPD_parse.time_shift_buffer_depth=MPDuration
        MPD_parse.availability_start_time="2020-05-03T18:38:00Z"

        # Remove all exess representations from Period MPD
        if (len(MPD_parse.periods[0].adaptation_sets[0].representations) > 1):
            for i in range(1, len(MPD_parse.periods[0].adaptation_sets[0].representations)):
                del MPD_parse.periods[0].adaptation_sets[0].representations[i]

        # Write
        MPEGDASHParser.write(MPD_parse, MPDName)


# HTTP GETs all the segments and saves them on disc
def GetSegments(baseURL, fileNameTemplate, baseWriteLocation, numberOfSegments, containerExtention):
    # First download init segment number 0
    getURL_init =  baseURL + fileNameTemplate + '0' + containerExtention
    fileName_init = baseWriteLocation + fileNameTemplate + '0' + containerExtention
    # Download init segment
    print("GET " + getURL_init)
    print(fileName_init)
    urllib.request.urlretrieve(getURL_init, fileName_init)

    # Init segment is 0, so start at 1 for data segments
    for i in range(1,numberOfSegments):
        # The file we will call HTTP GET for
        getURL = baseURL + fileNameTemplate + str(i) + containerExtention
        # The relative file location and name for the downloaded segment
        fileName = baseWriteLocation + fileNameTemplate + str(i) + containerExtention
        print("GET " + getURL)
        # Do HTTP GET
        urllib.request.urlretrieve(getURL, fileName)

        # TODO: start a new thread here that transcodes the download file
        fileName_seg_initialised = baseWriteLocation + fileNameTemplate + str(i) + '_initialised' + containerExtention
        # catSegment(fileName_init, fileName, fileName_seg_initialised)

        fileName_seg_converted = baseWriteLocation + fileNameTemplate + str(i) + '_converted' + containerExtention
        scaleSegment(fileName_seg_initialised, fileName_seg_converted, 480, 360)


# HTTP GETs all the segments and saves them on disc
def GetSegmentsV2(baseURL, baseWriteLocation, numberOfSegments, segmentTemplate, representationID, initSegmentTemplate, segmentsPerPeriod, MPDuration, stream_name, streaminfo, mpd_available, streamDir, mpd_url):
    # Add representation to database
    now = datetime.now()
    formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
    representationName = streaminfo.height + "x" + streaminfo.width
    DB_conn.addTranscoding(mpd_url, representationName, numberOfSegments, 0, formatted_date)
    # First download init segment
    initSegmentName = initSegmentTemplate.replace("$RepresentationID$", representationID)
    getURL_init =  baseURL + initSegmentName
    fileName_init = initSegmentName

    print(getURL_init)
    print(fileName_init)

    # Make directory
    initSegmentNameSplit = initSegmentName.split("/")
    dirName = ""
    for i in range(0, len(initSegmentNameSplit) - 1):
        dirName += initSegmentNameSplit[i] + "/"
    if not os.path.exists(dirName):
        os.makedirs(dirName)

    # Download init segment
    print("GET " + getURL_init)
    urllib.request.urlretrieve(getURL_init, fileName_init)

    BaseSegmentName = segmentTemplate.replace("$RepresentationID$", representationID)

    # MPD name
    MPDName = stream_name + "_local_" + ".mpd"
    # Create MPD
    createMPD(MPDName)

    periodNumber = 0
    initSplit = initSegmentName.split(".")
    origVideoExtention = initSplit[len(initSplit) -1]

    # Add stream to map
    addStreamMap(streamDir, mpd_url, representationID + "_period_", origVideoExtention, MPDName, stream_name, streaminfo.width, streaminfo.height, numberOfSegments)

    i = 1

    # Set the segments per period
    # initially use the number of segments for the first period
    # afterwards switch to the segments in period
    # this will reduce initial startup time of the stream
    segmentsPerPeriod = segmentsFirstPeriod

    # Init segment is 0, so start at 1 for data segments
    while(i < numberOfSegments):

        periodName = representationID + "_period_" + str(periodNumber) + "." + origVideoExtention
        # At the beginning of each period file we will place the init data
        copySegment(initSegmentName, periodName)

        print("i: " + str(i))

        # Fetch all segments needed for current period
        for j in range(i, i+segmentsPerPeriod):

            # check if we have reached the last segement
            if (i+segmentsPerPeriod >= numberOfSegments):
                break
            
            segmentName = BaseSegmentName.replace("$Number$", str(j))
            # The file we will call HTTP GET for
            getURL = baseURL + segmentName
            # The relative file location and name for the downloaded segment
            print(segmentName)
            fileName = segmentName
            print("GET " + getURL)
            # Do HTTP GET
            urllib.request.urlretrieve(getURL, fileName)
            catSegment(fileName, periodName)

        # Convert period to new resolution
        height = streaminfo.height
        width = streaminfo.width
        fileName_period_converted = representationID + "_period_" + str(periodNumber) + "_" + str(width) + 'x' + str(height) + '.' + origVideoExtention
        fileName_period_MPD = representationID + "_period_" + str(periodNumber) + "_" + str(width) + 'x' + str(height) + '.mpd'
        # Transcode
        scaleSegment(periodName, fileName_period_converted, width, height)

        # Make period
        # TODO: decide segmentsize and fragment size
        makePeriod(fileName_period_converted, fileName_period_MPD, 4000, 2000)

        # Update segmentcount in database
        DB_conn.updateTranscodedSegments(mpd_url, representationName, j)

        # Update final MPD
        # If this is the first period, copy the created MPD
        if (i == 1):
            copyMPD(MPDName, fileName_period_MPD, MPDuration, periodNumber)
            # Notify parent thread that first period is finished
            streaminfo.mpd_url = MPDName
            mpd_available.set()
            # Update time of availibility in database
            now = datetime.now()
            formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
            DB_conn.updateFirstPeriodTime(mpd_url, representationName, formatted_date)

            # Switch the segments per period to a larger number
            segmentsPerPeriod = segmentsInPeriod
            
        # Otherwise, add the created period to the existing MPD
        else:
            addPeriodToMPD(MPDName, fileName_period_MPD, periodNumber)
        
        periodNumber = periodNumber + 1
        i = j + 1

    # Transcoding complete, decrease load counter
    decreaseLoadCounter()

# This method will use already cached video segments to transcode them to a new resolution
def GetSegmentsExistingStream(mpd_url, streaminfo, segmentsPerPeriod):
    try:
        addRepresentationToStreamMap(mpd_url, streaminfo.width, streaminfo.height)
        # Add representation to database
        now = datetime.now()
        formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
        representationName = streaminfo.height + "x" + streaminfo.width
        numberOfSegments = getNumberOfSegments(mpd_url)
        DB_conn.addTranscoding(mpd_url, representationName, numberOfSegments, 0, formatted_date)

        numberOfSegments = 0
        periodBaseName = ""
        periodNameEnd = ""
        stream_name = ""
        MPDName = ""

        # Get the needed information out of the stream map
        with open(rootDir + streamMapName) as map:
            mapData = json.load(map)
            # loop through all the streams to find the correct one
            streamList = mapData["streamList"]
            for stream in streamList:
                if stream["mpd_url"] == mpd_url:
                    numberOfSegments = stream["numberOfSegments"]
                    periodBaseName = stream["periodBaseName"]
                    periodNameEnd = stream["periodNameEnd"]
                    stream_name = stream["stream_name"]
                    MPDName = stream["MPDName"]
                    break

        # Change working directory to cached video directory
        streamDir = rootDir + stream_name
        os.chdir(streamDir)

        # Segmentcounter
        i = 1
        # Period counter
        periodNumber = 0

        # Set the segments per period
        # initially use the number of segments for the first period
        # afterwards switch to the segments in period
        # this will reduce initial startup time of the stream
        segmentsPerPeriod = segmentsFirstPeriod

        # Init segment is 0, so start at 1 for data segments
        while(i < numberOfSegments):
            # We already concatenated the needed segments in GetSegmentsV2 when this stream was first cached
            # We only need to take that video and transcode it again to a new resolution
            periodName = periodBaseName + str(periodNumber) + "." + periodNameEnd

            # Convert period to new resolution
            height = streaminfo.height
            width = streaminfo.width
            # Name of the transcoded video
            fileName_period_converted = periodBaseName + str(periodNumber) + "_" + str(width) + 'x' + str(height) + "." + periodNameEnd
            fileName_period_MPD = periodBaseName + str(periodNumber) + "_" + str(width) + 'x' + str(height) + '.mpd'
            # Transcode
            print("Period video name: " + periodName)
            print("Period converted name: " + fileName_period_converted)
            scaleSegment(periodName, fileName_period_converted, width, height)

            # Make period
            # TODO: decide segmentsize and fragment size
            makePeriod(fileName_period_converted, fileName_period_MPD, 4000, 2000)

            # Add representation to the existing MPD
            addRepresentationToMPD(MPDName, fileName_period_MPD, periodNumber)

            # Update segmentcount in database
            DB_conn.updateTranscodedSegments(mpd_url, representationName, i)

            i = i + segmentsPerPeriod

            # Check if this was the first period
            if periodNumber == 0:
                # Switch the segments per period to a larger number
                segmentsPerPeriod = segmentsInPeriod

            periodNumber = periodNumber + 1

        # Transcoding complete, decrease load counter
        decreaseLoadCounter()

    except Exception as err:
        print(err)
        decreaseLoadCounter()


# Finds the highest quality stream in MPD according to it's bandwidth
def MPD_FindHighestStream(mpd_representations):
    highestBandwidth = 0
    highestStream = None
    for rep in mpd_representations:
        if rep.bandwidth > highestBandwidth:
            highestBandwidth = rep.bandwidth
            highestStream = rep

    return highestStream


# Find the base url of the mpd file
def findBaseURL(mpd_url):
    split = mpd_url.split("/")
    # Append everything except last split
    append = ""
    for i in range(0, len(split) - 1):
        append += split[i] + "/"

    return append


def parseMPD(mpd_url, stream_name, streaminfo, mpd_available, streamDir):
    mpd = MPEGDASHParser.parse(mpd_url)
    mpd_representations = mpd.periods[0].adaptation_sets[0].representations
    stream = MPD_FindHighestStream(mpd_representations)
    representationID = stream.id
    mpd_segment_template_string = mpd.periods[0].adaptation_sets[0].segment_templates[0].media
    try:
        base_stream_url = mpd.base_urls[0].base_url_value
    except:
        print("MPD base URL error")
        base_stream_url = ""

    base_site_url = findBaseURL(mpd_url)
    base_url_final = base_site_url + base_stream_url

    initSegmentTemplate = mpd.periods[0].adaptation_sets[0].segment_templates[0].initialization

    # Calculate the duration of the video in seconds
    durationHMS = isodate.parse_duration(mpd.media_presentation_duration)
    durationS = durationHMS.total_seconds()
    # Segment duration in frames
    segmentDurationF = mpd.periods[0].adaptation_sets[0].segment_templates[0].duration
    FPS = mpd.periods[0].adaptation_sets[0].segment_templates[0].timescale
    # Segment duration in seconds
    segmentDurationS = segmentDurationF / FPS
    # Number of segments
    nSegments = durationS / segmentDurationS
    nSegments = math.ceil(nSegments)
    print(nSegments)

    GetSegmentsV2(base_url_final, representationID+"/", nSegments, mpd_segment_template_string, representationID, initSegmentTemplate, 4, mpd.media_presentation_duration, stream_name, streaminfo, mpd_available, streamDir, mpd_url)


# This is the start of the thread that downloads videos and transcodes them
def startStream(mpd_url, streaminfo, mpd_available):
    # TRANSCODING DECISION
    # First, check if the stream already exists locally
    if streamInMap(mpd_url) and currentLoad < maxLoad:
        # Check if cached stream is the same as requested
        if not isCachedEqual(mpd_url, streaminfo):
            # Transcode cached stream
            # While the client is wachting the cached stream, the server will start transcoding the again to the clients preferred quality
            # We start a new thread
            increaseLoadCounter()
            thread = threading.Thread(target=GetSegmentsExistingStream, args=(mpd_url, streaminfo, 4))
            print("Starting thread")
            thread.start()
        # We return the existing stream, so that the client instantly can start watching the cached stream
        returnExistingStream(mpd_url, streaminfo, mpd_available)

    elif streamInMap(mpd_url) and currentLoad >= maxLoad:
        # Stream is cached but server load is too high
        # If requested resolution is lower than (or the same as) cached resolution, respond with local MPD
        # If requested resolution is higher than cached resolution, respond with origin MPD
        if isCachedStreamHigher(mpd_url, streaminfo):
            # Do not transcode cached stream, but return local MPD
            returnExistingStream(mpd_url, streaminfo, mpd_available)
        
        else:
            # Do not transcode stream, return origin MPD
            streaminfo.mpd_url = mpd_url
            mpd_available.set()

    elif currentLoad >= maxLoad:
        # Video is not cached and server is at max load
        # Do not start transcoding and respond with origin MPD
        streaminfo.mpd_url = mpd_url
        mpd_available.set()

    else: 
        # Make new directory for all files
        mpd_url_split = mpd_url.split("/")
        # Last element is MPD name
        mpd_name = mpd_url_split[-1]
        # Stream name will be MPD name without the MPD extention
        mpd_name_split = mpd_name.split(".")
        stream_name = mpd_name_split[0]

        # Make a directory for the stream and change working directory
        streamDir = rootDir + stream_name
        os.mkdir(streamDir)
        os.chdir(streamDir)

        streaminfo.stream_name = stream_name

        # Start parsing and transcoding
        increaseLoadCounter()
        try:
            parseMPD(mpd_url,stream_name, streaminfo, mpd_available, streamDir)
        except Exception as err:
            print(err)
            decreaseLoadCounter()


# parseMPD(mpd_url)
# startStream(mpd_url)

'''
# tread test
def main():
    streaminfo = Stream_Info()
    mpd_available = threading.Event()
    thread = threading.Thread(target=startStream, args=(mpd_url, streaminfo, mpd_available))
    thread.start()

    # wait here for the result to be available before continuing
    mpd_available.wait()

    print('The result is', streaminfo.mpd_url)

if __name__ == '__main__':
    main()
'''

# GetSegments('https://dash.akamaized.net/akamai/bbb_30fps/bbb_30fps_3840x2160_12000k/','bbb_30fps_3840x2160_12000k_', 'bbb_30fps_3840x2160_12000k/', 2, '.m4v')

'''
durationHMS = isodate.parse_duration(mpd.media_presentation_duration)
durationS = durationHMS.total_seconds()
print(durationS)
'''
