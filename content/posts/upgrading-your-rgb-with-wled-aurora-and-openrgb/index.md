---
title: "Upgrading your RGB with WLED, Aurora and OpenRGB"
date: 2021-11-29T00:00:00+01:00
draft: false
tags:
- arduino
- home assistant
- esp8266
- hardware
- RGB
- python
resources:
- src: assets/wled.png
  name: wled
  title: WLED Web UI
- src: assets/wled2.png
  name: wled
  title: WLED sync config page

- src: assets/openrgb.png
  name: openrgb
  title: OpenRGB UI
- src: assets/openrgb2.png
  name: openrgb
  title: OpenRGB config file
  
- src: assets/aurora.png
  name: aurora
  title: Aurora devices config tab
- src: assets/csgo.png
  name: aurora
  title: Aurora game effects config (CS:GO)
  
- src: assets/forza_1.png
  name: forza
  title: Forza Settings
- src: assets/forza_2.png
  name: forza
  title: Forza data graph
  
- src: assets/keyboard.png
  name: forza2
  title: OpenRGB Keyboard View
- src: assets/zforza.gif
  name: forza2
  title: Forza Demo
---

I was always interested in going furether than the pre-made RGB equipement by various manufacturers because each system was only compatible with only one brand (ex: iCUE, RGB Fusion, Asus RGB …) and that their RGB softwares were very unfinished and didn’t exploit the full potential of the RGB hardware.

## First Attempt

So, when I built my first desktop PC, I decided to create from scratch a custom RGB system. This was based on an arduino board, internally connected to my PC using USB. This arduino was controlling cheap adressable RGB strips (WS2812B) powered by my PSU in 5v. On the software side, I developped a custom C# application, [LedControl](https://github.com/drosoCode/LedControl). This was my first attempt at controlling my RGB leds.

{{< image src="assets/rgb_v1_setup.jpg" caption="The window mounted on the pc with the arduino control box in a HDD slot (on the left) and the WS2812B leds mounted on the window (on the right)" width="80%" >}}

{{< image src="assets/rgb_1.png" caption="My custom software in C#" >}}

A bit later, while adding RGB fans, I discovered that they were using the same type of adressable leds. Unfortunately, only an input port was available, meaning that you were not able to chain the devices and control their leds individually. So, in order to control every led of my system, I needed to wire each fan data line to a dedicated port on the arduino. As there wasn’t enough ports on the nano (and that a mega was too big), I needed to add a second arduino.

{{< image src="assets/wiring.jpg" caption="Going from the first to the second version (with 2 arduinos)" width="80%" >}}

{{< image src="assets/ws2812.png" caption="Example of WS2812B led strip, notice the white arrow next to the data pin, indicating the correct side to add more leds" >}}

This system was working quite well, my software was able to control each device and leds individually and to apply multiple effects at the same time (ex: GPU Temp reactive lighting for a fan, CPU Temp for another fan, and music reactive effect for the window’s leds). However it wasn’t able to interact with built-in RGB like the leds on the motherboard/GPU and also had a quite limited set of effects available.

{{< image src="assets/rgb_v1.jpg" caption="Control of the window/fans’s RGB leds on the left, wiring of the next version (see below) on the right" width="70%" >}}

## Second Attempt

### WLED

