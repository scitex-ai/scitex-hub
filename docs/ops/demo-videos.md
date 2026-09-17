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
  demo_tools.py          # locate ffmpeg/ffprobe, read durations, check the caption font
  demo_selectors.py      # stale-selector and UI-contract detection
  demo_manifest.py       # reproducible metadata (commit, digests, toolchain)
  demo_watch_gate.py     # the human watch gate for both languages
  verify_playback.py     # play a render in Chromium and measure the language switch
  scenarios/<app>.yaml   # one file per video
  scenarios/smoke-*.yaml # pipeline smoke tours that need no demo account (not published)
```

The public player's language switch is
`apps/infra/public_app/static/public_app/js/demo-video-player.js`, and the
rendition list it switches between comes from
`apps/infra/public_app/views/demo_video_languages.py`.

## Scenario format

```yaml
app: projects                       # output file stem
title:
  en: Create your first project
  ja: はじめてのプロジェクトを作る
languages:                          # one recording per language, UI switched to `locale`
  en: {locale: en}
  ja: {locale: ja}
alternates:                         # optional extra UI-locale renditions
  - language: ja                    # narration and captions in this language
    ui_locale: en                   # recorded with the UI in this language
    reason: The editor labels are not translated yet.
viewports: [desktop, mobile]        # 1280x720 and 390x844; list only those where the flow works
sign_in: true                       # sign in with DEMO_USERNAME / DEMO_PASSWORD first
steps:
  - action: type                    # goto | click | fill | type | press | hover | scroll | wait
    selector: "#name"               # Playwright selector (click, fill, type, hover; optional for press)
    value:                          # URL path, text to type, key to press, or scroll pixels
      en: Does sleep improve memory?
      ja: 睡眠は記憶を良くするか？
    narration:                      # spoken and captioned; omit for a silent step
      en: Type a name in lowercase letters.
      ja: 名前を小文字で入力します。
    hold: 0.8                       # extra seconds after the narration ends
    only: desktop                   # optional: run this step only for desktop or mobile
```

`narration`, `selector` and `value` are either one text for every language or a
mapping with an entry per language. Prefer language-neutral selectors (ids, data
attributes) so the same selector works in every UI language. `value` and
`selector` may use `{username}` (the demo account) and `{run_id}` (the recording
time as HHMMSS, so a scenario that creates a project gets a new name on every
run).

A canonical rendition records each language over the UI in that same language.
When a page is not translated yet — Writer's editor is the standing example — the
scenario declares an `alternates` entry instead: the same action timeline, the
same narration, recorded with the UI in the language that is finished. Its files
carry a `.ui-<locale>` infix (`writer-2026-09-14.ui-en.ja.mp4`) so the canonical
names never move, and the reason is required because the published card has to say
which screen the viewer is looking at. `--no-alternates` skips them.

A step may also declare a `chapter`: a short, localized name for that span of the
walkthrough. Chapters come from the same narration-driven timeline as the
captions, so a viewer switching to an alternate UI-locale rendition is looking at
the same map of the steps. They are written to
`<app>-<date>.<lang>.chapters.vtt` and listed at the top of the transcript as
`MM:SS Title` lines, which is the form YouTube reads out of a description, so the
upload step does not retype them. Chapters are optional and per step: a scenario
without them records exactly as before.

The scenario is recorded once per viewport x rendition. Before each recording the
script opens the first page the scenario visits and picks the language in the
site's own language switcher (footer globe menu), so the Japanese video shows the
Japanese UI where the Japanese UI exists.

Timing is driven by the voice. Before recording, every narration line is
synthesized. During recording each step lasts as long as its narration (or its
action, if a page load takes longer) plus `hold`. The narration starts when its
step starts, and the caption cue covers the whole step.

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

Options: `--date YYYY-MM-DD` (defaults to today), `--viewports`, `--languages` and
`--renditions language:ui_locale` to render a subset of the scenario's matrix (for
example re-running one language after a failed recording), `--no-alternates`,
`--no-voice` for captions only, `--dry-run` to print the matrix after the selector
check without recording, and `--allow-stale` to record anyway when a selector has
moved (for capturing evidence of the drift, not for publishing).

A subset that selects nothing is refused (exit 5) and says what the scenario
offers: `--viewports mobile` against a desktop-only scenario used to record
nothing and exit 0, leaving a manifest with an empty matrix — an empty render that
reports success is worse than a refusal, because it looks like the 390 px path was
exercised.

### Prove a render will work before spending ten minutes on it

`--preflight` answers the questions only a browser can answer — is the site up,
does the demo account sign in, does the language switcher reach each rendition's
locale, does every page the scenario opens load — and then stops:

```bash
DEMO_USERNAME=... DEMO_PASSWORD=... \
  python scripts/demo_videos/record.py scripts/demo_videos/scenarios/projects.yaml \
    --preflight --base-url http://127.0.0.1:8000
