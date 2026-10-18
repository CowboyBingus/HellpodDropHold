# How Hellpod Drop Hold works

When a player joins a mission in progress, the host sends that player's drop point at once, and the player's own
machine creates and steers the drop pod as soon as its avatar exists. On a slow PC that happens while the loading
screen is still up, so the pod falls unseen. It can even land: the player misses the only part of the drop they can
steer (the braking phase near the ground), and the pod can hit a teammate or equipment. This mod holds that pod in
the sky until the loading screen is gone, then lets the normal drop run.

All addresses are `game.dll` RVAs of Steam build 25480438 (EXE 1.8.46015.0).

## What the game does

- **Who drives the pod.** The avatar's spawn sequence (`0xA866F0`) runs on the avatar's own machine. It creates
  the pod as a networked entity (`0xFD9710`, networked flag set). The creating machine owns the pod (entity flag
  bit 0) and simulates it.
- **Pod types.**
  - A first drop or a join uses InitialSpawn (`0xE58163E71928D3E2`): spawn height 1500, 400 m/s, braking from
    500 m above ground to 100 m/s over 1 s.
  - Reinforce (`0xEF9EB729A9D6D849`): 1000, 350 m/s, braking from 350 m to 100 m/s.
- **How the pod moves.** The HellpodComponent update (`0x92B770`) moves each owned pod every frame by
  `((1 - t) * braking_velocity + t * initial_velocity) * dt` and publishes the new position.
  - t is a float in the pod's local state (+32). It is 1 at spawn.
  - It decays to 0 over the braking time once a ray of the type's braking height reaches the ground.
  - It decays only while t is above 0.
- **When the player can steer.** Steering input applies only during braking.
- **Join timing.** The host spawns a joining player (`0xACBE60`) as soon as that player's record exists. Nothing
  waits for the joining client's loading to end.
- **When the world updates.** The game update (`0xAB5000`) runs the world update (`0x571250`, which includes
  the pod update) whenever the entity world is active (game object +4276 and `0x134EF20`), whatever the game
  state. A joining client is in state 6 (preparing the mission: level, player histories, then every player's
  loadout, `0xAC50E0`) behind its loading screen, and its pod can fall during that state.
- **The loading UI.** The UI's PresenterManager is `[game+0x347CE28] + 0x4288`. It holds a HUD presenter (+8),
  a menu presenter (+12) and a popup presenter (+16). The menu presenter stack has five ids at +20 and its depth
  at +40.
  - Menu presenter names (`0x21DC810`): 1 Main, 2 LoadingMission, 3 LoadingShip, 4 LoadingTutorial, 5 Armory,
    14 Loadout, 15 Hologram.
  - HUD presenter names (`0x21DD450`): 1 NewUiIntroduction, 2 Ship, 3 Mission, 4 Tutorial.
  - At its end, prepare-mission closes the HUD presenter and pops the menus, then switches to state 4.
  - A live title-to-ship load on 2026-10-05 pushed no menu presenter at all; the stack depth stayed 0.

## What the mod does

- **Idle.** Every 0.25 s, read the game state (`[game+0x3326340] + 0xAC21C`) and the presenters (36 bytes at
  `[game+0x347CE28] + 0x4290`). A loading period starts while any of these holds:
  - the state is 5 or 6 (preparing the ship or a mission);
  - the menu presenter is 2 or 4 (LoadingMission, LoadingTutorial);
  - 2 or 4 is anywhere on the menu stack.