So, when I renewed my computer and bought a new case, I decided to completely change the RGB lighting system. A lot of things happened after I created my first solution, and the ESP8266/ESP32 were now very common and had received a lot of support from the opensource community. Among the incredible amount of projects, was [WLED](https://github.com/Aircoookie/WLED), a RGB control program for these wifi chips that allowed you to control various led strips, including the WS2812B from a web interface and much more. I decided to use this project as a base to control the WS2812B-based RGB in my PC. *As mutli-pin control (required for my fans) wasn’t available in the provided firmware, I neded to slightly edit the source-code and recompile it.* Starting from version 0.12.0, [multi-strips are supported](https://github.com/Aircoookie/WLED/wiki/Multi-strip) in the precompiled binaries and are easily configurables.

After wriring all my led strips, I connected my pc to the wireless hostpot created by the esp and configured the my home wifi credentials, and that’s it. I was now able to connect to the web ui of WLED and control my PC’s RGB from any device. WLED has a lot of really cool features such as synchronizing with other WLED devices, E1.31 support, an incredibly complete list of effects and the ability to define independant zones on the light strip.

{{< gallery id="wled" >}}

### OpenRGB

Once that the control of the WS2812B RGB was settled, I neded to find a way to control the build-in RGB of my motherboad, RAM, GPU and keyboard. That’s where another awesome software enters: [OpenRGB](https://gitlab.com/CalcProgrammer1/OpenRGB). This is what is tieing everything together: OpenRGB is a cross-platform software that is able to control practically any RGB device from many manufacturers like Corsair, Asus, Gigabyte, HyperX, MSI … It also supports controlling devices using E1.31 and exposes an universal API to control all of them. Most of the devices are auto-detected but for E1.31 , you need to manually edit the configuration file in `%appdata%/OpenRGB/OpenRGB.json` to specify the IP of the device (here, our WLED esp). Also, keep in mind that access to some devices control interfaces (like SMBus) may be blocked by other softwares, especially anti-cheats like Vanguard.

{{< gallery id="openrgb" >}}

### Aurora

A first options is to use [Aurora-Project](https://github.com/antonpup/Aurora), to interact in real time with some games and apply some effects based on the game’s data. Aurora supports many well-known games like CS:GO, Minecraft, LoL … and a lot of different devices and protocols, including OpenRGB. So we just need to enable OpenRGB in Aurora (it will automatically connect to your local OpenRGB instance) and start the OpenRGB API Server to be able to use these effects.

{{< gallery id="aurora" >}}

There are also some other software using the OpenRGB API, like [KeyboardVisualizer](https://gitlab.com/CalcProgrammer1/KeyboardVisualizer) (from the same author) that creates music-based lighting effects. 

{{< image src="assets/csgo.jpg" caption="Example in CS:GO, the F1-12 line represents your life and the 1-9 keys represents your ammo level" width="80%" >}}

### Custom effects

Another option is to use directly the OpenRGB API to create new effects. Fortunately a lot of [wrappers](https://gitlab.com/CalcProgrammer1/OpenRGB#openrgb-sdk) in multiple languages already exists for this API. Here, we’ll be using [python-openrgb](https://github.com/jath03/openrgb-python). 

We will take Forza Horizon 5 as an example (as this is the latest game that I played). This game is has an option in `Settings > HUD and Gameplay` to send UDP telemetry packets while playing, we will use this data to create our effects. To decode these packets we will use the ForzaDataPacket class from the [forza_motorsport](https://github.com/nettrom/forza_motorsport) project. We will, in the first time, use a little script (test.py, see code below) to gather a bit of data and graph it with matplotlib, to have an idea of the evolution of these metrics.

{{< gallery id="forza" >}}

We can then map these values to RGB colors using a custom script (see below) and send them to OpenRGB. To determine which key you want to light-up, you can click on `Toggle LED View` in OpenRGB to show the emplacements of your keys, you can then use `keyboard.matrix_map[y][x]` to get the correct led id. Also note that spaces between keys also counts as keys, for example, the F1 key has the id 2 (and not 1) because of the space between the escape key (id: 0) and this key. With this script, the 1-9 keys of the keyboard represent your position in a race, the line below represents the engine rpm, below is the speed and the last line is the power. The insert/suppr/page up/page down keys represent the slip ratio for each tire and the lines 1/4/7 2/5/8 and 3/6/9 on the numpad represent your car’s status (acceleration/brake/handbrake).

{{< gallery id="forza2" >}}

{{< file "content/posts/upgrading-your-rgb-with-wled-aurora-and-openrgb/main.py" >}}

{{< file "content/posts/upgrading-your-rgb-with-wled-aurora-and-openrgb/test.py" >}}

### Home Assistant

{{< image src="assets/hass1.png" caption="Home Assistant card with the different devices (on the left) and a device control popup (on the right)" width="80%" >}}

In addition to your RGB software on your PC, you can also control everything from your home automation system. For example, in [Home Assistant](https://www.home-assistant.io/), you can configure the [WLED integration](https://www.home-assistant.io/integrations/wled/) to control your PC’s led stips. Using [HACS](https://hacs.xyz/), you can also install the [OpenRGB integration](https://github.com/koying/openrgb_ha), which will then allow you to control all of your computer’s RGB devices using OpenRGB.

## Conclusion

We now have a complete RGB lighting system for our computer with dynamic game-based lighting effects. As written in the last paragraphs, we can even control it from python scripts or home automation systems which opens the door to even more powerful connections (for example make your first fan blink when you receive a new message, or sync your RGB with an ambilight system …).