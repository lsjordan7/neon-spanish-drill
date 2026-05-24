# NEÓN // ES — Spanish drill, cyberpunk edition

Single-file flashcard app for Castilian (Spain) Spanish, covering every CEFR
level from **A1 → C2** with three decks per level:

- **Sustantivos** — high-frequency nouns
- **Verbos** — core verbs with present-tense conjugations
- **Frases** — essential everyday expressions and idioms

Every Spanish card front plays a real `es-ES-ElviraNeural` voice clip, so
pronunciation is identical at every level — no robotic device TTS unless an
audio file is missing.

## Open it

Double-clicking `index.html` from Finder works on macOS, but audio (the
prerecorded MP3s) won't load over `file://`. Serve the folder over HTTP
instead, e.g. from inside this directory:

```sh
python3 -m http.server 8080
```

then open <http://localhost:8080/>.

## How it works

- **Tap** the card to flip; tap again to flip back.
- **Swipe right** — "I know this" (moves the card up a box; it appears less often).
- **Swipe left** — "I don't know this" (resets to box 1; it reappears soon).
- 🔊 button or `S` key — play the audio.
- Keyboard: `→` known, `←` unknown, `Space` or `Enter` flip, `Esc` back.

Progress is saved per-deck in `localStorage` under the key `neon-progress-v1`.
The settings cog lets you choose a specific Spanish voice for the fallback
TTS, adjust speech rate, or reset all progress.

## Regenerating the audio

The MP3s in `audio/words/` were generated with [`edge-tts`](https://pypi.org/project/edge-tts/)
using the `es-ES-ElviraNeural` voice at `-10%` rate. To regenerate everything
from scratch (or just the clips you've added since):

```sh
pip install --user edge-tts
python3 tools/build_audio.py              # generate everything missing
python3 tools/build_audio.py --force      # regenerate all
python3 tools/build_audio.py --kind phrases   # only one category
python3 tools/build_audio.py --dry-run    # list what would change
```

The script parses the `VOCAB` object literal out of `index.html` and writes
`audio/words/<slug>.mp3` files using the same slug rule as the app's
`normalize()` function.

## Adding vocabulary

Edit the `VOCAB` object in `index.html`. Each level has three arrays:

```js
nouns:   [{w:"casa",    e:"house",    g:"f"}, ...]
verbs:   [{i:"hablar",  e:"to speak", c:"hablo / hablas / habla"}, ...]
phrases: [{s:"Hola",    e:"Hello",    n:"Optional usage note"}, ...]
```

After adding entries, run `python3 tools/build_audio.py` to fetch the new
audio clips.

## Files

- `index.html` — the whole app (HTML + CSS + JS + vocabulary, single file).
- `audio/words/*.mp3` — pre-rendered Spanish (Spain) audio, one file per spoken string.
- `tools/build_audio.py` — `edge-tts`-based generator that keeps the audio set in sync with the vocabulary.

## Credits

Built as a companion to the [Cuéntame](https://github.com/lsjordan7/cuentame)
Spanish-learning project, sharing its Elvira-Neural voice for consistency.
