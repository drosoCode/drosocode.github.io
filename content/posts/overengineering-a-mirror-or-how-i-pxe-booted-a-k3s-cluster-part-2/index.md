---
title: "Overengineering a mirror - Part 2: Setting up the hardware"
date: 2026-09-13T01:00:00+00:00
draft: true
tags:
- hardware
- infra
- k8s
---

While the cluster is now ready, we still need to do all the hardware parts before integrating everything. More specifically, we need to figure out how to capture video from the kinect, how to mount the kinect to the tv and how to make some space in the room.

This is the second out of 3 of this posts series:
- [Part 1: Network Booting](/2026/09/13/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster/)
- Part 2: Hardware Setup
- Part 3: K8s Deployment

## Getting video from the Kinect

So, the first step is to connect the Kinect to our PC and get some output, ideally with a low-enough latency and in an easy-to-use form.

### Kinect V1 and V2 comparison

There are two "main" revisions of the Kinect (we're excluding the xbox vs windows versions as they are basically the same except for the cable):

- The Kinect V1 released in 2010 with the Xbox 360
- The Kinect V2 released in 2013 with the Xbox One

Of course, the main characteristic of the Kinect is that it's not a "simple" camera, but rather a device composed of:
- A color camera (480p for the V1 and 1080p for the V2)
- A microphone array
- A depth-sensor (IR grid + IR camera on the V1, Time of Flight on the V2)
- And of course an SDK that makes the depth data easy to manipulate (like skeleton/joints/hands tracking)

While the SDK is pretty extensive and easy to use on Windows, on Linux it's a totally different story.

There are very old frameworks called [OpenNI](https://github.com/OpenNI/OpenNI) / [OpenNI2](https://github.com/OpenNI/OpenNI2) (for the v1 and V2 respectively), with [modules for the v1](https://github.com/PrimeSense/Sensor). But the actual algorithms used to make the joints tracking easy to use are in another piece of software called NITE, which was always closed-source (and is now long dead). Furthermore, when Apple acquired PrimeSense (the company that manufactured the kinect's sensors, which is basically the same tech as FaceID), they took down all the websites (for example [openni.org](https://www.openni.org/) now redirects to their website).

So you can basically forget taking advantage of the tracking algos on Linux (and the progress of AI models makes this less and less interesting anyways).

Fortunately, there was an opensource implementation effort to get at least basic data from the sensors with:
- [libfreenect](https://github.com/OpenKinect/libfreenect) for the V1
- [libfreenect2](https://github.com/OpenKinect/libfreenect2) for the V2



### Compiling libfreenect2

### Adding a frame grabber

### Building the docker container

