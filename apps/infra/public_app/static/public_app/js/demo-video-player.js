/*
 * Position-preserving language switch for the narrated demo videos.
 *
 * A narrated guide ships as one video per language: English narration over the
 * English UI and Japanese narration over the Japanese UI. They are separate
 * files, so naively swapping <video src> restarts the playback from zero — the
 * viewer loses their place in the middle of the walkthrough, which is exactly
 * where the language buttons are useful. This script swaps the file and puts
 * the viewer back where they were.
 *
 * Contract with the template (kept in sync by
 * tests/apps/public_app/test_demo_video_player_contract.py):
 *
 *   #demo-video                        the video element
 *     data-languages='[...]'           JSON: one entry per rendition,
 *                                      {code,label,src,captions,ui_locale,note}
 *   button[data-demo-lang="<code>"]    one control per rendition
 *   #demo-video-language-status        aria-live region for the switch
 *
 * What is preserved across a switch: currentTime (within seek tolerance),
 * playbackRate, whether the video was playing, and the caption language.
 * `window.demoVideoPlayer.state()` exposes the same values for automated
 * playback verification (scripts/demo_videos/verify_playback.py).
 */
(function () {
  'use strict';

  var PLAYER_ID = 'demo-video';
  var STATUS_ID = 'demo-video-language-status';
  var EVENT_NAME = 'demo-video-language-changed';
  // A seek lands on the nearest keyframe, so a restore that is a fraction of a
  // second off is correct behaviour, not a failure.
  var TOLERANCE_SECONDS = 0.75;

  function readLanguages(video) {
    try {
      var parsed = JSON.parse(video.dataset.languages || '[]');
      return Array.isArray(parsed) ? parsed : [];
    } catch (error) {
      return [];
    }
  }

  function activeRendition(video) {
    return video.dataset.activeLanguage || '';
  }

  function setStatus(message) {
    var status = document.getElementById(STATUS_ID);
    if (status) {
      status.textContent = message;
    }
  }

  function captionTrackFor(video, code) {
    var tracks = video.textTracks || [];
    for (var index = 0; index < tracks.length; index += 1) {
      var track = tracks[index];
      var element = track.track || track;
      var language = (element && element.language) || '';
      if (language === code) {
        return track;
      }
    }
    return null;
  }

  function showCaptionsFor(video, code) {
    var tracks = video.textTracks || [];
    for (var index = 0; index < tracks.length; index += 1) {
      var track = tracks[index];
      var element = track.track || track;
      var language = (element && element.language) || '';
      track.mode = language === code && code ? 'showing' : 'disabled';
    }
  }

  function markButtons(code) {
    var buttons = document.querySelectorAll('button[data-demo-lang]');
    for (var index = 0; index < buttons.length; index += 1) {
      var button = buttons[index];
      var isActive = button.dataset.demoLang === code;
      button.setAttribute('aria-pressed', isActive ? 'true' : 'false');
      if (isActive) {
        button.classList.add('is-active');
      } else {
        button.classList.remove('is-active');
      }
    }
  }

  function initialize(video) {
    var languages = readLanguages(video);
    if (!languages.length) {
      return null;
    }
    var byCode = {};
    languages.forEach(function (entry) {
      byCode[entry.code] = entry;
    });

    function state() {
      return {
        language: activeRendition(video),
        currentTime: video.currentTime,
        duration: video.duration,
        playbackRate: video.playbackRate,
        paused: video.paused,
        captionsLanguage: (function () {
          var tracks = video.textTracks || [];
          for (var index = 0; index < tracks.length; index += 1) {
            if (tracks[index].mode === 'showing') {
              var element = tracks[index].track || tracks[index];
              return (element && element.language) || '';
            }
          }
          return '';
        })(),
      };
    }

    function select(code) {
      var target = byCode[code];
      if (!target) {
        return Promise.resolve(state());
      }
      if (code === activeRendition(video)) {
        // Same file, different captions: the position is already right, only the
        // subtitle track has to move.
        showCaptionsFor(video, target.captionCode || code);
        markButtons(code);
        return Promise.resolve(state());
      }
      var wasPlaying = !video.paused && !video.ended;
      var position = video.currentTime;
      var rate = video.playbackRate;
      var previous = activeRendition(video);

      function restore() {
        video.removeEventListener('loadedmetadata', restore);
        var duration = isFinite(video.duration) ? video.duration : null;
        var wanted = duration ? Math.min(position, Math.max(duration - 0.25, 0)) : position;
        video.currentTime = wanted;
        video.playbackRate = rate;
        showCaptionsFor(video, target.captionCode || code);
        if (wasPlaying) {
          var played = video.play();
          if (played && typeof played.catch === 'function') {
            played.catch(function () {
              /* autoplay policy: the picture is switched, the viewer resumes */
            });
          }
        }
        video.dataset.activeLanguage = code;
        video.setAttribute('data-active-language', code);
        markButtons(code);
        var drift = video.currentTime - position;
        setStatus(target.label + ' audio and captions selected.');
        document.dispatchEvent(
          new CustomEvent(EVENT_NAME, {
            detail: {
              from: previous,
              to: code,
              position: position,
              restoredTo: video.currentTime,
              drift: drift,
              withinTolerance: Math.abs(drift) <= TOLERANCE_SECONDS,
              playbackRate: video.playbackRate,
              paused: video.paused,
            },
          })
        );
      }

      // `load()` resets currentTime to 0 and re-runs the caption tracks, so the
      // restore has to wait for the new file's metadata.
      video.addEventListener('loadedmetadata', restore);
      video.setAttribute('aria-busy', 'true');
      video.src = target.src;
      if (target.captions) {
        updateCaptionTracks(video, target);
      }
      video.load();
      video.addEventListener(
        'canplay',
        function () {
          video.removeAttribute('aria-busy');
        },
        { once: true }
      );
      return Promise.resolve();
    }

    function updateCaptionTracks(video, target) {
      // The Japanese rendition carries its own WebVTT file; if the template
      // already rendered a track for the target language, point it at the new
      // source instead of duplicating cues.
      var track = captionTrackFor(video, target.captionCode || target.code);
      if (track) {
        var element = track.track || track;
        if (element && element.src !== target.captions && element.setAttribute) {
          element.setAttribute('src', target.captions);
        }
        return;
      }
      var created = document.createElement('track');
      created.kind = 'captions';
      created.label = target.label;
      created.srclang = target.captionCode || target.code;
      created.src = target.captions;
      video.appendChild(created);
    }

    var buttons = document.querySelectorAll('button[data-demo-lang]');
    for (var index = 0; index < buttons.length; index += 1) {
      (function (button) {
        button.addEventListener('click', function () {
          select(button.dataset.demoLang);
        });
      })(buttons[index]);
    }

    var initial = video.dataset.activeLanguage || (video.dataset.defaultLanguage || languages[0].code);
    video.dataset.activeLanguage = initial;
    video.setAttribute('data-active-language', initial);
    markButtons(initial);
    // Captions stay off unless the page says which language to start with (the
    // visitor's site language, when a matching file exists); picking a language
    // always switches its captions on.
    showCaptionsFor(video, video.dataset.defaultCaptions || '');

    return {
      languages: languages,
      select: select,
      state: state,
      toleranceSeconds: TOLERANCE_SECONDS,
      eventName: EVENT_NAME,
    };
  }

  function boot() {
    var video = document.getElementById(PLAYER_ID);
    if (!video) {
      return;
    }
    window.demoVideoPlayer = initialize(video);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
