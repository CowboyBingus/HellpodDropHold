# v1.2

- First public release.
- Holds your own hellpod in the sky while your game shows a loading screen or the join cutscene after it, as when you join a mission in progress, and lets it fall in the frame both are gone.
- The drop then runs as normal, with steering near the ground; a hold ends after 2 minutes at the most.
- Changes one value of your own pod's state and puts it back; reinforcements, teammates' pods and stratagem pods are never touched.
- Only you need the mod: teammates and hosts without it see your hellpod wait.
- Held the pod in two live joins (about 8 s at 1,500 m) and let it fall as the join cutscene ended.
- Measured in live play: 0.004 ms per frame in missions and 0.003 on the ship.
- Steam build 25480438 only; requires Bingus Shared Loader v18 or newer.
- Licensed under the Zero-Clause BSD license (0BSD).

# v1.1

- Keeps holding your hellpod after the loading screen while your join is still finishing (the join cutscene, or the game's own joining flag); in a live join the drop arrived only then and landed before the player could see it, so v1.0 never held it.
- The log now also records the cutscene, the join flags and the moment your own pod appears, so a join's timeline can be checked afterwards.

# v1.0

- Holds your own hellpod in the sky while your game shows a loading screen, as when you join a mission in progress, and lets it fall 1.5 s after the screen is gone.
- The drop then runs as normal, with steering near the ground, and the hold ends after 2 minutes at the most.
- Changes one value of your own pod's state and puts it back; reinforcements, teammates' pods and stratagem pods are never touched.
- Only you need the mod: teammates and hosts without it see your hellpod wait.
- Logs each loading screen, hold and release to `HellpodDropHold.log`.
