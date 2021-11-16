# On-the-fly DASH transcoder
# Introduction:

The docker-compose uses 4 images
    -mysql
    -phpmyAdmin
    -transcoder
    -dashboard
    
Things are hardcoded to work for localhost to work around CORS.



# Immportant addresses and ports:


Nginx uses port 8000, segments and .mpd are generated in the /dash/ directory:
localhost:8000/dash/

The client file hosted by the Nginx server is located at:
localhost:8000/dash/client.html

The PHPMyAdmin container is used to manage the database, but is not needed to run the project.
PHPMyAdmin uses port 8183. Uses the following default credentials:
server: mysql
user: root
password: root

localhost:8183


The dashboard uses port 8080:
localhost:8080


The Flask server uses port 5000 using uWSGI



-----------------------------------------------------------------------------------------------------------------------------------------------------------

# How to run

Step 1: build the image for the dasboard
---

navigate to /dashboard/
There you find a Dockerfile for the dashboard

docker build --tag dashboard .


Step 2: Image voor transcoder builden
---

Navigate to /bach-transcoder/
Dockerfile for the transcoder

docker build --tag transcoder .


Step 3: Docker-compose
---

Navigate to /bach-transcoder/db/
In this directory there is the docker-compose.yml file. This file combines all the images.

docker-compose up
