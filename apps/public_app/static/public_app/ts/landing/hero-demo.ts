/**
 * Hero Demo Video Player
 * Handles play/pause, speed control, and overlay for landing page demo video
 */

function initHeroDemo(): void {
  const container = document.getElementById("hero-demo-container");
  const thumbnail = document.getElementById(
    "hero-demo-thumbnail",
  ) as HTMLImageElement | null;
  const video = document.getElementById(
    "hero-demo-video",
  ) as HTMLVideoElement | null;
  const speedSelect = document.getElementById(
    "hero-speed-select",
  ) as HTMLSelectElement | null;
  const playOverlay = document.getElementById("hero-play-overlay");

  if (!container || !thumbnail || !video || !speedSelect) {
    return; // Not on landing page or elements not found
  }

  container.addEventListener("click", () => {
    if (video.paused) {
      thumbnail.style.display = "none";
      if (playOverlay) playOverlay.style.display = "none";
      video.style.display = "block";
      video.controls = true;
      video.playbackRate = parseFloat(speedSelect.value);
      video.play();
    }
  });

  speedSelect.addEventListener("change", () => {
    video.playbackRate = parseFloat(speedSelect.value);
  });

  video.addEventListener("ended", () => {
    thumbnail.style.display = "block";
    if (playOverlay) playOverlay.style.display = "flex";
    video.style.display = "none";
    video.controls = false;
  });
}

// Initialize on DOM ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initHeroDemo);
} else {
  initHeroDemo();
}

export { initHeroDemo };
