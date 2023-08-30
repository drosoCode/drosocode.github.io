---
title: "Wake on Lan and Dual Boot"
date: 2020-10-06T00:00:00+01:00
draft: false
tags:
- arduino
- boostrap
- c++
- cordova
- web
- wol
- hardware
resources:
- src: assets/app.png
  name: ui
  title: Mobile App
- src: assets/web.png
  name: ui
  title: Web UI
---

## Introduction

Wake on Lan is a technology delvelopped in 1995, that allows you to start a computer by sending a magic packet (usually in udp). I use it since a few years and it is especially useful when you are in a remote place, you can just start your computer and connect to it through rdp. The only problem is that this approach is not really suitable for dual-boot setups.

## The Problem

Sometimes, I need to run linux process that are using the GPU, so until the gpu support is added to the WSL2, a dual-boot is mandatory for me. However, a magic packet allows you to start you computer but you have no way to interact with it until the os is fully started. So it’s impossible to access boot menu using wake on lan.

## The Solution

So, if it’s impossible to do it in software, let’s use some hardware ! Our setup will be very simple: an Arduino Leonardo and an Ethernet Shield. Why a leonardo and not a uno or a nano ? Because, the Arduino Leonardo have a different kind of usb controller that allows to emulate an HID device, especially a keyboard in our case.

{{< image src="assets/arduino.jpg" caption="Arduino Leonardo with Ethernet shield" width="30%" >}}

The idea is to connect an ethernet shield to this arduino, so that we can send an http request with the os to start. The arduino will then send a magic packet (which is really simple to create as it is composed of 6x “FF” and 16x the mac address of the computer), wait for a predetermined amount of time (time to show the os selection screen), and then emulate the up/down/enter keys to select the correct os.

{{< file "content/posts/wake-on-lan-and-dual-boot/main.ino" >}}


With this simple code, the arduino will start an http server on port 80, and listen for simple commands like `2/start` to start linux of `1/stop` to stop windows, we can even serve a very simple ui on the default page.

I could have stopped there, but I decided to create a simple app for my phone, to easily wake-up the computer. For this really quick project, I used Apache Cordova (though I don’t recommand using it for real projects) and bootstrap. And a few lines of html later, there is our app !

{{< gallery id="ui" >}}

## Conclusion

So with less than $50, you can create a Wake On Lan device that supports multi-os systems. You could even bring wake up support to an incompatible computer using a realy or an optocoupler to “manually push the button”.