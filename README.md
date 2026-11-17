# Static Bloom

A neon courier racing game for the web and iOS. Harpoon a ride, slingshot past it, and deliver the package before the window closes.

Everything is generated at runtime: the graphics are drawn in code and the five-track soundtrack is synthesised live, so the app ships no image or audio assets beyond its icon and splash.

## Layout

| Path | What it is |
| --- | --- |
| `src/game.js` | Game, renderer, menus, save data |
| `src/audio.js` | Music engine, the score, sound effects |
| `src/style.css`, `src/body.html` | Interface |
| `build.mjs` | Bundles `src/` into one page |
| `index.html` | Built web version (committed, opens directly in a browser) |
| `ios/` | Capacitor Xcode project |
| `store/` | App icon, splash and App Store screenshots |

## Build

```
npm install
npm run build      # writes index.html and www/
```

## Run on an iPhone

Needs a Mac with Xcode and CocoaPods.

```
npm install
npm run ios        # builds, syncs the iOS project, opens Xcode
```

In Xcode: select the App target, set your Team under Signing & Capabilities, change the bundle identifier from `com.example.staticbloom` to your own (also in `capacitor.config.json`), then run on a device.

## Before submitting

The iOS project was generated on Linux and has not been compiled. Do these on a Mac first:

1. Build and run on a real iPhone and an iPad. Check sound, haptics, the notch and home-indicator spacing, and rotation.
2. Play all five zones on the oldest device you intend to support. The game lowers its render resolution if frames run slow.
3. Confirm the ringer switch silences the game, and that it pauses when you leave the app.
4. Replace the placeholder bundle identifier and set version and build numbers.
5. Archive and upload from Xcode, then test through TestFlight.

## App Store listing

- **Name:** Static Bloom (check availability in App Store Connect)
- **Subtitle:** Neon courier slingshot racer
- **Category:** Games, Racing. Secondary: Arcade
- **Age rating:** 4+. No violence, no user content, no web access, no purchases.
- **Privacy:** Data Not Collected. Progress is stored on the device only. There are no accounts, ads, analytics or network calls. A privacy policy URL is still required.
- **Export compliance:** no non-exempt encryption (already declared in `Info.plist`).
- **Keywords:** cyberpunk,synthwave,racing,arcade,neon,retro,courier,outrun,endless,runner
- **Screenshots:** `store/screenshots/`, sized for the 6.9-inch iPhone (1320 × 2868) and 13-inch iPad (2064 × 2752). They were captured from the web build; retake on a device if anything differs.

**Promotional text**

Harpoon traffic. Slingshot through it. Beat the window.

**Description**

You carry one package and the clock is already running.

Static Bloom is an arcade racer about borrowed speed. Line up behind a ride, fire your harpoon, reel in and slingshot past at one and a half times top speed, phasing through traffic while the burn lasts. Chain harpoons to stay alive. Skim cars and grab shards to buy seconds. Stay out of the static.

- Five zones, each with its own skyline, palette and music track
- A slingshot mechanic that rewards nerve over caution
- Contracts that pay out cred for stylish runs
- A garage of upgrades for your harpoon, boost, clock and shard magnet
- A daily run on a route everyone shares
- An original synth soundtrack generated live as you play
- Reduce Flashing mode, haptics, and separate music and effects volume
- Plays offline. No ads, no accounts, no data collected.

## Credits

Typefaces: Orbitron and Share Tech Mono, both under the SIL Open Font License, bundled through Fontsource.