```

It never clicks or types, so it does not create a project, write a file or send a
message: a preflight with side effects would be useless for a signed-in scenario,
whose first write is exactly what you are trying to de-risk. Exit 0 ready, 4 with
the reason, 2 when the credentials are missing (a dry run and a preflight do not
need them). When the account is missing the report says so and states that the
scenario's pages were not checked at all, rather than reporting pages it only saw
a redirect for.

### The media tools

The renderer finds ffmpeg itself instead of trusting `PATH`, because the
Playwright browser bundle ships an ffmpeg with no H.264 or AAC support and no
ffprobe at all — a machine can look "ready" and still be unable to encode the mp4
or synthesize the voice. Resolution order is `--ffmpeg`/`--ffprobe`, then
`SCITEX_DEMO_FFMPEG`/`SCITEX_DEMO_FFPROBE`, then `PATH`, then the static
`imageio-ffmpeg` wheel. Durations come from ffprobe when it exists and from
`ffmpeg -i` when it does not; the manifest records which binaries were used and
which encoders that build has.

`scitex_audio` reads durations through pydub, which needs `ffprobe` on `PATH`.
Without it the render still produces the webm, `.vtt` and `.txt` files, says so,
and records `voice: false` with the reason in `narration_failures` — a manifest
never claims narration over a silent file.

### Caption font

Burned-in captions need a font with Japanese glyphs. If `Noto Sans JP` is not
installed, pass `--fonts-dir <dir>` or `SCITEX_DEMO_FONTS_DIR` and the renderer
hands that directory to libass; the render warns when the font cannot be found
either way, because a fallback font renders boxes instead of kana.

Output in `--out-dir`, for each language `<lang>`:

| File | What |
| --- | --- |
| `<app>-<date>.<lang>.mp4` | 1280x720, narrated, captions burned in (H.264 + AAC) |
| `<app>-<date>.<lang>.vtt` | WebVTT captions |
| `<app>-<date>.<lang>.chapters.vtt` | chapter track, one cue per named span |
| `<app>-<date>.<lang>.txt` | transcript, with the chapter list when the scenario has one |
| `<app>-<date>.<lang>.webm` | the raw Playwright recording, no audio |
| `<app>-<date>.<lang>.thumbnail.png` | a frame from the last step |
| `<app>-<date>-thumbnail.png` | the catalog thumbnail (desktop, first language) |
| `<app>-<date>-mobile.<lang>.*` | the same at 390x844 |
| `<app>-<date>.manifest.json` | reproducible metadata for the whole run |
| `<app>-<date>.watch-gate.json` | the human watch gate, unrecorded |
| `<app>-<date>.ui-<locale>.<lang>.*` | an alternate UI-locale rendition |

### Selector checks (stale detection)

Before anything is recorded, `record.py` runs
`scripts/demo_videos/demo_selectors.py`: every selector the scenario uses must
exist in this checkout, and every control the pipeline depends on must still carry
its contract token in the file that owns it. A control that moved stops the render
with exit code 3 rather than producing a video of the wrong screen.

```bash
python scripts/demo_videos/demo_selectors.py --repo-root . --live-base-url http://127.0.0.1:8000 \
  --json-out /tmp/selectors.json
```

`--live-base-url` adds the live half: the controls that exist on a signed-out page
(the sign-in form, the footer language switcher) are resolved against a running
site, with the attached and visible counts both reported — the language menu is in
the DOM but hidden until its trigger is clicked, so existence and visibility are
different questions. The signed-in controls are resolved by the render itself,
because they cannot be reached without the demo account.

Selectors that are not ids or data attributes are reported as fragile (the strict
flag is `--strict-semantic`), and selectors whose owner is outside this checkout
are listed as unverifiable and confirmed against the live DOM at record time.
`tests/scripts/test_demo_video_selector_coverage.py` runs the static check over
every scenario in CI, and pins the fragile and unverifiable sets so adding one is
a decision rather than a drift.

### Reproducible metadata

Each run writes `<app>-<date>.manifest.json`: the scenario and its sha256, the
commit/branch/dirty state of the checkout, the toolchain (python, playwright,
ffmpeg/ffprobe and their encoders, narration backend, caption font), the
UI-contract fingerprint and per-selector verdicts, the step timings, and the
sha256, size and duration of every artifact. Rerunning the same scenario at the
same commit reproduces the captions and transcripts byte for byte; the encoded
mp4 is expected to differ, which is why the digests are recorded rather than
assumed.

```bash
python - <<'EOF'
import json, sys
sys.path.insert(0, "scripts/demo_videos")
from demo_manifest import load_manifest, verify_manifest
print(verify_manifest(load_manifest("media/videos/demos/projects-2026-09-17.manifest.json"),
                      "media/videos/demos"))
