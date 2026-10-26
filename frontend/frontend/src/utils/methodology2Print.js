/** Print Methodology 2 consolidation via a body-level portal (avoids blank pages). */

export const M2_PRINT_CLASS = "m2-consol-printing";
export const M2_PRINT_PORTAL_ID = "m2-print-portal";
export const M2_PRINT_SOURCE_ID = "methodology2-consolidation-print";
const M2_PRINT_PAGE_STYLE_ID = "m2-print-page-style";

/** Chrome uses the last @page rule in the document. Other reports set landscape. */
function applyPortraitPage() {
  let el = document.getElementById(M2_PRINT_PAGE_STYLE_ID);
  if (!el) {
    el = document.createElement("style");
    el.id = M2_PRINT_PAGE_STYLE_ID;
    document.head.appendChild(el);
  }
  el.textContent = "@page { size: A4 portrait; margin: 3mm 12mm; }";
}

function clearPortraitPage() {
  document.getElementById(M2_PRINT_PAGE_STYLE_ID)?.remove();
}

function ensurePrintPortal() {
  let portal = document.getElementById(M2_PRINT_PORTAL_ID);
  if (!portal) {
    portal = document.createElement("div");
    portal.id = M2_PRINT_PORTAL_ID;
    portal.className = "m2-print-portal";
    document.body.appendChild(portal);
  }
  return portal;
}

/** Case no. used as the Save-as-PDF name (browser appends .pdf). */
function pdfBaseName(name) {
  let text = String(name || "").trim();
  if (!text || text === "—" || text === "-") return "";
  text = text.replace(/[<>:"/\\|?*]+/g, "-");
  text = text.replace(/\s+/g, "_").replace(/^\.+|\.+$/g, "");
  return text.slice(0, 80);
}

/** Case NO printed on the sheet, when the caller did not pass one. */
function caseNoFromSheet(source) {
  const text = source?.querySelector?.(".m2-consol-print__case-no")?.textContent;
  return pdfBaseName(text);
}

/**
 * Clone the off-screen consolidation sheet to a direct child of <body>,
 * then open the browser print dialog. Parent display:none cannot blank the clone.
 * fileName is the suggested PDF name (case number, e.g. 35925 → 35925.pdf).
 */
export function printMethodology2Consolidation(fileName) {
  const previousTitle = document.title;
  const source = document.getElementById(M2_PRINT_SOURCE_ID);
  const base = pdfBaseName(fileName) || caseNoFromSheet(source);

  const applyTitle = () => {
    if (base) document.title = base;
  };
  const restoreTitle = () => {
    document.title = previousTitle;
  };

  applyTitle();
  window.addEventListener("beforeprint", applyTitle);
  applyPortraitPage();

  if (!source) {
    window.addEventListener(
      "afterprint",
      () => {
        window.removeEventListener("beforeprint", applyTitle);
        clearPortraitPage();
        restoreTitle();
      },
      { once: true },
    );
    window.print();
    return;
  }

  const portal = ensurePrintPortal();
  const clone = source.cloneNode(true);
  clone.id = `${M2_PRINT_SOURCE_ID}-clone`;
  clone.classList.add("m2-consol-print-wrap");
  portal.replaceChildren(clone);

  document.documentElement.classList.add(M2_PRINT_CLASS);

  const cleanup = () => {
    document.documentElement.classList.remove(M2_PRINT_CLASS);
    portal.replaceChildren();
    window.removeEventListener("beforeprint", applyTitle);
    clearPortraitPage();
    restoreTitle();
    window.removeEventListener("afterprint", cleanup);
  };

  window.addEventListener("afterprint", cleanup);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      window.print();
    });
  });
}
