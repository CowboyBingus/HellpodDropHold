# Hellpod Drop Hold v1.2.1

Joining a mission in progress, or loading slowly, no longer costs you the drop. Your hellpod waits in the sky
until your loading screen, and the join cutscene after it, are gone. It is already falling when you see it, like a
normal drop, and you can steer it near the ground.

Without it, the game starts a joining player's drop as soon as the host sends the drop point. On a slow PC that
can be while you are still on the loading screen or the join cutscene. You then see the pod halfway down or
already landed (even on a fast PC the whole drop can pass unseen), miss the part of the drop you can steer, and can
land on a teammate or their equipment.

**Status:** held the pod in two live joins (about 8 s at 1,500 m) and let it fall as the join cutscene ended.
Steam build 25480438 (EXE 1.8.46015.0) only.

**Requires Bingus Shared Loader v18 or newer / API 1**, a separate download:
[latest loader](https://github.com/CowboyBingus/BingusSharedLoader/releases/latest). Import both ZIPs into
Arsenal or HD2MM, enable both and deploy. Only you need the mod: teammates and the host see your hellpod wait.

What it does and does not do:

- **What is held.** Only your own drop pod is held, and only while your game shows a loading screen or the join
  cutscene that follows it.
  Reinforcements during play, teammates' pods and stratagem pods are never touched.
- **How long.** Release comes in the frame the loading screen and the join cutscene are gone, so the pod is
  already falling when you see it. The hold lasts 2 minutes at the most.
- **What it changes.** It writes one value of your pod's state when the hold starts and puts it back at release.
  It changes no game code and no game files.
- **Other game builds.** On any other game build it does nothing.

Log: `%LOCALAPPDATA%\CowboyBingus\Helldivers2\Logs\HellpodDropHold.log`, with the loading screen, hold and
release events.

## Cost

Four memory reads every 0.25 s while you play; every frame only while a loading screen or the join cutscene is
up; one checked write when a hold starts and one at release. Measured in live play: 0.004 ms per frame in
missions and 0.003 on the ship.

## Source

- `src/`: the mod (`drop_hold.lua`, `archive_loader.lua`, `windows_api.lua`) and Bingus Shared Runtime v1,
  vendored byte-identical.
- `tests/`: offline checks on synthetic memory with exact per-frame call budgets, and the package check.
- `scripts/`: build and packaging. `python -B scripts/build.py` runs the tests in LuaJIT and in the game's own
  `lua51.dll` (`HD2_LUA51_DLL` if the game is not in the default Steam folder; the game is never started) and
  builds `releases/Hellpod-Drop-Hold-v1.2.1.zip`. It needs the installed game (`HD2_GAME_ROOT` if not in the
  default Steam folder), LuaJIT (`HD2_LUAJIT`) and `hd2-patch-inspect` (`HD2_PATCH_INSPECT`, from
  [Better Stratagem Bounce](https://github.com/CowboyBingus/BetterStratagemBounce)) to check the archive.

[How it works](docs/TECHNICAL.md) · [Changes](CHANGELOG.md)

**AI disclosure:** Claude Opus 5.5 did the research, implementation, tests and documentation.

## License

Zero-Clause BSD (0BSD): use, copy, modify and distribute for any purpose, with no conditions. See `LICENSE`.
