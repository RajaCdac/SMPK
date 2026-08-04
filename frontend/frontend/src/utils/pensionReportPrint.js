/** Shared landscape print hook for all pension bill / report printouts. */
export const PENSION_REPORT_PRINT_CLASS = "pension-report-printing";
export const PRINT_PORTAL_ID = "pension-print-portal";

const PRINT_ROOT_SELECTOR =
  ".lic-report-print, .bill-abstract-print, .proposal-sanction-print, .fp-proposal-print, .fp-advice-print, .comm-sanction-print, .sepcom-bill-print, .journal-summary-print";

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

export function printPensionReport(event) {
  const source = findPrintRoot(event?.currentTarget ?? null);
  if (!source) {
    window.print();
    return;
  }

  const portal = ensurePrintPortal();
  portal.replaceChildren(clonePrintRoot(source));

  document.documentElement.classList.add(PENSION_REPORT_PRINT_CLASS);

  const cleanup = () => {
    document.documentElement.classList.remove(PENSION_REPORT_PRINT_CLASS);
    portal.replaceChildren();
    window.removeEventListener("afterprint", cleanup);
  };

  window.addEventListener("afterprint", cleanup);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      window.print();
    });
  });
}
