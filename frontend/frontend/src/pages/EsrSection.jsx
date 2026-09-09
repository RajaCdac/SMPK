/**
 * ESR (Employee Service Record) section placeholders.
 * Areas map to Oracle masters: Personal / Admin / Finance.
 */
const SECTION_COPY = {
  personal: {
    title: "ESR — Personal",
    note: "Personal details entry (fi_xx_mh_emp_per) — module coming next.",
  },
  admin: {
    title: "ESR — Admin",
    note: "Administrative details entry (fi_xx_mh_emp_adm) — module coming next.",
  },
  finance: {
    title: "ESR — Finance",
    note: "Finance / pay details entry (fi_xx_mh_emp_fin) — module coming next.",
  },
};

export default function EsrSection({ section = "personal" }) {
  const meta = SECTION_COPY[section] || SECTION_COPY.personal;

  return (
    <div className="container-fluid mt-3 mt-md-4 px-2 px-md-3">
      <div className="row justify-content-center">
        <div className="col-12 col-xl-11">
          <div className="card shadow">
            <div className="card-header bg-primary text-white">
              <h4 className="mb-0">{meta.title}</h4>
            </div>
            <div className="card-body">
              <p className="mb-0 text-muted">{meta.note}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
