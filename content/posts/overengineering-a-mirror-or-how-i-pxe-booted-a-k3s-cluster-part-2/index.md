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
- And of course an associated SDK that makes the depth data easy to manipulate (like skeleton/joints/hands tracking)

While the SDK is pretty extensive and easy to use on Windows, on Linux it's a totally different story.

There are very old frameworks called [OpenNI](https://github.com/OpenNI/OpenNI) / [OpenNI2](https://github.com/OpenNI/OpenNI2) (for the v1 and V2 respectively), with [modules for the v1](https://github.com/PrimeSense/Sensor). But the actual algorithms used to make the joints tracking easy to use are in another piece of software called NITE, which was always closed-source (and is now long dead). Furthermore, when Apple acquired PrimeSense (the company that manufactured the kinect's sensors, which is basically the same tech as FaceID), they took down all the websites (for example [openni.org](https://www.openni.org/) now redirects to their website).

So you unless you want to struggle to compile decades-old and unmaintained software, you can pretty much forget taking advantage of the tracking algos on Linux (and the progress of specialized AI models makes this less and less interesting anyways).

Fortunately, there was an opensource implementation effort to get at least basic data from the sensors with:
- [libfreenect](https://github.com/OpenKinect/libfreenect) for the V1
- [libfreenect2](https://github.com/OpenKinect/libfreenect2) for the V2

I have both models at home, and use the V1 as my desktop webcam since the resolution doesn't matter that much for this use case, however I definitely want to use the V2 for displaying on a TV.

Getting video for the V1 is as easy as installing libfreenect: `yay -S libfreenect`.

Then after plugging the Kinect a new video device appears, so you can directly use this in any software that supports using `/dev/videoX` devices (ex: `ffplay /dev/video0`).

For the V2, it's a bit more complicated, as the AUR package doesn't compiles (and ideally, I want this in a debian container). So let's take a closer look.

Another thing to keep in mind is that the V2 requires a much higher USB bandwidth, so **USB 3** ports are required. I tested with a RPi 4, but it still struggled to keep a decent framerate, so I switched to the dell mini-pc.

### Compiling libfreenect2

We can use the [PKGBUILD](https://aur.archlinux.org/cgit/aur.git/tree/PKGBUILD?h=libfreenect2) file of the [AUR package](https://aur.archlinux.org/packages/libfreenect2) as a reference for installation instructions.

Some comments on the package's page suggests to add `DCMAKE_POLICY_VERSION_MINIMUM=3.5` to CMake options to fix the current issues.

I faced another error, this time during compilation and found that commenting out `s:const int CL_ICDL_Version` fixed this issue.

So after installing the deps and cloning the repo:
- `apt-get install -y build-essential git cmake opencl-headers pkg-config libjpeg62-turbo-dev libturbojpeg0-dev libusb-1.0-0-dev libglfw3-dev ocl-icd-opencl-dev libopencv-dev`
- `git clone https://github.com/OpenKinect/libfreenect2 /tmp/libfreenect2 &&	cd /tmp/libfreenect2/ && git checkout fd64c5d9b214df6f6a55b4419357e51083f15d93`

We can finally compile libfreenect2:

```bash
cd /tmp/libfreenect2 && mkdir build && cd build
sed --debug -i -e 's:const int CL_ICDL_VERSION:// const int CL_ICDL_VERSION:' "../src/opencl_depth_packet_processor.cpp" "../src/opencl_kde_depth_packet_processor.cpp" && \
cmake ".." \
		-DCMAKE_INSTALL_PREFIX=/usr \
		-DCMAKE_BUILD_TYPE=Release \
		-DENABLE_CXX11=ON \
		-DENABLE_OPENCL=ON \
		-DENABLE_OPENGL=OFF \
		-DENABLE_CUDA=OFF \
		-DBUILD_EXAMPLES=OFF \
		-DBUILD_SHARED_LIBS=OFF \
		-DCMAKE_POLICY_VERSION_MINIMUM=3.5 && \
	make
```

After running `make install` you should be able to execute the demo program with: `/usr/bin/Protonect`.
If everything went well, you should now see a window with the live images for the multiple kinect's sensors.

### Adding a frame grabber

But it's not yet finished for the video acquisition part as, unlike the KinectV1, the V2's libfreenect doesn't provides a `/dev/videoX` device from which we can easily grab the frames.

Considering we only want to restream the color camera's video to the tv (with low latency), we just need to find a way to capture the raw frames from the kinect and *somehow* put them in the video framebuffer.

Reading the issues and pull-requests on the libfreenectv2 repo regarding this matter, I found the following [PR](https://github.com/OpenKinect/libfreenect2/pull/1197) from which I copied most of my code.

I slightly modified it to directly write the raw frames to stdout (the logs are sent to stderr), remove the dependency on opencv for color space conversion (and also add a frame limiter, but this was mostly used for testing).

Now, we just need to add this file and the CMakeLists file in a `frame_grabber` folder and reference our project in the main CMakeLists file with `ADD_SUBDIRECTORY(\${MY_DIR}/examples/frame_grabber)` for it to be build during libfreenect2 compilation.

{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster-part-2/assets/kinect/frame_grabber.cpp" >}}

{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster-part-2/assets/kinect/CMakeLists.txt" >}}


### Usage

Our frame_grabber is now outputing the raw color frames from the kinect. To display them, we can use `ffplay` (part of [ffmpeg](https://ffmpeg.org/ffplay.html)), since there's no encoding, we need to specify the characteristics of the video directly to ffplay as cli args.

The following command can be used to display the video: `./frame_grabber | ffplay -f rawvideo -pixel_format bgra -video_size 1920x1080 -` (note the `-` at the end to get the video from the stdin).

We can add a few other parameters to reduce latency (honestly I don't know which ones are really useful, but I'm too lazy to test them independently): `./frame_grabber | ffplay -autoexit -max_delay 0 -max_probe_packets 1 -analyzeduration 0 -flags +low_delay -fflags +nobuffer -f rawvideo -pixel_format bgra -video_size 1920x1080 -`

By default, ffplay will display the video in a new window if running with a desktop environment, but otherwise it will directly display the video on the framebuffer of a connected screen (which is exactly what we want !).

As a bonus, we can also first pipe the frames through ffmpeg and then to ffplay, that way the video is displayed on the tv in realtime but can also be encoded and streamed to other devices (ex: for recording).

To allow both modes, I created this simple script (controlled by an env var):

{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster-part-2/assets/kinect/launch.sh" >}}


### Building the docker container

Now that everything is working, let's package everything nicely as a docker container.

I'm using a two-stage build process: the first one to clone, patch and build libfreenect with our frame_grabber, and the second one to make a small image to deploy with only the required libs at runtime and our litte startup script.

{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster-part-2/assets/kinect/Dockerfile" >}}



## References
- https://aur.archlinux.org/packages/libfreenect2
- 
