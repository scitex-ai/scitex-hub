/**
 * Global <head> stylesheets, part 1 (before site-content-frame.css), bundled
 * into one file by {% vite_css 'shared/head-styles-base' %} in
 * global_head_styles.html. ~100 separate <link>/@import files queued behind
 * the browser's six connections and held first paint on every page.
 * Order is cascade order; keep it.
 */
import "/static/shared/css/primitives/variables.css";
import "/static/shared/css/components/icon-sizes.css";
import "/static/shared/css/common.css";
import "/static/shared/css/base/bootstrap-override/index.css";
import "/static/shared/css/components/modal.css";
import "/static/shared/css/components/shortcuts-modal.css";
import "/static/shared/css/layouts/global-base.css";
