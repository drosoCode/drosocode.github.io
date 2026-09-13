---
title: "Overengineering a mirror - Part 2: Setting up the hardware"
date: 2026-09-13T01:00:00+00:00
draft: true
tags:
- hardware
- infra
- k8s
---

While the cluster is now ready to support our kinect, we still need to figure out how to actually grab the video from it and restream it to the TV with a low latency.

This is the second out of 3 of this posts series:
- [Part 1: Network Booting](/2026/09/13/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster/)
- Part 2: Hardware Setup
- Part 3: K8s Deployment

## Getting video from the Kinect

### Kinect V1 and V2 comparison

### Compiling libfreenect2

### Adding a frame grabber

### Building the docker container

