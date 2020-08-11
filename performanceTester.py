import requests

n = 20
qualities = [[2560,1140],[1920,1080],[1280,720],[640,360]]

server = 'http://localhost:5000/media/'

for rep in qualities:
    print(rep)
    val = {'MPD_URL': 'http://192.168.1.115/dash/bbb_30fps.mpd', 'WANTED_WIDTH': str(rep[0]), 'WANTED_HEIGHT': str(rep[1])}
    for i in range(0,n):
        print(i)
        r = requests.post(server, json=val)
        print(r.text)