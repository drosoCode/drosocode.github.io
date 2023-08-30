---
title: "Create your own ambilight solution"
date: 2022-05-30T00:00:00+01:00
draft: false
tags:
- docker
- home assistant
- iot
- arduino
- esp8266
resources:
- src: assets/box_1.jpg
  name: box
  title: The box that I recovered
- src: assets/box_2.jpg
  name: box
  title: Filling the box with all the components
- src: assets/box_3.jpg
  name: box
  title: The finished result
- src: assets/android_grabber.jpg
  name: settings
  title: Android Grabber Settings
- src: assets/kodi_settings.jpg
  name: settings
  title: Kodi Settings
- src: assets/audio1.jpg
  name: audio
  title: Fixing the audio bar
- src: assets/usb_plug.jpg
  name: audio
  title: The usb relay plug
---

Ambilight is a technology of Bias lighting used in Phillips TVs which illumitates the back of your tv with colors related to the image displayed. Their solution is expensive, but you can create your own solution using an ESP 8266 controller and some cheap led strips.

In order to adapt the lights to the image, the ambilight system needs to capture the images displayed on your tv. There are 2 main ways to do that: you can use a physical box to capture the video using an HDMI splitter and an acquisition card between your devices (Mi Box, Nvidia Shield, Xbox ...) and your TV or you can use a software solution to directly stream the video from a device (PC, Android TV ...).

## First Method

My first attempt was with the fist method (which was at that time the most used). The advantages are that you don't need to install a third-party software in order to connect a device to your ambilight. You only need to plug the HDMI output in the splitter and it should work. You can even connect an HDMI switch before the splitter to connect multiple devices to your amblight system.

