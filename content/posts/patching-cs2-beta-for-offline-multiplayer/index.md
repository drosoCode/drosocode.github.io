---
title: "Patching CS2 beta for offline multiplayer"
date: 2023-10-24T00:00:00+01:00
draft: false
tags:
- reverse engineering
- assembly
- games
---

## Introduction

On march 2023, Valve announced with a [youtube video](https://www.youtube.com/watch?v=_y9MpNcAitQ): [Counter-Strike 2](https://www.counter-strike.net/cs2), the sequel to Counter-Strike: Global Offensive on a new engine: [Source 2](https://developer.valvesoftware.com/wiki/Source_2). The game was scheduled for global release at "summer 2023" and available as a beta program to a few selected players.

Unfortunately, I was not granted access to the beta, but it didn't take long for the beta files to be [leaked](https://www.gameblog.fr/jeu-video/ed/news/counter-strike-2-leak-420422) as a torrent.

## Playing in multiplayer

Once you have obtained the game files, you can't run them directly as steam will detect that you don't own the game, but this is easily bypassed using a steam emulator like [goldberg_emulator](https://gitlab.com/Mr_Goldberg/goldberg_emulator): this works by reimplementing all the `steam_api.dll` functions, so that you can replace this file in your game and completely bypass steam.

Once this is done, the game finally starts ! Of course, you can't access all the steam features with this method (as you are not authenticated), so no inventory and no official servers, but that's fine, we just want to test the game.

Some of you may already know that in the [Source Engine](https://developer.valvesoftware.com/wiki/Source_Multiplayer_Networking) based games, you can access the console and connect to a custom game server using the `connect <SERVER_IP>` command. This way, CS:GO could be played on LAN (started in offline mode) even if you didn't have internet access: you just start a game on one pc and tell your friends to connect to your session using your ip. Your friends can also connect to your session over the internet if you port-forward the `27015` port from your router to your PC (in IPv4).

So, with Source 2, this shoudn't be different and we should be able to play in multiplayer using this method (even without internet or steam). But in reality, this doesn't work out of the box, this may be related to changes on how the networking is handled in source 2, or to the fact that we use a steam emulator, but the end result is the same: you can't connect to your server.

{{< admonition type=info title="Update" open=true >}}
At the time of writing this post, I have re-tested to connect to a lan dedicated server: everything works fine as long as you are connected to the internet and to steam. But if you switch to offline mode on steam or start the game without internet access, you will get a certificate error when connecting.
{{< /admonition >}}

## Digging

So, here's the error message:

{{< image src="assets/error_lan_cert.png" caption="CS2 error when connecting to a local server" width="90%" >}}

We can see that the error is seemingly related to a certificate problem: as we are not connected to steam/internet, we can't get our certificate from Steam, so a self-signed one is probably generated. The connection is terminated with this message "Cannot use unsigned cert; failing connection" as we don't have a valid certificate.

An interesting thing, is that on CS:GO (on Source 1), the certificate error also appears, but you are still able to connect, so it seems that in CS2, the signed certificate requirement is enforced.

{{< image src="assets/csgo_conn_ok.png" caption="CS:GO certificate warning" width="90%" >}}

The first thing I did was to search for similar issues on the internet, and after a few searches, I stumbled upon [this thread](http://bir3yk.net/forum/topic_411/19/) about Dota 2 (which was already using Source 2 for quite a while). In particular, an option caught my attention: `-sdr IP_AllowWithoutAuth = "1"`, this seems like a command line parameter allowing to bypass the authentication step, so this would probably solve our certificate issue.

I tried to use it in command line when starting the game, without success. So I tried to launch the game and enter it in the console, but, as you can see the sdr command returns a list of parameters but `IP_AllowWithoutAuth` is unknown.

{{< image src="assets/error_set_noauth.png" caption="IP_AllowWithoutAuth not recognised" width="50%" >}}

## Setting the right parameter

While searching for the cause of our error message, I also found a link to a Valve library, called [GameNetworkingSockets](https://github.com/ValveSoftware/GameNetworkingSockets) with this exact error message [referenced in the code](https://github.com/ValveSoftware/GameNetworkingSockets/blob/16ec25a66c27e79fb4d36ffa8c64a7a421cfa877/src/steamnetworkingsockets/clientlib/steamnetworkingsockets_connections.cpp#L1329).

If you remember, the library throwing certificates error AND replying that the parameter `IP_AllowWithoutAuth` doesn't exists is called SteamNetworkingSockets. Pretty similar right ?

Well, actually GameNetworkingSockets is the [opensource version](https://github.com/ValveSoftware/GameNetworkingSockets/tree/16ec25a66c27e79fb4d36ffa8c64a7a421cfa877?tab=readme-ov-file#why-do-i-see-steam-everywhere) of SteamNetworkingSockets with a few steam-specific features removed.

Of course, CS2 uses the proprietary version.

But we can still find interesting things in the opensource library, especially [this portion of code](https://github.com/ValveSoftware/GameNetworkingSockets/blob/master/src/steamnetworkingsockets/clientlib/csteamnetworkingsockets.cpp#L86) which defines different values for the `IP_AllowWithoutAuth` configval depending on the library version that is used. And, according to [these comments](https://github.com/Facepunch/Facepunch.Steamworks/blob/steamworks157/Facepunch.Steamworks/SteamNetworkingUtils.cs#L254) the 0 value is for "Not allowed (the default)" unencrypted communications. So, it's safe to assume that the library used in CS2 uses a default value which forbids unencrypted communcations. 

But, if this parameter really exists, why can't we change it ?

The answer lies a little lower in the same file: [this function](https://github.com/ValveSoftware/GameNetworkingSockets/blob/16ec25a66c27e79fb4d36ffa8c64a7a421cfa877/src/steamnetworkingsockets/clientlib/csteamnetworkingsockets.cpp#L2265) takes in parameter a configval and returns a boolean to indicate if this configval is allowed to be queried/modified. But `IP_AllowWithoutAuth` is a special case: it is only visible when the parameter `bEnumerateDevVars` is true, which means that we can only modify it when the library is compiled in dev mode.

## Patching CS2

Of course, I thought of simple approaches first: swapping the `steamnetworkingsockets.dll` of CS2 with the one from Dota 2 (where the configval seems to work) and swapping it with a recompiled version of GameNetworkingSockets, with devmode enabled. Obviously neither worked, but it was worth a try.

So, I fired up a decompiler, ([Ghidra](https://github.com/NationalSecurityAgency/ghidra) in this case) and put in the `steamnetworkingsockets.dll` from CS2. I then searched for a switch block of 3 cases and 3 cases (just like the function seen above) in the decompile view. 

Once I found this block, I looked at the code executed for the first 3 cases: this was a `JZ` instruction which is a conditionnal jump in x86 assembly. This jump is executed if the value is equal to zero (JZ = jump if zero).

To allow to edit our configvar in CS2, I changed this `JZ` instruction to its negative form: `JNZ` (jump if not zero) and saved the modifications to the dll using [this script](https://github.com/schlafwandler/ghidra_SavePatch). The configvar should now be visible only in release mode, which is the case of CS2.

{{< image src="assets/ghidra_fix.png" caption="Patching JZ instruction" width="90%" >}}

I started CS2, typed the same command, and it worked !
{{< image src="assets/set_noauth_ok.png" caption="IP_AllowWithoutAuth recognised" width="90%" >}}

Now that we have set this parameter, we can try to connect to a gameserver:
{{< image src="assets/cs2_conn_ok.png" caption="IP_AllowWithoutAuth recognised" width="70%" >}}

Annddddd ... it works !

You can see at the bottom of the screen that we get the same error: "Cert request failed" but now, it is immediately followed by "Continuing with self-signed cert" and the connection to the server is established.

We are now able to use the connect command to connect multiple PCs to the same session, we can now do a simple port forwarding to the pc hosting the game and try this shiny new beta in multiplayer.


{{< admonition type=warning title="Warning" open=true >}}
Do not use a patch like this when connecting to official VAC secured servers as the modification of game files is prohibited and you could get banned.
{{< /admonition >}}

## Conclusion

What was initially a simple curiosity to try-out the new beta quickly turned into quite a bit of research, but it was really fun project to do and in the end, we finally could test this game. 

We received were admitted in the beta program five months later, just a few weeks before gloabl launch. Now the game has officially replaced CS:GO, and is very regularely updated, so let's hope that this continues and that we get a really good game to play for years to come !
