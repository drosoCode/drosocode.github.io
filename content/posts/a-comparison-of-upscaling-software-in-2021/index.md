---
title: "A comparison of upscaling software in 2021"
date: 2022-01-14T00:00:00+01:00
draft: false
tags:
- docker
- python
resources:
- src: assets/ds_1.jpg
  name: ds
  title: The DS booting with linux and connecting to WiFi
- src: assets/ds_2.jpg
  name: ds
  title: The DS connected to the container with the control interface
---

A few months ago, I started to search for some upscaling software to integrate into Zogwine, my media center with the goal of upscaling some of my old animes either on the fly or via some kind of preprocessing. I found quite a lot of projects on github, and especially the [Video2X](https://github.com/k4yt3x/video2x) project which gathered many different projects and versions. So I decided to do a quick benchmark to decide which one to use. I would also recommend you to read this excellent [article](https://medium.com/crunchyroll/scaling-up-anime-with-machine-learning-and-smart-real-time-algorithms-2fb706ec56c0) from crunchyroll’s tech blog where they did their own tests for upscaling.

## Presentation of the benchmarked solutions

I used the version [4.6.0](https://github.com/k4yt3x/video2x/releases/tag/4.6.0) of [Video2X](https://github.com/k4yt3x/video2x) and the version [3.3.1](https://github.com/akai-katto/dandere2x/releases/tag/3.3.1) of [dandere2X](https://github.com/akai-katto/dandere2x).

dandere2x is a faster version of [Waifu2X](https://github.com/nagadomi/waifu2x), an upscaling software targeted to anime-style images and using a CNN approach.

Video2X allows to use different upscaling software from the same interface. I have decided to test the following:
- [Anime4KCPP](https://github.com/TianZerL/Anime4KCPP) an algorithmic approach to upscale anime-style images, based on the [Anime4K](https://github.com/bloc97/Anime4K) algorithm
- Anime4KCPP_GPU Anime4KCPP in GPU mode
- Anime4KCPP_GPU_CNN Anime4KCPP with a CNN based algorithm and running on the GPU
- [REALSR_NCNN_VULKAN](https://github.com/nihui/realsr-ncnn-vulkan) an implementation of [RealSR](https://github.com/jixiaozhong/RealSR) using the [NCNN](https://github.com/Tencent/ncnn) project and the Vulkan API
- [SRMD_NCNN_VULKAN](https://github.com/nihui/srmd-ncnn-vulkan) an implementation of [SRMD](https://github.com/cszn/SRMD) using the NCNN project and the Vulkan API
- [Waifu2X_NCNN_VULKAN](https://github.com/nihui/waifu2x-ncnn-vulkan) an implementation of [Waifu2X](https://github.com/nagadomi/waifu2x) using NCNN and the Vulkan API
- [Waifu2X_CAFFE_CUNET](https://github.com/lltcggie/waifu2x-caffe) a Waifu2X implementation using [Caffe](https://github.com/BVLC/caffe) and the CUDA API
- Waifu2X_CAFFE_UPRESNET10 the upresnet10 model for Waifu2X-Caffe running on the GPU
- Waifu2X_CAFFE_ANIME_STYLE_ART_RGB the anime_style_art_rgb model for Waifu2X-Caffe running on the GPU
- [Waifu2X_CPP_CONVERTER](https://github.com/WL-Amigo/waifu2x-converter-cpp) Waifu2X C++ implementation running on the GPU

You can find additional information on the different Waifu2X-Caffe models [here](https://www.reddit.com/r/waifu2x/comments/c3v38r/whats_the_difference_between_the_models/).

All the tests were ran using an X3 upscale ratio, to go from a 480p video to a 1440p video on a configuration with a Ryzen 7 5800X, 16GB RAM and an RTX 2070. Each upscale was run with this configuration without any other significant software running in the meantime. 

The input video was a 480p version of the 4th opening of Naruto Shippuden. The images shown here are only for educational purposes and belongs to their respective copyright owners.

## Gathering Results

To process the results and compare the different solutions, I created a python script to extract a few frames (158, 500, 835, 1090, 1200 and 2200) for each video using ffmpeg.

```python
import os

FRAMES = [158, 500, 835, 1090, 1200, 2200]

def extractFrames(path, f, offset=0):
    print("extracting frames for: "+f)
    for i in FRAMES:
        os.system('ffmpeg -i "'+f+'" -vf "select=gte(n\,'+str(i+offset)+')" -vframes 1 '+path+'/frame_'+str(i+offset)+'.png ')

base = os.getcwd()
for dir in os.listdir(base):
    path = os.path.join(base, dir)
    if os.path.isdir(path):
        for file in os.listdir(path):
            if file.endswith(".mkv") or file.endswith(".mp4"):
                extractFrames(path, os.path.join(path, file))
                break
    elif path.endswith(".mkv") or path.endswith(".mp4"):
        extractFrames(base, path, -1)
```

In addition to this, I also executed the [VMAF](https://github.com/Netflix/vmaf) tool from Netflix to get some quality indicator for each video (compared to the original) using the [easy-vmaf](https://github.com/gdavila/easyVmaf) docker image like this: `docker run –rm -v /srv/Documents/test_upscaling:/vid gfdavila/easyvmaf -r /vid/nt_op_480.mkv -d /vid/upscale_video2x_waifu2x_ncnn_vulkan/n_op_1440.mp4`.

I then graphed the results of `pooled_metrics > vmaf > harmonic_mean` for each method compared to their execution time. Here is the result:

{{< image src="assets/result.png" caption="VMAF score and processing time for each upscaling solution" width="90%" >}}

[DOWNLOAD xls file](assets/results.xlsx)

## Conclusions

The input video has a length of 90 seconds, so for a real time upscaling system, only anime4KCPP qualifies. We can also note that a [GLSL implementation](https://github.com/TianZerL/ACNetGLSL) of Anime4K exists which opens the door to client-side upscaling.

We can exclude the implementations with a time greater than 4000s as more than 1 hour to process a 1min30 video is wayy too long.

For real time upscaling the most efficient version seems to be video2x_anime4KCPP_cnn_gpu while dandere2x_waifu2x_caffe seems to bring the best quality for the lowest execution time among the potential pre-processing upscaling.

{{< image src="assets/original_anime4kcpp_gpu_anime4kcpp_cnn.png" caption="Original vs Anime4KCPP_gpu vs Anime4KCPP_cnn_gpu" width="90%" >}}

We can see here that the cnn version of anime4KCPP brings quite interesting improvements with smoother curves while anime4KCPP_gpu ends up outputting a more blurry image than the original.

{{< image src="assets/original_vs_anime4k_cnn.png" caption="Original vs Anime4KCPP_cnn_gpu" width="90%" >}}

We can note that while the image improvements are minor with Anime4KCPP_cnn_gpu, the this is not the case for the text, which is way more readable in the upscaled version.

{{< image src="assets/og_realsr_srmd_cunet_rgb_dandere.png" caption="Original vs RealSR vs SRMD | Waifu2x_cunet vs Waifu2x_anime_style_art_rgb vs dandere2x" width="90%">}}

{{< image src="assets/original_dandere.png" caption="Original vs dandere2x" width="90%" >}}

In opposition to the anime4K performance for the image, we can see some really impressive improvements with an image without any major pixelation for each Waifu2X methods. With the lowsest execution time among the non-realtime candidates, dandere2x is the clear winner of this benchmark.

## General Conclusion

With this benchmark, I was able to determine the best upscaling software to use for my mediacenter. Anime4KCPP with the CNN version seems to be the best possible result for a realtime upscaling. While this remains an option, I don’t think that this feature would be implemented in the near future, as the benefits are quite thin. 

However, I discovered a very interesting option for a pre-processing feature (the file would be upscaled in background and not in realtime), dandere2x which proved to bring really impressive results. But while this solution is the fastest for non-realtime upscaling, this would still take more than 5 hours to upscale a single episode. This could be implemented as a feature that allows to upscale only a few selected files, a distributed system may also be a good lead if you have multiple powerful computers at home.