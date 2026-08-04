import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import API from "../services/Api";
import PensionCalculationSheet from "../components/PensionCalculationSheet";
import "../styles/PensionPrint.css";

export default function PensionCalculationPrint() {
  const { id } = useParams();
  const [data, setData] = useState(null);

  useEffect(() => {
    API.get(`first-pension/report/${id}/`)
      .then((res) => setData(res.data))
      .catch((err) => console.error(err));
  }, [id]);

  const handlePrint = () => window.print();

  if (!data) {
    return <div className="loading-text">Loading...</div>;
  }

  return (
    <div className="print-page">
      <div className="no-print">
        <button type="button" onClick={handlePrint}>
          Print Report
        </button>
      </div>
      <PensionCalculationSheet data={data} />
    </div>
  );
}
