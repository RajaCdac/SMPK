export default function MethodologyClass12Result({ category, class12Result }) {
  if (!class12Result) return null;

  return (
    <div className="row justify-content-center mt-4">
      <div className="col-12 col-xl-10">
        <div className="card shadow">
          <div className="card-header bg-secondary text-white d-flex justify-content-between align-items-center">
            <h5 className="mb-0">
              Category {category} Revision —{" "}
              {class12Result.scale_display || class12Result.grade} (start{" "}
              {class12Result.start_revision})
            </h5>
          </div>
          <div className="card-body">
            <table className="table table-striped table-bordered mb-3">
              <thead>
                <tr>
                  <th>Particulars</th>
                  <th className="text-end">Amount</th>
                </tr>
              </thead>
              <tbody>
                {(class12Result.rows || []).map((row, idx) => (
                  <tr key={idx}>
                    <td>{row.description}</td>
                    <td className="text-end">
                      {Number(row.value).toLocaleString("en-IN", {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 2,
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div className="row g-3">
              <div className="col-12 col-md-4">
                <div className="border rounded p-3 text-center">
                  <div className="text-muted small">Basic Pay (2017)</div>
                  <div className="fs-5 fw-bold">
                    {Number(class12Result.basic_pay_2017).toLocaleString("en-IN")}
                  </div>
                </div>
              </div>
              <div className="col-12 col-md-4">
                <div className="border rounded p-3 text-center">
                  <div className="text-muted small">Pension (50%)</div>
                  <div className="fs-5 fw-bold">
                    {Number(class12Result.pension).toLocaleString("en-IN")}
                  </div>
                </div>
              </div>
              <div className="col-12 col-md-4">
                <div className="border rounded p-3 text-center">
                  <div className="text-muted small">Family Pension (30%)</div>
                  <div className="fs-5 fw-bold">
                    {Number(class12Result.family_pension).toLocaleString("en-IN")}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
