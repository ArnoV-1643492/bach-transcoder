from DB_login import *

import mysql.connector
from mysql.connector import errorcode

from datetime import datetime

# Adds a new row in the transcoding table
# mpd_url and representation: string
# numberOfSegments and segmentTranscoded: int
# requestTime: date
def addTranscoding(mpd_url, representation, numberOfSegments, segmentsTranscoded, requestTime):
    # connect to database
    try:
        conn = mysql.connector.connect(user=user, password=password, host=host, port=port, database=database)
        cursor = conn.cursor()

        # create insert
        add = ("INSERT INTO transcoding "
                "(mpd_url, representation, numberOfSegments, segmentsTranscoded, requestTime) "
                "VALUES (%s, %s, %s, %s, %s)")

        data = (mpd_url, representation, numberOfSegments, segmentsTranscoded, requestTime)

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

now = datetime.now()
formatted_date = now.strftime('%Y-%m-%d %H:%M:%S')
# addTranscoding("192.168.1.115/dash/bbb_30fps.mpd", "640x360", 200, 0, formatted_date)
# updateFirstPeriodTime("192.168.1.115/dash/bbb_30fps.mpd", "640x360", formatted_date)
getFirstPeriodTime()