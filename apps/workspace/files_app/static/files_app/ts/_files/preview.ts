/** Fill the preview pane for one file. */

import {
  API,
  AUDIO,
  el,
  Entry,
  IMAGE,
  linkButton,
  PDF,
  query,
  TEXT,
  VIDEO,
} from "./dom";

const PREVIEW_TEXT_LIMIT = 512 * 1024;

export function renderPreview(
  container: HTMLElement,
  entry: Entry,
  t: (key: string) => string,
  onError: (error: unknown) => void,
): void {
  const src = `${API}raw/${query(entry.path)}`;
  container.replaceChildren();
  if (IMAGE.test(entry.name)) {
    const img = el("img", "files-preview-media");
    img.src = src;
    img.alt = entry.name;
    container.append(img);
  } else if (VIDEO.test(entry.name)) {
    const video = el("video", "files-preview-media");
    video.src = src;
    video.controls = true;
    container.append(video);
  } else if (AUDIO.test(entry.name)) {
    const audio = el("audio", "files-preview-audio");
    audio.src = src;
    audio.controls = true;
    container.append(audio);
  } else if (PDF.test(entry.name)) {
    const frame = el("iframe", "files-preview-frame");
    frame.src = src;
    frame.title = entry.name;
    container.append(frame);
  } else if (TEXT.test(entry.name) && entry.size <= PREVIEW_TEXT_LIMIT) {
    const pre = el("pre", "files-preview-text");
    container.append(pre);
    fetch(src, { credentials: "same-origin" })
      .then((r) => r.text())
      .then((body) => {
        pre.textContent = body;
      })
      .catch(onError);
  } else {
    container.append(el("p", "files-preview-none", t("noPreview")));
  }
  const actions = el("div", "files-preview-actions");
  actions.append(
    linkButton(
      t("download"),
      "fa-download",
      `${API}download/${query(entry.path)}`,
    ),
  );
  if (entry.project_url) {
    actions.append(
      linkButton(
        t("openInProject"),
        "fa-up-right-from-square",
        entry.project_url,
      ),
    );
  }
  container.append(actions);
}