EOF
```

A manifest also carries the fingerprint of the UI contracts it was recorded
against. The report answers the publishing question for a whole directory —
which videos are intact, and which were recorded against a UI contract that has
since moved:

```bash
python scripts/demo_videos/demo_manifest.py --dir media/videos/demos --repo-root . --json-out /tmp/report.json
```

One row per manifest: `artifacts_verified` (every file still matches its recorded
sha256), `stale` with the `changed_contracts`/`broken_contracts` that moved, and
the watch-gate status. Exit 1 when a row is stale or unverified. Videos that
predate the manifest simply do not appear — the published 2026-09-14 guides carry
no recorded metadata, so the report says so instead of guessing their contract
set.

### Playback verification

Template assertions do not prove that the player keeps the viewer's place when the
language changes, so the switch is measured in a real browser against the recorded
files:

```bash
python scripts/demo_videos/verify_playback.py \
  --manifest media/videos/demos/projects-2026-09-17.manifest.json \
  --json-out /tmp/playback.json
```

It loads the shipped player script, plays the desktop rendition, seeks into the
middle, sets a non-default rate, clicks the other language, and reports position
drift, playback rate, pause state, caption language and whether playback
continued. It exits non-zero when a check fails. `--page-url` runs the same
measurement against a deployed page and reports `not_deployed` when that page
still has no rendition list.

### Human watch gate — both languages

The Japanese rendition is the one that silently breaks (untranslated pages,
wrapped captions), so publishing requires a watch of every language:

```bash
# record a watch (per language); the entry is bound to the artifact's sha256
python scripts/demo_videos/demo_watch_gate.py record \
  media/videos/demos/projects-2026-09-17.watch-gate.json \
  --language ja --by <operator> --verdict pass --watched-seconds 63 \
  --notes "captions clear of the dock; narration matches the screen"

# the publish check: exits 1 until both languages pass against the current files
python scripts/demo_videos/demo_watch_gate.py status \
  media/videos/demos/projects-2026-09-17.watch-gate.json \
  --out-dir media/videos/demos
```

Re-rendering a language invalidates its watch, and a watch of a few seconds is not
a watch. The gate cannot be satisfied by the pipeline: the person who watched is
recorded by name.

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

In order, none of which is optional:

1. `demo_selectors.py` clean for the scenario (the render refuses otherwise).
2. `verify_manifest` against the render directory: the manifest and the files agree.
3. `verify_playback.py --manifest ...`: the language switch keeps its place with
   real media.
4. `demo_watch_gate.py status ... --out-dir ...`: a named person watched both
   languages against the files being published.

A dev server that reloads mid-recording (someone saving a file in the checkout)
shows up as a blank page or a connection error; re-run the scenario.

Known limits (2026-09-14): Writer's editor is not reachable at 390x844, so
`writer.yaml` lists only the desktop viewport. The Writer page itself is not yet
translated, so its Japanese video still shows the English Writer labels; that is
what `writer.yaml`'s alternate rendition records on purpose.

`scenarios/smoke-public-demos.yaml` is a pipeline smoke tour: every step is
reachable signed out, so the whole pipeline (narration, cues, burned captions,
mp4, thumbnail, manifest, gate) can be rendered and verified on a machine with no
demo account. It is not in `VIDEO_CATALOG` and its files are not published.

## Publish on the hub

The rendered files are not committed. Copy them to the media volume so they are
served at `/media/videos/demos/`:

```bash
cp <render-dir>/<app>-<date>* /home/ywatanabe/proj/scitex-hub/media/videos/demos/
```

Then add or update the entry in `VIDEO_CATALOG`
(`apps/infra/public_app/views/pages_data.py`): `url` and `ja_url`, `captions` and
`ja_captions`, `thumbnail`, optional `mobile_url` and `ja_mobile_url`,
`narrated: True` (the player
then starts unmuted and does not autoplay) and `playback_rate: 1`. Add the card to
`public_app/pages/demos_partials/guide_cards.html`, and the new file names to
`RENDERED_DEMO_GUIDES` in `tests/apps/public_app/test_demo_video_asset_names.py`.

For a video that publishes more than the flat English/Japanese pair — an alternate
UI-locale rendition from a scenario's `alternates` — add a `renditions` list to
the catalog entry instead: one entry per rendition with `language`, `ui_locale`,
`url`, `captions` and, for an alternate, a `note` saying which UI the viewer is
looking at. The player renders one control per rendition from that list, and
captions follow the narration language, not the UI language. The flat keys stay
for the Open Graph tags and the download links.

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
