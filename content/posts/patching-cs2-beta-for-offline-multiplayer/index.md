---
title: "Patching CS2 beta for offline multiplayer"
date: 2022-05-30T00:00:00+01:00
draft: true
tags:
- reverse engineering
---

Error location in lib:
https://github.com/ValveSoftware/GameNetworkingSockets/blob/master/src/steamnetworkingsockets/clientlib/steamnetworkingsockets_connections.cpp#L1329

IP_AllowWithoutAuth lead:
http://bir3yk.net/forum/topic_411/19/

Default values for IP_AllowWithoutAuth:
https://github.com/ValveSoftware/GameNetworkingSockets/blob/master/src/steamnetworkingsockets/clientlib/csteamnetworkingsockets.cpp#L86

Values explanation:
https://github.com/Facepunch/Facepunch.Steamworks/blob/master/Facepunch.Steamworks/SteamNetworkingUtils.cs#L254

Check preventing edition in production mode:
https://github.com/ValveSoftware/GameNetworkingSockets/blob/master/src/steamnetworkingsockets/clientlib/csteamnetworkingsockets.cpp#L2262


play csgo offline:
https://www.reddit.com/r/LearnCSGO/comments/jf9btu/is_it_possible_to_setup_csgo_to_play_on_lan/