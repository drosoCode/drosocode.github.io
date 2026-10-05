---
title: "Overengineering a mirror or how I PXE-booted a k3s cluster - Part 3"
date: 2026-02-14T00:00:00+00:00
draft: true
tags:
- hardware
- infra
- k8s
---

This is the third and last part of this series of posts:
- [Part 1: Network Booting](/2026/09/13/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster/)
- [Part 2: Hardware Setup](/2026/10/02/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster-part-2/)
- Part 3: K8s Deployment

Now that our cluster is ready and that we know how to use the Kinect, we're ready to ~~write a ton of yaml~~, deploy everything on the cluster and do some automations !

## Discovering USB devices with Akri

Since we'll be deploying our containers in a kubernetes cluster, we need a way to schedule these containers on the right node (in my case, the mini-pc that is connected to the Kinect and to the TV).

The easiest way would be to set a specific taint on the mini-pc and match it in our deployment, but this is a bit hacky.

What if we could directly tell the scheduler what devices are required on the node ? That's what [Akri](https://docs.akri.sh/) provides.

More specifically, the [udev](https://docs.akri.sh/discovery-handlers/udev) handler allows us to match specific udev rules for scheduling.

### Deploying Akri

I'm using [Flux CD](https://fluxcd.io/) to manage all my k8s config, so I'll show the configuration foe this environnement.

First, create a `HelmRepository` and a `HelmRelease` to install Akri.

In the `HelmRelease` values, don't forget to enable udev discovery.

{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster-part-3/assets/k8s/akri_helm.yaml" >}}

### Configuring udev rules

Then, we can create Akri `Configuration` objects to match specific udev rules.

I created 3 Configurations:
- `udev-framebuffer` to match a framebuffer device with: `SUBSYSTEM=="graphics", KERNEL=="fb[0-9]*"`
- `udev-violet-mirror` to match the violet mir:ror: `SUBSYSTEM=="hidraw", ATTRS{idVendor}=="1da8", ATTRS{idProduct}=="1301"`
- And `udev-kinect2` with 3 rules to match the Kinect's usb devices: `SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="...."`

{{< file "content/posts/overengineering-a-mirror-or-how-i-pxe-booted-a-k3s-cluster-part-3/assets/k8s/akri_dev.yaml" >}}

### Adding it to the deployment

Now, just add the required devices as resources/limits in your deployment with the prefix `akri.sh/`.

For example, with the libfreenect/ffplay container:

```yaml
resources:
  limits:
    akri.sh/udev-kinectv2: "3"
    akri.sh/udev-framebuffer: "1"
  requests:
    akri.sh/udev-kinectv2: "3"
    akri.sh/udev-framebuffer: "1"
```

## Capturing the Kinect's video

## Automating everything with Home-Assistant

### Using the mir:ror as a trigger

NATS + mirror-mqtt

### Switching the TV On

ESPHome (cf prev post)

### Switching the Kinect On

433mhz + RFXLan + xPL2MQTT

### Virtual workloads Switch


## Scaling workloads with Keda


## Final Setup


## Conclusion


## References


