from DB_login import *

import mysql.connector
from mysql.connector import errorcode

from datetime import datetime

import json

# Adds a new row in the transcoding table
# mpd_url and representation: string
# numberOfSegments and segmentTranscoded: int
# requestTime: date
def addTranscoding(mpd_url, representation, numberOfSegments, segmentsTranscoded, requestTime, durationS):
    # connect to database
    try:
        conn = mysql.connector.connect(user=user, password=password, host=host, port=port, database=database)
        cursor = conn.cursor()

        # create insert
        add = ("INSERT INTO transcoding "
                "(mpd_url, representation, numberOfSegments, segmentsTranscoded, requestTime, durationS) "
                "VALUES (%s, %s, %s, %s, %s, %s)")

        data = (mpd_url, representation, numberOfSegments, segmentsTranscoded, requestTime, durationS)

        cursor.execute(add, data)

        conn.commit()
        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)

def updateTranscodedSegments(mpd_url, representation, segmentsTranscoded):
    # connect to database
    try:
        conn = mysql.connector.connect(user=user, password=password, host=host, port=port, database=database)
        cursor = conn.cursor()

        # create insert
        add = ("UPDATE transcoding "
                "SET segmentsTranscoded = %s "
                "WHERE (mpd_url = %s AND representation = %s) ")

        data = (segmentsTranscoded, mpd_url, representation)

        cursor.execute(add, data)

        conn.commit()
        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)

def updateFirstPeriodTime(mpd_url, representation, firstPeriodTime):
    # connect to database
    try:
        conn = mysql.connector.connect(user=user, password=password, host=host, port=port, database=database)
        cursor = conn.cursor()

        # create insert
        add = ("UPDATE transcoding "
                "SET firstPeriodTime = %s "
                "WHERE (mpd_url = %s AND representation = %s) ")

        data = (firstPeriodTime, mpd_url, representation)

        cursor.execute(add, data)

        conn.commit()
        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)


def updateDownloadTime(mpd_url, representation, downloadTime):
    # connect to database
    try:
        conn = mysql.connector.connect(user=user, password=password, host=host, port=port, database=database)
        cursor = conn.cursor()

        # create insert
        add = ("UPDATE transcoding "
                "SET downloadTime = %s "
                "WHERE (mpd_url = %s AND representation = %s) ")

        data = (downloadTime, mpd_url, representation)

        cursor.execute(add, data)

        conn.commit()
        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)


# Gets total response time in seconds
def getFirstPeriodTime():
    # connect to database
    try:
        conn = mysql.connector.connect(user=user, password=password, host=host, port=port, database=database)
        cursor = conn.cursor()

        # create insert
        query = ("SELECT requestTime, firstPeriodTime FROM transcoding "
                "WHERE firstPeriodTime IS NOT NULL")

        cursor.execute(query)

        # Find the difference between all
        diff_list = []
        for (requestTime, firstPeriodTime) in cursor:
            diff_list.append((firstPeriodTime - requestTime).total_seconds())
        # Calculate average
        average = 0
        for e in diff_list:
            average = average + e

        if (len(diff_list) != 0):
            average = average / len(diff_list)

        conn.commit()
        cursor.close()
        conn.close()

        return average

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)

