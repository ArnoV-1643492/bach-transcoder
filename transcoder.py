from mpegdash.parser import MPEGDASHParser
import urllib
import ffmpeg
import isodate
import datetime
import math
import os
import subprocess
# from h26x_extractor import h26x_parser

# get current directory
dir_path = os.path.dirname(os.path.realpath(__file__))
print("------------------------------------------------")
print(dir_path)
print("------------------------------------------------")
# change working directory
os.chdir("/usr/share/nginx/html/")

mpd_url = 'https://dash.akamaized.net/akamai/bbb_30fps/bbb_30fps.mpd'
# mpd_url = 'https://bitmovin-a.akamaihd.net/content/MI201109210084_1/mpds/f08e80da-bf1d-4e3d-8899-f0f6155f6efa.mpd'


# Scale the segment to a different resolution
def scaleSegment(inputSeg, outputSeg, output_width, output_height):
    stream = ffmpeg.input(inputSeg)
    stream = ffmpeg.filter(stream, 'scale', width=output_width, height=output_height)
    stream = ffmpeg.output(stream, outputSeg)
    ffmpeg.run(stream)


# Concatenate a segment to the initial segment
def catSegment(initSegment, segment, outputName):
    with open(initSegment, "rb") as initFile, open(segment, "rb") as vidFile, open(outputName, "ab") as outputFile:
        outputFile.write(initFile.read())
        outputFile.write(vidFile.read())


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
        catSegment(fileName_init, fileName, fileName_seg_initialised)

        fileName_seg_converted = baseWriteLocation + fileNameTemplate + str(i) + '_converted' + containerExtention
        scaleSegment(fileName_seg_initialised, fileName_seg_converted, 480, 360)


# HTTP GETs all the segments and saves them on disc
def GetSegmentsV2(baseURL, baseWriteLocation, numberOfSegments, segmentTemplate, representationID, initSegmentTemplate):
    
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

    # Init segment is 0, so start at 1 for data segments
    for i in range(1,numberOfSegments):
        segmentName = BaseSegmentName.replace("$Number$", str(i))
        # The file we will call HTTP GET for
        getURL = baseURL + segmentName
        # The relative file location and name for the downloaded segment
        print(segmentName)
        fileName = segmentName
        print("GET " + getURL)
        # Do HTTP GET
        urllib.request.urlretrieve(getURL, fileName)

        # TODO: start a new thread here that transcodes the download file
        fileNameSplit = fileName.split(".")
        fileName_seg_initialised = ""
        for i in range(len(fileNameSplit) -2):
            fileName_seg_initialised += fileNameSplit[i] + "."
        fileName_seg_initialised += fileNameSplit[len(fileNameSplit) - 2] + '_initialised' + '.' + fileNameSplit[len(fileNameSplit) - 1]
        catSegment(fileName_init, fileName, fileName_seg_initialised)

        # Convert segments to new resolution
        height = 360
        width = 480
        fileName_seg_converted = fileNameSplit[len(fileNameSplit) - 2] + '_converted_' + str(width) + 'x' + str(height) + '.' + fileNameSplit[len(fileNameSplit) - 1]
        
        # ts test
        # fileName_seg_converted = fileNameSplit[len(fileNameSplit) - 2] + '_converted_' + str(width) + 'x' + str(height) + '.' + 'ts'
        # out = subprocess.run(["ffmpeg","-i",fileName_seg_initialised,"-filter","scale=480:360","-vb","20M","-c:a","copy",fileName_seg_converted])

        scaleSegment(fileName_seg_initialised, fileName_seg_converted, width, height)

        # remove init data from segment
        '''with open(fileName_seg_converted, 'r') as fin:
            data = fin.read().splitlines(True)
        with open(fileName_seg_converted, 'w') as fout:
            fout.writelines(data[1:])
        # with open(fileName_seg_converted, "rb") as videoInit:
        # create parser
        ex = h26x_parser.H26xParser(f=fileName_seg_converted, verbose=True)
        ex.parse()'''


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


def parseMPD(mpd_url):
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

    GetSegmentsV2(base_url_final, representationID+"/", nSegments, mpd_segment_template_string, representationID, initSegmentTemplate)


parseMPD(mpd_url)

# GetSegments('https://dash.akamaized.net/akamai/bbb_30fps/bbb_30fps_3840x2160_12000k/','bbb_30fps_3840x2160_12000k_', 'bbb_30fps_3840x2160_12000k/', 2, '.m4v')

'''
durationHMS = isodate.parse_duration(mpd.media_presentation_duration)
durationS = durationHMS.total_seconds()
print(durationS)
'''
