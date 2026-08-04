/** Print Methodology 2 consolidation via a body-level portal (avoids blank pages). */

export const M2_PRINT_CLASS = "m2-consol-printing";
export const M2_PRINT_PORTAL_ID = "m2-print-portal";
export const M2_PRINT_SOURCE_ID = "methodology2-consolidation-print";

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

/**
 * Clone the off-screen consolidation sheet to a direct child of <body>,
 * then print. Parent display:none cannot blank the clone.
 */
export function printMethodology2Consolidation() {
  const source = document.getElementById(M2_PRINT_SOURCE_ID);
  if (!source) {
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
    window.removeEventListener("afterprint", cleanup);
  };

  window.addEventListener("afterprint", cleanup);

  requestAnimationFrame(() => {
    requestAnimationFrame(() => {
      window.print();
    });
  });
}
