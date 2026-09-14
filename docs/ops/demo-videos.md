# Narrated demo videos

Short "how to" videos for the public demos page (`/demos/`) are rendered from a
scenario spec. Nothing is filmed or voiced by hand: a Playwright browser drives
the real UI with a visible moving cursor, a text-to-speech engine reads the
narration, and ffmpeg burns the captions in and mixes the voice. One spec gives an
English and a Japanese video, captions and transcript; a new video is a new spec.

```
scripts/demo_videos/
  record.py              # replay a scenario, record, narrate, caption, encode
  demo_scenario.py       # scenario YAML schema (load_scenario)
  demo_captions.py       # WebVTT, transcripts, caption line wrapping
  demo_narration.py      # TTS clips (scitex_audio) and narration tracks
  demo_cursor.py         # cursor overlay and click highlight
  scenarios/<app>.yaml   # one file per video
```

## Scenario format

```yaml
app: projects                       # output file stem
title:
  en: Create your first project
  ja: はじめてのプロジェクトを作る
languages: [en, ja]                 # one video, caption file and transcript per language
sign_in: true                       # sign in with DEMO_USERNAME / DEMO_PASSWORD first
steps:
  - action: type                    # goto | click | fill | type | press | hover | scroll | wait
    selector: "#name"               # Playwright selector (click, fill, type, hover; optional for press)
    value: sleep-study-{run_id}     # URL path, text to type, key to press, or scroll pixels
    narration:                      # spoken and captioned; omit for a silent step
      en: Type a name in lowercase letters.
      ja: 名前を小文字で入力します。
    hold: 0.8                       # extra seconds after the narration ends
    only: desktop                   # optional: run this step only for desktop or mobile
```

`value` and `selector` may use `{username}` (the demo account) and `{run_id}`
(the recording time as HHMMSS, so a scenario that creates a project gets a new
name on every run).

Timing is driven by the voice. Before recording, every narration line is
synthesized in every language. During recording each step lasts as long as its
longest narration (or its action, if a page load takes longer) plus `hold`. The
narration starts when its step starts, and the caption cue covers the whole
step. So the English and the Japanese video share one recording and stay in
sync.

For pointer actions the cursor glides to the target before acting, and every
click shows an orange ring.

## Render

Run inside the dev container, which has Playwright, Chromium, ffmpeg,
`scitex_audio` and the Noto Sans JP font. Use a throwaway, non-staff account and
delete it afterwards.

```bash
docker exec -w /app \
  -e DEMO_USERNAME=<demo-user> -e DEMO_PASSWORD=<password> \
  scitex-hub-dev-django-1 \
  python scripts/demo_videos/record.py scripts/demo_videos/scenarios/projects.yaml \
    --base-url http://127.0.0.1:8000 --out-dir media/videos/demos
```

Options: `--date YYYY-MM-DD` (defaults to today), `--viewports desktop,mobile`,
and `--no-voice` for captions only.

Output in `--out-dir`, for each language `<lang>`:

| File | What |
| --- | --- |
| `<app>-<date>.<lang>.mp4` | 1280x720, narrated, captions burned in (H.264 + AAC) |
| `<app>-<date>.<lang>.vtt` | WebVTT captions |
| `<app>-<date>.<lang>.txt` | plain-text transcript |
| `<app>-<date>.webm` | the raw Playwright recording, no audio |
| `<app>-<date>-thumbnail.png` | a frame from the last step |
| `<app>-<date>-mobile.*` | the same at 390x844 |

### Voice

Narration uses `scitex_audio.generate_bytes(text, backend="gtts", voice=<lang>)`.
gTTS needs no API key but does need internet access from the container. If it
fails, the script says why and renders captions only, timing each step by an
estimated reading speed. The ElevenLabs backend in `scitex_audio` gives more
natural voices but needs an `ELEVENLABS_API_KEY`; to use it, change the backend
in `demo_narration.py` and pass a voice id per language instead of a language code.

Without ffmpeg on `PATH` the script keeps the `.webm`, `.vtt` and `.txt` files and
says that it skipped the mp4 and the voice.

### Check before publishing

Watch both languages. A dev server that reloads mid-recording (someone saving a
file in the checkout) shows up as a blank page or a connection error; re-run the
scenario.

Known limits (2026-09-14): Writer's editor is not reachable at 390x844, so render
`writer.yaml` with `--viewports desktop`.

## Publish on the hub

The rendered files are not committed. Copy them to the media volume so they are
served at `/media/videos/demos/`:

```bash
cp <render-dir>/<app>-<date>* /home/ywatanabe/proj/scitex-hub/media/videos/demos/
```

Then add or update the entry in `VIDEO_CATALOG`
(`apps/infra/public_app/views/pages_data.py`): `url` and `ja_url`, `captions` and
`ja_captions`, `thumbnail`, optional `mobile_url`, `narrated: True` (the player
then starts unmuted and does not autoplay) and `playback_rate: 1`. Add the card to
`public_app/pages/demos_partials/guide_cards.html`, and the new file names to
`RENDERED_DEMO_GUIDES` in `tests/apps/public_app/test_demo_video_asset_names.py`.

## Upload to YouTube (later)

Uploading needs the operator's YouTube account, so it is a manual step:

1. Open YouTube Studio for the SciTeX channel and click **Create > Upload videos**.
2. Upload `<app>-<date>.en.mp4` (and `<app>-<date>.ja.mp4` as its own video, or
   use YouTube's multi-language audio if the channel has it).
3. Title: the scenario `title`. Description: the transcript `.txt` plus a link to
   the matching docs page (for example `/apps/docs/#howto-projects`).
4. Under **Subtitles**, upload `<app>-<date>.en.vtt` as English and
   `<app>-<date>.ja.vtt` as Japanese.
5. Upload the 390x844 version as a Short if wanted.
6. Once public, add the YouTube URL to the demos card as another link.
