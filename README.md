### Copy Live Manifest Tool

DVR an HLS live manifest onto your computer. Polls and downloads the manifest and fragments with python then runs FFMpeg to create one single video at the end. Manifest downloaded can be served as separate [event-type playlist](https://developer.apple.com/documentation/http_live_streaming/example_playlists_for_http_live_streaming/event_playlist_construction) from `manifest/level.m3u8`


### Usage

* Have ffmpeg installed
* Create an empty manifest directory in the project oot
* Run `python3 main.py`
* Paste the level manifest url of your choice
* Optionally enter a referrer to be passed with the level and frag requests
* Specify how long (in hours) to dvr before stopping
* Enter `y` to log debug output to a file instead of the terminal
