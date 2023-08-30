---
title: "Use your oculus rift completly offline"
date: 2020-10-04T00:00:00+01:00
draft: false
tags:
- batch
- oculus
- offline
- reverse engineering
- vr
---

## Introduction

With the recent turn of events (upcoming requirement of a facebook account to use your oculus), I finally decided to get my oculus working fully offline, but it was harder than I thought.

## First Attempt

Indeed, if you can use your headset without an internet connection, you still need to have the oculus software installed. So, after some research, I came across [this topic](https://forums.oculusvr.com/developer/discussion/49742/offline-installer) where a user describes how to backup the installer files to use it offline. So I tested it and ….

{{< image src="assets/oculus.png" caption="Screenshot of non-working installer" >}}

Yeah, the current installer (tested with version 1.51.0.0) checks for an internet connection before starting the install process. So, I started Fiddler to see which requests are sent by this little software. However, with the HTTPS decoding enabled, the installer won’t work and we can’t see anything useful in fiddler. This behavior is probably due to the use of SSL-Pinning (we can also confirm that by checking the installer logs), which is a method more and more used to prevent this kind of attack. So, unless we can alter the hash stored inside the installer, this is a dead-end.

## Second Attempt

So, I switched to another method, and decided to just re-create the installer because … why not ? An installer is just copying files and adjusting some settings, so I should be able to do that too. But in order to archieve that, I needed to know exectly what this installer is doing. 

First I searched for oculus stuff in some key locations in the registry and backuped them, I also used a driver store explorer to see which drivers are installed to the headset and backuped them with this command: `dism /online /export-driver /destination:"BACKUP_FOLDER"`. I also knew that there was 2 services installed for the oculus software: “OVRService” which handles most of the work and “OVRLibraryService” which manages your oculus games, so I wrote down the path of the executables used in these services.

To backup and restore all of these components, I decided to use batch scripts, as they are natively supported on windows and are easily ediatables. To restore drivers I used the following command: `pnputil /add-driver "BACKUP_FOLDER\*.inf" /subdirs /install` and to re-create the service, I used this one: `sc.exe create OVRService binpath="PATH_TO_OCULUS“`. But after an unsuccessful try, I looked in the oculus logs in AppData\Local\Oculus and I saw that registy keys were missing, so I re-runned the official installer while using a software named [ProcessMonitor](https://docs.microsoft.com/en-us/sysinternals/downloads/procmon) that allwed me to record all system modifications (especially filesystem and registry operations).

{{< image src="assets/oculus_pm.png" caption="Screenshot of Process Monitor" >}}

Thanks to ProcessMonitor, I found the remaining registry keys, but also an easier way to install drivers and services. Indeed, I noticed that the installer called this executable in `Support\oculus-drivers\oculus-driver.exe` which handles driver installation. Same for OVRService which is installed with the command: `Support\oculus-runtime\OVRServiceLauncher.exe" -install -start`.

I also needed to backup some of the AppData folders, like `Appdata\Local\Oculus` which stores the headset settings, and `AppData\Roaming\Oculus` which stores the account setttings (so you absolutely need to backup and restore this in order to skip the online login procedure when launching the oculus-client for the first time). Finally, I needed to block any communication with Facebook servers (for obvious privacy concerns) which was possible by simply pointing the domains found in the first attempt to localhost, using the hosts file (located in `%windir%\System32\drivers\etc\hosts`).

## Conclusion

With all of these data, I was able to successfuly create backup, install and uninstall scripts for the Oculus software that will run without internet access, making it possible to preserve the use of my vr headset forever.

Of course, these scripts are freely available to everyone on my github [here](https://github.com/drosoCode/Offculus).