# Get all the info about all the streams and representations
# TODO: make method that only selects ongoing transcodings and streams
def getStreamsProgressData():
    # connect to database
    try:
        conn = mysql.connector.connect(user=user, password=password, host=host, port=port, database=database)
        cursor = conn.cursor()

        # create insert
        query = ("SELECT mpd_url, representation, numberOfSegments, segmentsTranscoded, requestTime, firstPeriodTime, downloadTime, durationS FROM transcoding ")

        cursor.execute(query)

        # Put results in JSON
        result = []
        for (mpd_url, representation, numberOfSegments, segmentsTranscoded, requestTime, firstPeriodTime, downloadTime, durationS) in cursor:
            # make representation
            percentage = int((segmentsTranscoded / numberOfSegments) * 100)
            timePerSegment = int(durationS / numberOfSegments)
            transcodedInTime = segmentsTranscoded * timePerSegment
            rep = {
                "name": representation,
                "percentage": percentage,
                "transcodedInTime": transcodedInTime,
                "durationS": durationS
            }

            # Add time it took to download segments
            if downloadTime is not None:
                rep["downloadTime"] = (downloadTime - requestTime).total_seconds()

            # Add time it took to transcode segments
            if downloadTime is not None and firstPeriodTime is not None:
                rep["transcodeTime"] = (firstPeriodTime - downloadTime).total_seconds()

            # Add total time it took to process first period
            if firstPeriodTime is not None:
                rep["firstPeriodTime"] = (firstPeriodTime - requestTime).total_seconds()

            # check if mpd already in result
            inResult = False
            for el in result:
                if el["mpd_url"] == mpd_url:
                    inResult = True
                    el["representations"].append(rep)
                    break
            
            if not inResult:
                # stream has not yet been added, add now
                stream = {
                    "representations": [rep],
                    "mpd_url": mpd_url,
                    "numberOfSegments": numberOfSegments,
                    "durationS": durationS,
                    "clients": []
                }
                result.append(stream)

        conn.commit()
        cursor.close()
        cursor = conn.cursor()

        # Now add client status data
        # create query
        query = ("SELECT id, mpd_url, currentTime, ip, width, height FROM clientStatus "
        "WHERE running = 1")

        cursor.execute(query)

        for (id, mpd_url, currentTime, ip, width, height) in cursor:
            # Search for correct mpd
            for el in result:
                if el["mpd_url"] == mpd_url:
                    percentage = 0
                    if el["durationS"] != 0:
                        percentage = int((currentTime / el["durationS"])*100)
                    # Make client
                    client = {
                        "id": id,
                        "ip": ip,
                        "percentage": percentage,
                        "currentTime": currentTime,
                        "durationS": durationS,
                        "width": width,
                        "height": height
                    }
                    el["clients"].append(client)
                    break


        resultJSON = {"streamData": result}


        conn.commit()
        cursor.close()
        conn.close()

        return resultJSON

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)


# Used by client to update its status (current watch time)
def postClientStatus(mpd_url, currentTime, ip, running, width, height):
    # connect to database
    try:
        conn = mysql.connector.connect(user=user, password=password, host=host, port=port, database=database)
        cursor = conn.cursor()

        # create insert
        add = ("INSERT INTO clientStatus "
                "(mpd_url, currentTime, ip, running, width, height) "
                "VALUES (%s, %s, %s, %s, %s, %s)")

        data = (mpd_url, currentTime, ip, running, width, height)

        cursor.execute(add, data)

        conn.commit()

        id = cursor.lastrowid

        cursor.close()
        conn.close()

        return id

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)


# Update the current time of the client
def updateClientCurrTime(id, currentTime):
    # connect to database
    try:
        conn = mysql.connector.connect(user=user, password=password, host=host, port=port, database=database)
        cursor = conn.cursor()
        
        # create insert
        add = ("UPDATE clientStatus "
                "SET currentTime = %s "
                "WHERE id = %s ")

        data = (currentTime, id)

        cursor.execute(add, data)

        conn.commit()
        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)


# Makes running False in clientStatus database
def stopClientStream(id):
    # connect to database
    try:
        conn = mysql.connector.connect(user=user, password=password, host=host, port=port, database=database)
        cursor = conn.cursor()
        
        # create insert
        add = ("UPDATE clientStatus "
                "SET running = %s "
                "WHERE id = %s ")

        data = (False, id)

        cursor.execute(add, data)

        conn.commit()
        cursor.close()
        conn.close()

    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)


now = datetime.now()
formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
# addTranscoding("192.168.1.115/dash/bbb_30fps.mpd", "640x360", 200, 0, formatted_date)
# updateFirstPeriodTime("192.168.1.115/dash/bbb_30fps.mpd", "640x360", formatted_date)
print(getFirstPeriodTime())
print(getStreamsProgressData())

# id= postClientStatus("stream.com/bbb.mpd", 0, "192.168.1.1")
#print(id)
# updateClientCurrTime(id, 2)
#updateDownloadTime("http://192.168.1.115/dash/bbb_30fps.mpd", "1920x1080", formatted_date)