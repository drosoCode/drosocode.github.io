---
title: "Why Vanguard is the wrong way of doing anticheats"
date: 2022-05-30T00:00:00+01:00
draft: true
tags:
- python
- raspberrypi
- hardware
---

It has now been about 2 years since the new FPS of Riot Games, [Valorant](https://playvalorant.com) was released. This game made quite a fuss when it was released because of its anti-cheat software: Vanguard.

## What is Vanguard

In all PvP online games (and especially if they are competitive and on PC) the editors needs to ensure that all players are playing the game as intended and doesn't have installed a third-party hack to cheat in the game.
To ensure that the game isn't tamepered with and that the player is not cheating, these separate programs were included in these games. 
Among the most popular ones, you can find:
- [VAC: Valve Anti-Cheat](https://en.wikipedia.org/wiki/Valve_Anti-Cheat) which is used in Counter Strike
- [EAC: Easy Anti Cheat](https://www.easy.ac/) an anti-cheat developed by Epic Games and used by a lot of games like Fortnite and Apex Legends
- [BattlEye](https://www.battleye.com/) used in the Ubisoft games like Rainbow 6 and Destiny

Aaaand the latest one, Vanguard, devloped by Riot Games for VALORANT.

## What is the problem

With cheats getting more and more complex, this is a game of cat and mouse with the game editors, so the anti-cheats solutions also becomes more and more complex and invasive. Invasive, beacuse most of these solutions implements a kernel module to ensure that no cheat is hidden in the lowest and most secure places of windows: the kernel level (or layer 0). This usage seems justified and if it blocks most of the cheaters you may consider it as a good thing.

However it is important to keep in mind that you are installing another piece of completely closed source software in the most restricted area of your system (well we could say the same of using a closed source system such as Windows, but that's for another day ...).

Writing some software to run it in [kernel mode](https://docs.microsoft.com/en-us/windows-hardware/drivers/gettingstarted/user-mode-and-kernel-mode#kernel-mode) isn't an trivial thing: any error could compromise the security or the stability of the system. And you sould be wary of what you are running in this mode as we've already seen in the past 


## Why it isn't effective

## Proof of Concept

## Alternatives

## Conclusion

why vanguard and kernel anti cheats are too invasive
why they are not 100% secure
-> demo of aimbot for vanguard
alternative to these anticheats (server-side analysis, community moderation (csgo), ranking (trust factor))
https://playvalorant.com/en-gb/news/dev/valorant-anti-cheat-what-why-and-how/
https://www.frandroid.com/marques/microsoft/927715_halo-infinite-anti-triche-pc-kernel-noyau
https://www.reddit.com/r/linux_gaming/comments/t7g87g/how_does_easy_anti_cheat_work_with_proton_on_linux/
https://en.wikipedia.org/wiki/Cheating_in_online_games
https://www.leagueoflegends.com/en-us/news/dev/dev-null-anti-cheat-kernel-driver/
https://www.leagueoflegends.com/en-us/news/dev/dev-anti-cheat-in-lol-more/
