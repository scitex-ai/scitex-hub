/** JA/EN strings for the citation graph, keyed off <html lang>. */

const STRINGS = {
  seedPaper: { en: "Seed paper", ja: "起点の論文" },
  citedPaper: { en: "Cited paper", ja: "引用された論文" },
  citations: { en: "citations", ja: "被引用" },
  openDoi: { en: "Open DOI", ja: "DOIを開く" },
  addToLibrary: { en: "Add to library", ja: "ライブラリに追加" },
  saving: { en: "Saving…", ja: "保存中…" },
  saved: { en: "Added", ja: "追加しました" },
  saveFailed: { en: "Could not add", ja: "追加できませんでした" },
  noProject: {
    en: "Select a project first",
    ja: "先にプロジェクトを選択してください",
  },
  explore: { en: "Explore from here", ja: "ここから探索" },
  exploreShort: { en: "Explore", ja: "探索" },
  startFrom: { en: "Start the graph from", ja: "グラフの起点" },
  modeSearch: { en: "A DOI or title", ja: "DOI・タイトル" },
  modeLibrary: { en: "My library", ja: "マイライブラリ" },
  close: { en: "Close", ja: "閉じる" },
  building: {
    en: "Building citation network…",
    ja: "引用ネットワークを作成中…",
  },
  emptyTitle: {
    en: "No citation network found",
    ja: "引用ネットワークが見つかりませんでした",
  },
  emptyNoPaper: {
    en: "No paper with a DOI matched. Try a DOI or a more specific title.",
    ja: "DOI付きの論文が見つかりませんでした。DOIか、より具体的なタイトルで試してください。",
  },
  emptyNoLinks: {
    en: "This paper has no cited works with DOIs in Crossref, so there is nothing to connect.",
    ja: "この論文にはCrossrefでDOI付きの参考文献がないため、つなげる論文がありません。",
  },
  graphSummary: {
    en: "{nodes} papers, {edges} citation links",
    ja: "論文 {nodes} 件・引用リンク {edges} 本",
  },
  hint: {
    en: "Drag to pan · pinch or scroll to zoom · tap a paper",
    ja: "ドラッグで移動・ピンチ/スクロールで拡大・論文をタップ",
  },
  networkOf: { en: "Network: {title}", ja: "ネットワーク: {title}" },
  related: { en: "Papers in this graph", ja: "このグラフの論文" },
} as const;

export type GraphStringKey = keyof typeof STRINGS;

export function graphLang(): "ja" | "en" {
  return (document.documentElement.lang || "en").toLowerCase().startsWith("ja")
    ? "ja"
    : "en";
}

export function gt(
  key: GraphStringKey,
  vars: Record<string, string | number> = {},
): string {
  let s: string = STRINGS[key][graphLang()];
  for (const [k, v] of Object.entries(vars)) s = s.replace(`{${k}}`, String(v));
  return s;
}
