import { useCallback, useEffect, useMemo, useState } from "react";
import API from "../services/Api";
import "../styles/FirstPensionCase.css";
import "../styles/NomineeEntry.css";

const EMPTY_FORM = {
  nomin_type: "PN",
  nominee_name: "",
  relation_cd: "",
  share_pct: "",
  birth_dt: "",
  marital_status: "M",
  employed_flg: "0",
  handicap_flg: "0",
  bank_cd: "",
  bank_branch: "",
  bank_ac_no: "",
  addr1: "",
  addr2: "",
  ps: "",
  city: "",
  dist: "",
  state: "",
  pin: "",
  country: "INDIA",
  contact1: "",
  email_id: "",
};

export default function NomineeEntry() {
  const [empCode, setEmpCode] = useState("");
  const [employee, setEmployee] = useState(null);
  const [nominees, setNominees] = useState([]);
  const [shareTotals, setShareTotals] = useState({});
  const [typeChoices, setTypeChoices] = useState([
    { value: "PN", label: "Pension" },
    { value: "GR", label: "Gratuity" },
  ]);
  const [relations, setRelations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);

  useEffect(() => {
    API.get("family-pension/relations/")
      .then((res) => setRelations(res.data?.results || []))
      .catch(() => setRelations([]));
  }, []);

  const loadNominee = useCallback(async (rawCode) => {
    const code = String(rawCode || "").trim();
    if (!code) {
      setError("Please enter Employee code");
      return;
    }
    setLoading(true);
    setError("");
    setMessage("");
    setShowAdd(false);
    try {
      const res = await API.get("family-pension/nominee/", {
        params: { emp_cd: code },
      });
      setEmployee(res.data.employee || null);
      setNominees(res.data.nominees || []);
      setShareTotals(res.data.share_totals || {});
      if (res.data.nomin_type_choices?.length) {
        setTypeChoices(res.data.nomin_type_choices);
      }
      setEmpCode(res.data.employee?.emp_cd || code);
      setMessage(
        res.data.nominees?.length
          ? `${res.data.nominees.length} nominee record(s) found`
          : "No nominees on record — use Add Nominee"
      );
    } catch (err) {
      setEmployee(null);
      setNominees([]);
      setShareTotals({});
      setError(
        err.response?.data?.error || err.message || "Could not load nominees"
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const onSearch = (e) => {
    e?.preventDefault?.();
    loadNominee(empCode);
  };

  const openAdd = () => {
    setForm({ ...EMPTY_FORM });
    setShowAdd(true);
    setError("");
    setMessage("");
  };

  const setField = (key, value) => {
    setForm((prev) => {
      const next = { ...prev, [key]: value };
      if (key === "bank_cd") {
        next.bank_branch = "";
      }
      return next;
    });
  };

  const resolveBank = async () => {
    const code = String(form.bank_cd || "").trim();
    if (!code) {
      setForm((prev) => ({ ...prev, bank_branch: "" }));
      return;
    }
    try {
      const { data } = await API.get("family-pension/bank-lookup/", {
        params: { bank_cd: code },
      });
      if (data?.found) {
        const branch = data.bank_branch || "";
        const name = data.bank_name || "";
        const label =
          name && branch && name !== branch
            ? `${name} — ${branch}`
            : branch || name || "";
        setForm((prev) => ({ ...prev, bank_branch: label }));
        setError((prev) =>
          prev && prev.startsWith("Bank code") ? "" : prev
        );
      } else {
        setForm((prev) => ({ ...prev, bank_branch: "" }));
        setError(`Bank code ${code} not found`);
      }
    } catch {
      setForm((prev) => ({ ...prev, bank_branch: "" }));
    }
  };

  const remainingShare = useMemo(() => {
    const used = Number(shareTotals[form.nomin_type] || 0);
    return Math.max(0, Math.round((100 - used) * 100) / 100);
  }, [shareTotals, form.nomin_type]);

  const saveNominee = async (e) => {
    e?.preventDefault?.();
    if (!employee?.emp_cd) {
      setError("Search employee first");
      return;
    }
    setSaving(true);
    setError("");
    setMessage("");
    try {
      const res = await API.post("family-pension/nominee/", {
        emp_cd: employee.emp_cd,
        ...form,
        share_pct: form.share_pct === "" ? null : form.share_pct,
        relation_cd: form.relation_cd === "" ? null : form.relation_cd,
      });
      setNominees(res.data.nominees || []);
      setShowAdd(false);
      setMessage(res.data.message || "Nominee saved");
      // refresh share totals
      await loadNominee(employee.emp_cd);
      setMessage(res.data.message || "Nominee saved");
    } catch (err) {
      setError(
        err.response?.data?.error || err.message || "Could not save nominee"
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="first-pension-page nominee-page">
      <header className="nominee-page__header">
        <h1>Nominee</h1>
        <p className="text-muted mb-0">
          Employee nominee master (Oracle FI_XX_MD_NOMIN_PN_E / fi_xx_md_nominee)
          — pension, gratuity and related nominee shares for die-in-harness and
          other cases.
        </p>
      </header>

      <section className="card first-pension-search-card mb-3">
        <div className="card-body">
          <form className="nominee-search-row" onSubmit={onSearch}>
            <label className="nominee-search-row__field">
              Employee code
              <input
                type="text"
                className="form-control"
                value={empCode}
                onChange={(e) => setEmpCode(e.target.value)}
                placeholder="e.g. 44377"
                maxLength={5}
                disabled={loading}
              />
            </label>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
            >
              {loading ? "Searching…" : "Search"}
            </button>
          </form>
        </div>
      </section>

      {error ? <div className="alert alert-danger py-2">{error}</div> : null}
      {message ? <div className="alert alert-info py-2">{message}</div> : null}

      {employee ? (
        <>
          <div className="first-pension-employee-bar">
            <div>
              <strong>
                {employee.emp_cd} — {employee.emp_name || "—"}
              </strong>
              {Object.keys(shareTotals).length > 0 ? (
                <div className="small text-muted mt-1">
                  Share used:{" "}
                  {Object.entries(shareTotals)
                    .map(([t, v]) => `${t} ${v}%`)
                    .join(" · ")}
                </div>
              ) : null}
            </div>
            <button type="button" className="btn btn-success" onClick={openAdd}>
              + Add nominee
            </button>
          </div>

          <section className="card mb-3">
            <div className="card-header py-2">Nominee details</div>
            <div className="card-body p-0 table-responsive">
              <table className="table table-sm table-hover mb-0 nominee-table">
                <thead className="table-light">
                  <tr>
                    <th>Type</th>
                    <th>Sl</th>
                    <th>Name</th>
                    <th>Relation</th>
                    <th className="text-end">Share %</th>
                    <th>Bank</th>
                    <th>A/c No</th>
                    <th>Contact</th>
                  </tr>
                </thead>
                <tbody>
                  {!nominees.length ? (
                    <tr>
                      <td colSpan={8} className="text-center text-muted py-4">
                        No nominee rows for this employee.
                      </td>
                    </tr>
                  ) : (
                    nominees.map((n) => (
                      <tr key={`${n.nomin_type}-${n.sl_no}`}>
                        <td>
                          {n.nomin_type_label || n.nomin_type}
                          <span className="text-muted"> ({n.nomin_type})</span>
                        </td>
                        <td>{n.sl_no}</td>
                        <td>{n.nominee_name}</td>
                        <td>
                          {n.relation_desc || n.relation_cd || "—"}
                        </td>
                        <td className="text-end">
                          {n.share_pct != null ? n.share_pct : "—"}
                        </td>
                        <td>
                          {n.bank_cd
                            ? `${n.bank_cd}${n.bank_desc ? ` — ${n.bank_desc}` : ""}`
                            : "—"}
                        </td>
                        <td>{n.bank_ac_no || "—"}</td>
                        <td>{n.contact1 || "—"}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>

          {showAdd ? (
            <section className="card mb-3 nominee-add-card">
              <div className="card-header py-2 d-flex justify-content-between align-items-center">
                <span>Add nominee</span>
                <button
                  type="button"
                  className="btn btn-sm btn-outline-secondary"
                  onClick={() => setShowAdd(false)}
                >
                  Cancel
                </button>
              </div>
              <div className="card-body">
                <form onSubmit={saveNominee}>
                  <div className="row g-2">
                    <div className="col-md-3">
                      <label className="form-label">
                        Nominee type <span className="text-danger">*</span>
                      </label>
                      <select
                        className="form-select"
                        value={form.nomin_type}
                        onChange={(e) => setField("nomin_type", e.target.value)}
                        required
                      >
                        {typeChoices.map((t) => (
                          <option key={t.value} value={t.value}>
                            {t.label} ({t.value})
                          </option>
                        ))}
                      </select>
                      <div className="form-text">
                        Remaining for type: {remainingShare}%
                      </div>
                    </div>
                    <div className="col-md-3">
                      <label className="form-label">
                        Nominee name <span className="text-danger">*</span>
                      </label>
                      <input
                        className="form-control"
                        value={form.nominee_name}
                        onChange={(e) => setField("nominee_name", e.target.value)}
                        maxLength={50}
                        required
                      />
                    </div>
                    <div className="col-md-3">
                      <label className="form-label">
                        Relationship <span className="text-danger">*</span>
                      </label>
                      <select
                        className="form-select"
                        value={form.relation_cd}
                        onChange={(e) => setField("relation_cd", e.target.value)}
                        required
                      >
                        <option value="">Select…</option>
                        {relations.map((r) => (
                          <option
                            key={r.relation_cd ?? r.RELATION_CD}
                            value={r.relation_cd ?? r.RELATION_CD}
                          >
                            {r.relation_desc ||
                              r.RELATION_DESC ||
                              r.relation_cd ||
                              r.RELATION_CD}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="col-md-3">
                      <label className="form-label">
                        Share % <span className="text-danger">*</span>
                      </label>
                      <input
                        type="number"
                        className="form-control"
                        min={0.01}
                        max={100}
                        step={0.01}
                        value={form.share_pct}
                        onChange={(e) => setField("share_pct", e.target.value)}
                        required
                      />
                    </div>
                    <div className="col-md-2">
                      <label className="form-label">Birth date</label>
                      <input
                        type="date"
                        className="form-control"
                        value={form.birth_dt}
                        onChange={(e) => setField("birth_dt", e.target.value)}
                      />
                    </div>
                    <div className="col-md-2">
                      <label className="form-label">Marital</label>
                      <select
                        className="form-select"
                        value={form.marital_status}
                        onChange={(e) =>
                          setField("marital_status", e.target.value)
                        }
                      >
                        <option value="M">Married</option>
                        <option value="U">Unmarried</option>
                        <option value="W">Widow(er)</option>
                        <option value="D">Divorced</option>
                      </select>
                    </div>
                    <div className="col-md-2 d-flex flex-column justify-content-end pb-1">
                      <div className="form-check">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id="nominee-employed"
                          checked={
                            form.employed_flg === "1" ||
                            form.employed_flg === 1 ||
                            form.employed_flg === true
                          }
                          onChange={(e) =>
                            setField(
                              "employed_flg",
                              e.target.checked ? "1" : "0"
                            )
                          }
                        />
                        <label
                          className="form-check-label"
                          htmlFor="nominee-employed"
                        >
                          Employed
                        </label>
                      </div>
                      <div className="form-check">
                        <input
                          className="form-check-input"
                          type="checkbox"
                          id="nominee-handicap"
                          checked={
                            form.handicap_flg === "1" ||
                            form.handicap_flg === 1 ||
                            form.handicap_flg === true
                          }
                          onChange={(e) =>
                            setField(
                              "handicap_flg",
                              e.target.checked ? "1" : "0"
                            )
                          }
                        />
                        <label
                          className="form-check-label"
                          htmlFor="nominee-handicap"
                        >
                          Handicapped
                        </label>
                      </div>
                    </div>
                    <div className="w-100" />
                    <div className="col-md-2">
                      <label className="form-label">Bank code</label>
                      <input
                        className="form-control"
                        value={form.bank_cd}
                        onChange={(e) => setField("bank_cd", e.target.value)}
                        onBlur={resolveBank}
                        maxLength={6}
                      />
                    </div>
                    <div className="col-md-6">
                      <label className="form-label">Bank / branch name</label>
                      <input
                        className="form-control"
                        value={form.bank_branch}
                        readOnly
                        tabIndex={-1}
                        title={form.bank_branch || ""}
                        placeholder="Fill bank code, then leave field"
                      />
                    </div>
                    <div className="col-md-4">
                      <label className="form-label">Bank A/c no</label>
                      <input
                        className="form-control"
                        value={form.bank_ac_no}
                        onChange={(e) => setField("bank_ac_no", e.target.value)}
                        maxLength={15}
                      />
                    </div>
                    <div className="col-md-4">
                      <label className="form-label">Address line 1</label>
                      <input
                        className="form-control"
                        value={form.addr1}
                        onChange={(e) => setField("addr1", e.target.value)}
                        maxLength={25}
                      />
                    </div>
                    <div className="col-md-4">
                      <label className="form-label">Address line 2</label>
                      <input
                        className="form-control"
                        value={form.addr2}
                        onChange={(e) => setField("addr2", e.target.value)}
                        maxLength={25}
                      />
                    </div>
                    <div className="col-md-3">
                      <label className="form-label">Police station</label>
                      <input
                        className="form-control"
                        value={form.ps}
                        onChange={(e) => setField("ps", e.target.value)}
                        maxLength={30}
                      />
                    </div>
                    <div className="col-md-3">
                      <label className="form-label">City</label>
                      <input
                        className="form-control"
                        value={form.city}
                        onChange={(e) => setField("city", e.target.value)}
                        maxLength={20}
                      />
                    </div>
                    <div className="col-md-3">
                      <label className="form-label">District</label>
                      <input
                        className="form-control"
                        value={form.dist}
                        onChange={(e) => setField("dist", e.target.value)}
                        maxLength={20}
                      />
                    </div>
                    <div className="col-md-3">
                      <label className="form-label">State</label>
                      <input
                        className="form-control"
                        value={form.state}
                        onChange={(e) => setField("state", e.target.value)}
                        maxLength={20}
                      />
                    </div>
                    <div className="col-md-2">
                      <label className="form-label">PIN</label>
                      <input
                        className="form-control"
                        value={form.pin}
                        onChange={(e) => setField("pin", e.target.value)}
                      />
                    </div>
                    <div className="col-md-3">
                      <label className="form-label">Country</label>
                      <input
                        className="form-control"
                        value={form.country}
                        onChange={(e) => setField("country", e.target.value)}
                        maxLength={20}
                        placeholder="INDIA"
                      />
                      <div className="form-text">Default INDIA; change if needed</div>
                    </div>
                    <div className="col-md-3">
                      <label className="form-label">Contact</label>
                      <input
                        className="form-control"
                        value={form.contact1}
                        onChange={(e) => setField("contact1", e.target.value)}
                        maxLength={15}
                      />
                    </div>
                    <div className="col-md-3">
                      <label className="form-label">Email</label>
                      <input
                        type="email"
                        className="form-control"
                        value={form.email_id}
                        onChange={(e) => setField("email_id", e.target.value)}
                        maxLength={30}
                      />
                    </div>
                  </div>                  <div className="mt-3 d-flex gap-2">
                    <button
                      type="submit"
                      className="btn btn-primary"
                      disabled={saving}
                    >
                      {saving ? "Saving…" : "Save nominee"}
                    </button>
                    <button
                      type="button"
                      className="btn btn-outline-secondary"
                      onClick={() => setShowAdd(false)}
                      disabled={saving}
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            </section>
          ) : null}
        </>
      ) : null}
    </div>
  );
}
