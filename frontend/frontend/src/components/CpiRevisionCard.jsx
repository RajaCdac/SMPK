import { formatCardValue } from "../utils/methodology2RevisionCards";

export default function CpiRevisionCard({ title, rows }) {
  if (!rows?.length) return null;

  return (
    <div className="col-12 col-sm-6 col-lg-3">
      <div className="card h-100 shadow-sm border-0 revision-cpi-card">
        <div className="card-header bg-warning text-dark py-2">
          <h6 className="mb-0 fw-bold text-center">{title}</h6>
        </div>
        <div className="card-body p-0">
          <table className="table table-sm table-bordered mb-0">
            <tbody>
              {rows.map((line) => (
                <tr key={line.row}>
                  <td
                    className="small fw-bold text-center"
                    style={{ width: "32px" }}
                  >
                    {line.code || ""}
                  </td>
                  <td className="small text-muted" style={{ width: "58%" }}>
                    {line.description}
                  </td>
                  <td className="small fw-semibold text-end">
                    {formatCardValue(line.value)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