- **A join still finishing (v1.1).** In the mission state (4) or its preparation (6), a loading period also lasts
  while either of these holds:
  - a cutscene plays or waits: `[game+0x346D530] + 6412` (current scene), then +6416 (queued);
  - the session's `is_hotjoining` byte (`[game+0x347CEF0] + 92135`) is 1.
  Both end in the client's synchronized-tasks-done (`0xAD4520`): it clears `is_hotjoining`, then interrupts the
  cutscene. Unreadable values never count.
  - A cutscene alone never starts a loading period, and one in the ship state never extends it.
  - A joining client queues `ship_teleporter_network_join` (scene 15) when the host accepts the join
    (`0x10850F0`, on the ship). It interrupts the scene in the mission state only once its synchronized tasks
    are done (`0xAD4520`).
  - Meanwhile the host has already spawned that player's drop. In a live join on 2026-10-05, preparing lasted 7 s
    and ended before the pod existed (the world initialized 0.1 s before the mission state), so v1.0 held nothing.
    The player saw the pod hitting the ground when the screen cleared. The cover lasted at least the whole
    descent, about 7.5 s, after the mission state began.
  - Scene names: `0x117E950`. 6 is `ship_hellpod_launch`, the normal launch cinematic; 15 is the network join.
- **While a loading period lasts.** Every frame, read the signals and the HellpodComponent manager header
  (`[game+0x3326D58]`).
  - When the active pod count changes, and every 0.25 s, look for a drop pod with these properties:
    - owned by this machine;
    - InitialSpawn or Reinforce;
    - falling or braking;
    - placed at its index by the manager's own id map;
    - not handled during this loading period.
- **Hold.** For that pod:
  - read its type's initial and braking velocity from the type's HellpodComponent settings
    (`*(*(game+0x346BF98) + 15805152)`: 16 hash slots, then 104-byte records);
  - save its t;
  - write `t_hold = (0.5 - braking) / (initial - braking)`.

  The pod then sinks at 0.5 m/s, however long a loading frame takes. The speed is not zero, because the game
  derives the pod's rotation and its landing ray from the step direction. The braking decay leaves a negative t
  alone, so the hold lasts even if braking began.
- **Release (v1.2).** While holding, the cover is checked every frame. In the first frame with no loading signal
  and nothing covering the mission, the saved t is written back.
  - The pod is already falling when the player first sees it.
  - v1.1 waited 1.5 s after the cover, and in a live join the pod looked stuck in the air for that time.
  - The write happens only if the pod is still the same entity, still owned, and still holds t_hold.
  - The rest of the drop is a normal drop from that moment: fast fall, braking with steering, landing.
  - In that join (v1.1) the pod was held at 1500 m from the frame it appeared (635.25 s) until the cutscene
    ended (642.09 s). Without the hold it would have landed at about 642.75 s.
- **Safety.**
  - Release after 120 s of holding in any case.
  - Release when the update guard pauses (an update below raised) or stops.
  - Forget the pod, without a write, when it is gone.
  - If the manager cannot be read at release, keep the hold and retry 4 times a second.
  - At shutdown nothing is written.
- **Other players.** Teammates and the host need nothing. They receive the pod's published position and see it
  hover.
- **What is never held.**
  - Teammates' pods, stratagem payload pods, landed pods, and pods whose t another writer set outside 0..1.
  - Reinforcements during play, because no loading screen is up then.

## Validation and refusals

- **Game build.** Both game modules must match the supported build (`verify_build`, SHA-256 once per session).
  Any other build gets no change.
- **Manager header.** Capacity at most 4096, active ≤ total ≤ capacity, user-mode array pointers. A header that
  fails this stops the mod.
- **Settings.** A missing settings slot, a variant other than the type's, or velocities that make no sense
  (braking ≤ 0.5, initial ≤ braking, initial > 5000, braking time ≤ 0) also stop the mod. A stop comes before any
  write.
- **Each write.**
  - Right before it: reread the pod's record pointer, record and value.
  - The write itself: `write_batch` checks that the 4 bytes are committed private read-write memory (one
    VirtualQuery), writes, then reads the value back.

## Cost

Reads use the adapter's `read_to`: ReadProcessMemory at plain-number addresses into buffers made once. That is
one system call, about 1-2 us in game, and no Lua allocation.

