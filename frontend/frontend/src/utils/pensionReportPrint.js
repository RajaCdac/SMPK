/** Shared landscape print hook for all pension bill / report printouts. */
export const PENSION_REPORT_PRINT_CLASS = "pension-report-printing";
export const PRINT_PORTAL_ID = "pension-print-portal";
const PRINT_PAGE_STYLE_ID = "pension-print-page-style";

const PRINT_ROOT_SELECTOR =
  ".lic-report-print, .bill-abstract-print, .proposal-sanction-print, .fp-proposal-print, .fp-dih-print, .fp-advice-print, .comm-sanction-print, .sepcom-bill-print, .journal-summary-print, .fp-bill-print, .fp-lic-bill-print";

/** Force @page orientation (Chrome often ignores named CSS page rules). */
function applyPageOrientation(orientation = "landscape") {
  let el = document.getElementById(PRINT_PAGE_STYLE_ID);
  if (!el) {
    el = document.createElement("style");
    el.id = PRINT_PAGE_STYLE_ID;
    document.head.appendChild(el);
  }
  const size =
    orientation === "portrait" ? "A4 portrait" : "A4 landscape";
  const margin = orientation === "portrait" ? "12mm" : "8mm";
  el.textContent = `@page { size: ${size}; margin: ${margin}; }`;
  return el;
}

function clearPageOrientation() {
  document.getElementById(PRINT_PAGE_STYLE_ID)?.remove();
}

function resolvePrintScope(trigger) {
  if (trigger?.closest) {
    const pane = trigger.closest(".tab-pane");
    if (pane) return pane;
  }

  return (
    document.querySelector(".pension-reports .tab-pane.active.show") ||
    document.querySelector(".pension-reports .tab-pane.show.active")
  );
}

function findPrintRoot(trigger) {
  const scope = resolvePrintScope(trigger);
  if (scope) {
    const scoped = scope.querySelector(PRINT_ROOT_SELECTOR);
    if (scoped) return scoped;
  }

  return document.querySelector(PRINT_ROOT_SELECTOR);
}

function ensurePrintPortal() {
  let portal = document.getElementById(PRINT_PORTAL_ID);
  if (!portal) {
    portal = document.createElement("div");
    portal.id = PRINT_PORTAL_ID;
    portal.className = "pension-print-portal";
    document.body.appendChild(portal);
  }
  return portal;
}

function clonePrintRoot(source) {
  const clone = source.cloneNode(true);
  clone.querySelectorAll("img").forEach((img, index) => {
    const src = img.getAttribute("src");
    if (src) {
      img.setAttribute("src", src);
    }
    if (!img.getAttribute("alt") && index === 0) {
      img.setAttribute("alt", "SMP Kolkata");
    }
  });
  return clone;
}

export function printPensionReport(event, options = {}) {
  const source =
    options.root ||
    (options.selector
      ? document.querySelector(options.selector)
      : null) ||
    findPrintRoot(event?.currentTarget ?? null);
  if (!source) {
    window.print();
    return;
  }

  // Default landscape; advice letters stay portrait. Override via options.orientation.
  let orientation = "landscape";
  if (options.orientation === "portrait" || options.orientation === "landscape") {
    orientation = options.orientation;
  } else if (
    source.classList?.contains("fp-advice-print") ||
    source.classList?.contains("fp-lic-bill-print") ||
    source.querySelector?.(".fp-advice-print__page") ||
    source.querySelector?.(".fp-lic-bill-print__page")
  ) {
    orientation = "portrait";
  }
  applyPageOrientation(orientation);

  const portal = ensurePrintPortal();
  portal.replaceChildren(clonePrintRoot(source));

  document.documentElement.classList.add(PENSION_REPORT_PRINT_CLASS);

  const cleanup = () => {
    document.documentElement.classList.remove(PENSION_REPORT_PRINT_CLASS);
    portal.replaceChildren();
    clearPageOrientation();
    window.removeEventListener("afterprint", cleanup);
  };

  window.addEventListener("afterprint", cleanup);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      window.print();
    });
  });
}
