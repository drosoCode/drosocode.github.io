#!/bin/bash

if [ -z $RTSP_URL ]; then
    /app/frame_grabber | ffplay -autoexit -max_delay 0 -max_probe_packets 1 -analyzeduration 0 -flags +low_delay -fflags +nobuffer -f rawvideo -pixel_format bgra -video_size 1920x1080 -
else
    sleep 2
    /app/frame_grabber | ffmpeg -re -pix_fmt bgra -f rawvideo -video_size 1920x1080 -i pipe: -f rawvideo - -c:v libx264 -preset ultrafast -f rtsp $RTSP_URL -rtsp_transport tcp | ffplay -autoexit -max_delay 0 -max_probe_packets 1 -analyzeduration 0 -flags +low_delay -fflags +nobuffer -f rawvideo -pixel_format bgra -video_size 1920x1080 -
fi