However a stream may be protected with HDCP: a DRM protection which prevents it from being recorded, but there are many [flaws](https://en.wikipedia.org/wiki/High-bandwidth_Digital_Content_Protection#Circumvention) in this technology and you can find some cheap HDMI splitters or HDMI-to-RCA converters from China that are able to strip the HDCP to obtain a readable stream. 

You then need to capture and process the video signal, for this task I used an RCA-to-USB key (the image quality isn't important as the image is only used to detect the colors on the borders of the image). I used a Raspberry PI B+ to process the image and an arduino to control the led strips. The schema looked like this:

{{< image src="assets/v1.jpg" caption="Schema of the first version" width="90%" >}}

I then sticked some WS2812B led strips behind the TV and renovated an old metal box to fit all the components for the ambilight system. This box already had an integrated power supply that I used to power the raspberry pi and the leds in 5V.

{{< gallery id="box" >}}

On the software side, I used [Hyperion](https://github.com/hyperion-project/hyperion) (the first version) and the [Hypercon.jar](https://github.com/hyperion-project/hypercon) program to create the configuration file. The Raspberry PI would then send the orders to the connected arduino card that controlled the leds.

{{< image src="assets/tv_1.jpg" caption="the final result on the tv" width="70%" >}}

This method worked pretty well but the box was pretty big and when I moved in, I didn’t have it on hand (nor did I have the necessary components to build a new one). So I decided to try another method.

## Second Method

### Presentation

With this second solution, the splitter, converter and grabber are no longer needed: I just connect the HDMI devices directly to my tv and these devices will stream their video to an external server with [Hyperion-ng](https://github.com/hyperion-project/hyperion.ng) (a new version of hyperion) which will send led control commands to an ESP 8266 over wifi (using [E 1.31](https://en.wikipedia.org/wiki/DMX512#Wireless_operation)). Note that with this version, it will be impossible to capture DRM protected content.

{{< image src="assets/v2.jpg" caption="Schema of the second version" width="90%" >}}

### Configuration of the Hyperion Clients

To stream the video feed from my android tv box, I used the [hyperion-android-grabber](https://github.com/abrenoch/hyperion-android-grabber) app and for my PC I used the [HyperionScreenCap](https://github.com/sabaatworld/HyperionScreenCap) software.

To install a third-party apk on android tv, you need to enable ADB in the developer settings and connect to your box from your PC with `adb connect 192.168.1.X` You can then type `adb install ./tv-release.apk` to install the apk on your box. The app sould appear in your applications menu, if this is not the case, you can launch it manually with `adb shell am start -n com.abrenoch.hyperiongrabber/.tv.activities.MainActivity`. You can then go in the app’s settings and configure the IP of your server and the protobuf port (that will be used to receive the video from the box). You also need to set the priority between 100 and 199.

For android tv, you may need to disable some hadware acceleration features that prevents the image from being captured, for Kodi, you need to disable the `MediaCodec (Surface)` feature in the settings.

Note that any service serving drm protected content will not work (like Netflix, Amazon Prime, Twitch ...).
For youtube, you can bypass this protection by using the excellent [SmartTube](https://github.com/yuliskov/SmartTubeNext) app.

{{< gallery id="settings" >}}

### Configuration of the Hyperion Server

Once the clients are configured, you need to setup the hyperion-ng server that will receive the video streams from the clients, process it and send the commands to you leds. You can use the following dockerfile and docker-compose to run it.

```dockerfile
FROM debian:11-slim
RUN apt-get update && apt-get install -y \
  wget jq \
  qtbase5-dev \
  libqt5serialport5-dev \
  libqt5sql5-sqlite \
  libqt5svg5-dev \
  libqt5x11extras5-dev \
  build-essential \
  libusb-1.0-0-dev \
  libcec-dev \
  libavahi-core-dev \
  libavahi-compat-libdnssd-dev \
  libxcb-util0-dev \
  libxcb-randr0-dev \
  libxcb-shm0-dev \
  libxcb-render0-dev \
  libxcb-image0-dev \
  libxrandr-dev \
  libxrender-dev \
  libturbojpeg0-dev \
  libssl-dev
RUN wget "https://api.github.com/repos/hyperion-project/hyperion.ng/releases" -O - | jq -r '.[0].assets[] | select(.name | contains("x86_64.deb")).browser_download_url' | wget -i - -O hyperion.deb && dpkg -i hyperion.deb
CMD "/usr/share/hyperion/bin/hyperiond"
```

```yaml
version: "3"
services:
    hyperion:
        build: .
        volumes:
            - /app/docker/data/Hyperion:/root/.hyperion
        labels:
            - traefik.http.routers.hyperion.rule=Host(`hyperion.domain.tld`)
            - traefik.http.routers.hyperion.tls=true
            - traefik.http.routers.hyperion.entrypoints=https_lan
            - traefik.http.services.hyperion.loadbalancer.server.port=8090
            - traefik.enable=true
        restart: unless-stopped
        ports:
          - 19400:19400
          - 19444:19444
          - 19445:19445
          - 19333:19333
```

### Configuration of the ESP8266

The last thing to configure is the ESP 8266, that will receive the commands from the Hyperion server (with the E1.31 protocol) and control the leds. To do this easily, we can use ESP Home (see my previous post [here](/2022/01/14/easily-create-you-diy-iot-devices-with-esp-home-and-home-assistant/)). With the basic config, you just need to add a [neopixelbus](https://esphome.io/components/light/neopixelbus.html) component with the type, command pin and amount of leds, and add the E1.31 effect to allow hyperion to control the leds. While writing the configuration file, I also decided to add an infrared led to control my TV from Home Assistant. For this you can either attach an IR receiver to capture the IR codes from your remote or try to find the codes online. Fom my TV brand (LG) I have found the following [gist](https://gist.github.com/francis2110/8f69843dd57ae07dce80) with all the codes.

{{< file "content/posts/create-you-own-ambilight-solution/ambilight.yaml" >}}

{{< image src="assets/tv_wiring.jpg" caption="Wiring of the second version" width="90%" >}}

On a side note, if like me you are using an ESP-32, you can add the following code to your esp configuration to make it capable of acting as a [bluetooth relay](https://www.home-assistant.io/integrations/bluetooth/#esphome-requirements) for Home-Assistant.


```yaml
esp32_ble_tracker:
  scan_parameters:
    interval: 1100ms
    window: 1100ms
    active: true

bluetooth_proxy:
```

### Configuration of Home Assistant (Optional)

You should now be able to add all the esp home devices in Home Assistant. You can see below that I also configured the Hyperion integration. We now have a complete remote to control our tv thanks to the IR led and a light entity representing our led strip that we can use to either use like a normal color bulb, set it in E1.31 mode to allow hyperion to control it, or set it in WLED mode to allow it to sync with other wled devices (using the Effect menu).

{{< image src="assets/hass.png" caption="The devices in Home Assistant" width="90%" >}}

You can also see a TV switch in Home Assistant. I created this device to be able to switch the tv on and off using the IR code corrsponding to the "power" button on the remote and based on the TV's status on the network (as you can see in the tv's picture above this TV has an ethernet port, so if the TV is on, then we can ping its IP address). Here is the configuration used to create this device:

```yaml
switch:
  - platform: template
    switches:
      tv:
        value_template: "{{ is_state('binary_sensor.tv_status', 'on') }}"
        turn_on:
          service: switch.turn_on
          data_template:
            entity_id: >
              {% if is_state('binary_sensor.tv_status', 'off') %}
              switch.lg_power
              {% else %}
              null
              {% endif %}
        turn_off:
          service: switch.turn_on
          data_template:
            entity_id: >
              {% if is_state('binary_sensor.tv_status', 'on') %}
              switch.lg_power
              {% else %}
              null
              {% endif %}

binary_sensor:
  - platform: ping
    host: 10.20.4.2
    name: tv_status
    count: 2
    scan_interval: 10
```

On the right, you can see a custom card for controlling the TV with a more user-friendly UI. This [card (usernein/tv-card)](https://github.com/usernein/tv-card) is available on [HACS](https://hacs.xyz/).
I used the following configuration (the last row is for controlling a media_player entity, here my kodi instance):
{{< file "content/posts/create-you-own-ambilight-solution/tvcard.yaml" >}}

## Bonus

### Fixing the audio bar

My Phillips audio bar also stopped working after some time, so I decided to fix it. As I don't have a lot of knowledge about electronics I wasen't able to identify the faulty component on the board, so I simply ordered a cheap 2.1 amplifier. As this ampifier wouldn't fit into the bar, I rewired the bar's speakers to RCA plugs on the bar and then used these plugs to connect the bar to the amplifier. 

But there was no remote with this amplifier, it's not much of a problem for the volume (as we can still adjust it from the tv) but it isn't practical to power it on and off. So I created a simple plug with a 230v relay powered by a usb port. The usb plug is connected to the TV, so when the TV is powered on, the usb ports will also be powered, which will then power the relay and let the current pass to power the amplifier.

{{< gallery id="audio" >}}

## Conclusion

We have seen 2 different methods to create an amibilght system and especially to capture video, both of them having their advantages and drawbacks.

The second one requires less hardware and space but you need to install a client software on each device that you want to use (and some devices will just not work like the PS4 where you can't install anything), moreover you can only use this method to capture unprotected content.

In contrast to this, the first method, while requiring significantly more hardware, will likely allow you to capture pretty much anything and once the first setup is done, it should be only a matter of plugging the device on the HDMI switch to add a new device.

So, in the next version (an hopefully the last one), I think that I will use a bit of both methods with a standalone capture device like in the first method based on a raspberry pi and either an RCA grabber or directly with a CSI-to-HDMI adapter, and a command part kept as is, with the ESP8266 that allows to control the tv and the leds from Hyperion or directly from Home Assistant.

