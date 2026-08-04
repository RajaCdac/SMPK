import { useLayoutEffect, useRef } from "react";
import DataTable from "datatables.net-bs5";
import "datatables.net-responsive-bs5";
import "datatables.net-bs5/css/dataTables.bootstrap5.min.css";
import "datatables.net-responsive-bs5/css/responsive.bootstrap5.min.css";
import "./SmpkDataTable.css";

const DEFAULT_LANGUAGE = {
  search: "Search:",
  lengthMenu: "Show _MENU_ entries",
  info: "Showing _START_ to _END_ of _TOTAL_ entries",
  infoEmpty: "Showing 0 entries",
  emptyTable: "No data available",
  paginate: {
    first: "First",
    last: "Last",
    next: "Next",
    previous: "Previous",
  },
};

const DEFAULT_OPTIONS = {
  responsive: true,
  pageLength: 25,
  lengthMenu: [10, 25, 50, 100, -1],
  order: [],
  autoWidth: false,
  language: DEFAULT_LANGUAGE,
};

function mergeDataTableOptions(options = {}) {
  return {
    ...DEFAULT_OPTIONS,
    ...options,
    language: {
      ...DEFAULT_LANGUAGE,
      ...options.language,
      paginate: {
        ...DEFAULT_LANGUAGE.paginate,
        ...options.language?.paginate,
      },
    },
  };
}

/**
 * Inner instance: mounts once per `tableKey` (remounted by the parent's React key).
 *
 * A fresh <table> DOM node is created on every data change, so React never has to
 * diff a node that DataTables has already restructured (wrapped, paginated, reordered).
 * DataTables is initialized/destroyed in useLayoutEffect so destroy() runs synchronously
 * before React removes the node on remount — preventing "removeChild" errors.
 */
function DataTableInstance({ children, className, options }) {
  const tableRef = useRef(null);
  const dtRef = useRef(null);

  useLayoutEffect(() => {
    const el = tableRef.current;
    if (!el) return undefined;

    dtRef.current = new DataTable(el, mergeDataTableOptions(options));

    return () => {
      if (dtRef.current) {
        try {
          dtRef.current.destroy();
        } catch {
          /* table node may already be gone */
        }
        dtRef.current = null;
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <table ref={tableRef} className={className}>
      {children}
    </table>
  );
}

/**
 * Bootstrap 5 DataTable wrapper.
 * - Pass `tableKey` and change it whenever row data changes so the grid remounts.
 * - Pass `ready={false}` while async data is loading to skip an empty first init.
 */
export default function SmpkDataTable({
  children,
  tableKey = "default",
  ready = true,
  options = {},
  className = "table table-striped table-hover table-bordered w-100 smpk-datatable",
}) {
  if (!ready) {
    return (
      <div className="smpk-datatable-wrap smpk-datatable-loading text-muted py-3">
        Loading…
      </div>
    );
  }

  return (
    <div className="smpk-datatable-wrap">
      <DataTableInstance
        key={tableKey}
        className={className}
        options={options}
      >
        {children}
      </DataTableInstance>
    </div>
  );
}
