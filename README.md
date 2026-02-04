# NVDA Media Player Addon

A lightweight, high-quality background media player integrated directly into NVDA. Play your music and podcasts with minimal resource usage and zero interruptions to your screen reading workflow.

## Key Features
- **High Quality Audio**: Powered by the BASS audio library for crystal clear playback and support for various formats (MP3, WAV, OGG, FLAC, M4A, WMA).
- **Extremely Low Footprint**: Uses disk streaming to keep memory usage under 5MB, even for multi-hour recordings.
- **Persistent Memory**: Automatically remembers your last played track, exact position, and volume level across NVDA restarts.
- **Smart Playlists**: Open one file, and the player automatically discovers all other tracks in that folder for seamless navigation.
- **Accessible UI**: Uses native Windows dialogs and provides clear speech feedback for every action.

## Installation / Packaging
1. Double-click **`package.bat`** in the project root.
2. This will generate a file named **`nvda_media_player.nvda-addon`**.
3. Install this file into NVDA like any other addon.

## Shortcuts
- `NVDA+Shift+M`: **Open File** (Select a track and automatically load the folder)
- `NVDA+Shift+R`: **Resume Playback** (Pick up exactly where you left off)
- `NVDA+Shift+.`: **Play / Pause**
- `NVDA+Shift+/`: **Next Track**
- `NVDA+Shift+,`: **Previous Track**
- `NVDA+Shift+S`: **Toggle Shuffle**
- `NVDA+Shift+V`: **Toggle Autoplay** (Move to next song automatically)
- `Alt+NVDA+'` (Apostrophe): **Volume Up**
- `Alt+NVDA+;` (Semicolon): **Volume Down**
- `NVDA+Shift+;`: **Rewind** (by current interval)
- `NVDA+Shift+'`: **Fast Forward** (by current interval)
- `NVDA+Shift+J`: **Cycle Seek Interval** (5s, 15s, 30s, 1m, 5m, 30m, 1h)

## Seek Intervals
The default seek interval is 15 seconds. You can cycle through the intervals using `NVDA+Shift+J`. NVDA will announce the active interval.
- 5 / 15 / 30 seconds
- 1 / 5 / 30 minutes
- 1 hour
