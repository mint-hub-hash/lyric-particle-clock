# 🎵 Lyric Particle Clock

**A full-screen, audio-reactive particle clock for your desktop — with lyrics that sync to the song, detected automatically on your own machine.**

[繁體中文](README.zh-TW.md) ·  · MIT license

!\[demo](docs/demo.gif)

Thousands of particles form the current time. They breathe, ripple and explode with the beat of whatever you play, and the lyrics fade in underneath, line by line, in time with the music. Leave it running as a screensaver.

## Features

* **Particle clock** — 3,200 particles re-form `HH:MM:SS` every second (plain HTML5 Canvas, no build step, no dependencies).
* **Reacts to sound** — microphone, a local audio file, or a built-in demo beat. Kicks make the particles burst and shift colour.
* **10 up/down motion modes** — switch with keys `1`–`9`, `0`, or let it auto-cycle:
sine wave · spectrum bars · mirror expand · ripple · breathing · bounce · waterfall · jitter · double helix · curtain.
* **Synced lyrics, automatically**

  1. **Local AI (recommended):** `lyrics\_server.py` downloads a small [Whisper](https://github.com/openai/whisper) model (via [faster-whisper](https://github.com/SYSTRAN/faster-whisper)) and transcribes your song *on your machine*. Lines stream into the page while it is still transcribing. Audio never leaves your computer.
  2. **LRCLIB lookup:** if no local server is running, the page looks the song up on [LRCLIB](https://lrclib.net) by ID3 tags / filename (works on the GitHub Pages demo).
  3. **Manual:** drop an `.lrc` file next to the audio when you pick it.
When no lyrics exist, it shows a short quote only while sound is playing.
* Screensaver feel: controls auto-hide, `F` for fullscreen, `Space` to pause, `\[` / `]` to nudge lyric timing.

## Quick start

**Just look at it** (demo beat, microphone, or a local file; LRCLIB lyrics when online):

```bash
git clone https://github.com/mint-hub-hash/lyric-particle-clock
cd lyric-particle-clock
# open index.html in a browser — or use the live demo link above
```

**With local AI lyrics** (Python 3.9+):

```bash
python lyrics\_server.py --model small           # first run installs faster-whisper and downloads the model
python lyrics\_server.py --model medium --lang zh --trad   # better for Chinese; --trad outputs Traditional
```

Your browser opens `http://127.0.0.1:8765/`. Pick a song with **本地音乐 / 歌词** and the lyrics appear as they are recognised.

Only want a `.lrc` file? `python lyrics\_server.py --lrc "song.mp3"`

|Model|Rough size|Notes|
|-|-|-|
|`small`|\~0.5 GB|default, fast, OK for most songs|
|`medium`|\~1.5 GB|noticeably better for Chinese/Japanese; fits in 6 GB of VRAM|
|`large-v3`|\~3 GB|best accuracy, slow|

GPU: with an NVIDIA card the script offers to install the CUDA libraries it needs; otherwise it falls back to CPU (slower). `--device cpu|cuda|auto`.

## How it works

```
index.html  ──(song file)──►  lyrics\_server.py  ──►  faster-whisper (local)
     ▲                              │
     └────── NDJSON stream of {start, end, text} lines ──┘
```

The page plays the file with the Web Audio API, reads the spectrum from an `AnalyserNode`, and shows the line whose timestamp matches `audio.currentTime`.

## Known limitations

* Singing is harder to transcribe than speech. Loud instrumentals can cause missing or wrong words; the server filters low-confidence segments but it is not perfect. Use `\[` / `]` to nudge timing, or load a hand-made `.lrc`.
* System audio (Spotify, YouTube…) cannot be captured by a web page directly; use a "stereo mix"/loopback device as the microphone input.
* Microphone mode uses the browser's speech recognition for subtitles, which is not tuned for music.
* The UI is currently Chinese. Translations welcome.

## Roadmap

* \[ ] English/Japanese UI
* \[ ] Vocal separation before transcription (Demucs) for better accuracy
* \[ ] Word-level karaoke highlighting
* \[ ] Custom fonts, colour themes, 12/24-hour switch, hide seconds
* \[ ] Electron/Tauri wrapper for a real screensaver

Contributions and new motion modes are very welcome — a mode is a single function in the `MODES` array in `index.html`.

## Credits

[faster-whisper](https://github.com/SYSTRAN/faster-whisper), [OpenAI Whisper](https://github.com/openai/whisper) (MIT), [LRCLIB](https://lrclib.net), [OpenCC](https://github.com/BYVoid/OpenCC).
Lyrics are fetched or generated on the user's machine; this project does not bundle any copyrighted lyrics.

