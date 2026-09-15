/**
 * Writer page stylesheets, bundled into ONE file linked from <head> by
 * {% vite_css 'writer_app/styles' %}. Order is the cascade order the old
 * <link> list used; keep it.
 */
import "/static/writer_app/css/shared/variables.css";
import "/static/shared/css/components/file-tabs.css";
import "/static/writer_app/css/editor/tex-view-main.css";
import "/static/writer_app/css/editor/index-editor-panels.css";
import "/static/writer_app/css/editor/pdf-view-main.css";
import "/static/writer_app/css/components/pdfjs-viewer.css";
import "/static/shared/css/components/alerts.css";
import "/static/shared/css/components/migration-cards.css";
import "/static/shared/css/components/terminal-log.css";
import "/static/writer_app/css/shared/index-ui/00-index-ui.css";
import "/static/writer_app/css/shared/index-ui/01-panel-header.css";
import "/static/writer_app/css/shared/index-ui/02-latex-panel.css";
import "/static/writer_app/css/shared/index-ui/03-preview-panel.css";
import "/static/writer_app/css/shared/index-ui/04-toolbar.css";
import "/static/writer_app/css/shared/index-ui/05-compilation-output.css";
import "/static/writer_app/css/shared/index-ui/06-split-view.css";
import "/static/writer_app/css/shared/index-ui/07-panel-resizer.css";
import "/static/writer_app/css/shared/index-ui/08-save-status.css";
import "/static/writer_app/css/shared/index-ui/09-button-styling.css";
import "/static/writer_app/css/shared/index-ui/10-dark-mode.css";
import "/static/writer_app/css/shared/index-ui/11-responsive.css";
import "/static/writer_app/css/shared/index-ui/12-initialization-prompt.css";
import "/static/writer_app/css/shared/index-ui/13-accessibility.css";
import "/static/writer_app/css/shared/index-ui/15-details-panel.css";
import "/static/writer_app/css/shared/index-ui/16-mobile-panes.css";
import "/static/writer_app/css/components/status-lamp.css";
import "/static/writer_app/css/components/shortcuts-modal.css";
import "/static/writer_app/css/components/sidebar-controls.css";
import "/static/writer_app/css/editor/main-editor-inline.css";
import "/static/writer_app/css/editor/file-tabs.css";
import "/static/writer_app/css/editor/citations-panel/index.css";
import "/static/writer_app/css/editor/figures-panel/index.css";
import "/static/writer_app/css/editor/tables-panel.css";
import "/static/writer_app/css/editor/codemirror-styling.css";