| State | When | Reads | Page checks |
| --- | --- | --- | --- |
| Idle (ship, menus, mission without a loading screen) | every 0.25 s | 4: game object pointer, state, UI pointer, presenters | 0 |
| Loading period | every frame | 11: the same 4; session pointer, client state, hotjoin flags; cutscene pointer, scenes; manager pointer, header | 0 |
| Same, scanning (count changed, or every 0.25 s) | | + 2 scans (sighting and hold) of 1 + one per active pod, + phase, map and height per own pod | 0 |
| Pod found | once | 11 more than the scans: settings 5, factor 1, recheck 3, read back 1, height 1 | 1 (the hold write) |
| Holding | every frame; every 0.25 s also the pod | 9 (signals); 14 with the pod check (manager 2, the pod 3) | 0 |
| Release | once, in the frame the cover ends | 9 signals + 8 | 1 (the release write) |
| Watch, 30 s after a loading period or hold | every 0.25 s | 9 signals + manager 2 + a sighting scan | 0 |

The tests pin these exact counts per frame, and zero Lua garbage per frame while idle, loading and holding. Measured
in live play with the frame probe of Bingus Shared Loader's development build: 0.004 ms per frame in missions and
0.003 on the ship. The mod's own functions run with `jit.off`: they run 4 times a second,
or every frame only during loading, so they add no machine code to the game's shared code cache. Only the shared
runtime's update guard compiles.

## Packaging

The archive holds two resources:

- **`mods/cowboybingus/hellpod_drop_hold`**, a plaintext entry. Its first line is
  `-- HD2-Addon: mods/cowboybingus/hellpod_drop_hold`, and it requires the implementation.
  - Bingus Shared Loader starts only declared plaintext entries that are not in its built-in list.
  - A compiled entry is skipped. That happened in the first live run on 2026-10-05: `Discovery: 1 declared
    entries`, the test agent only.
- **`mods/cowboybingus/hellpod_drop_hold_impl`**, the stripped non-GC64 bytecode.

A loader's own `discover.lua`, run over the built archive, finds the entry (loader v19). Live, with loader v19 in an
automated session to the ship:
- the loader logged `mods/cowboybingus/hellpod_drop_hold: loaded`;
- the mod logged `loading screen up` and `loading screen gone` around the ship's preparing state 5;
- it wrote nothing (no pod), and the game quit clean.

## Logs

`%LOCALAPPDATA%/CowboyBingus/Helldivers2/Logs/HellpodDropHold.log` holds the revision, the status and the last 40
events with seconds since start:
- loading screen up and gone;
- every change of the signals while a loading period or a hold lasts, and for 30 s after. Each line gives:
  - the game state, the HUD, the menu, the popup and the menu stack;
  - from v1.1 also the current and queued cutscene, the client state and the is_hotjoining / has_hotjoined flags;
- from v1.1, every own drop pod the first time it is seen in that window: type, id, height, phase;
- held pod: type, id, height, speed factor;
- released pod: reason, seconds held, height.

These lines give a join's timeline: when preparing ended, when the cutscene ended, when the own pod appeared. Read
them before changing the signals.

## Test builds

`python -B scripts/build.py --test-hold 5` builds `Hellpod-Drop-Hold-TEST-BUILD-v1.2.1.zip`, under its own manager
GUID. It holds every own drop pod for 5 s, loading screen or not, so the hold can be checked in solo play at
mission start or on a reinforcement. Never publish it.

## Tests

`python -B scripts/build.py` runs everything:

- `tests/test_hold.lua`: 18 checks on synthetic memory, with exact frame budgets, in LuaJIT and in the game's own
  `lua51.dll` (`tests/game_lua.py`; the game is never started).
- The archive inspection.
- `tests/test_package.py`.

Not covered offline:
- the game's real loading screen timing;
- frame order between the Lua update and the world update;
- how far a pod falls before the first held frame.

These need live play.

## Live joins (v1.2, 2026-10-05)

In two real joins of missions in progress, the own initial-spawn pod appeared at 1500 m while the join cutscene
still covered the screen. It was held for 8.1 s and 8.2 s and released in the frame the cutscene ended, at
1496 m, and the drops then ran as normal. In one of them the game crashed 2 s after the release, in the render
world's LOD culling job on a worker thread; the same crash had happened before in a session without this mod, and
the mod writes no render data. The other join ran to extraction.
