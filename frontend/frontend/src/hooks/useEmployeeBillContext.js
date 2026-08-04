import { useCallback, useEffect, useState } from "react";
import API from "../services/Api";

export function useEmployeeBillContext(employee) {
  const [billContext, setBillContext] = useState(null);
  const [loading, setLoading] = useState(false);

  const reload = useCallback(async ({ showLoading = false } = {}) => {
    if (!employee?.emp_id) {
      setBillContext(null);
      return;
    }

    if (showLoading) {
      setLoading(true);
    }
    try {
      const statusRes = await API.get(
        `first-pension/pension-bill/status/employee/${employee.emp_id}/`
      );
      const status = statusRes.data;
      let voucherNo = "";

      if (status?.bill_no) {
        try {
          const voucherRes = await API.get(
            "first-pension/pension-bill/voucher/status/",
            { params: { bill_no: status.bill_no } }
          );
          voucherNo = voucherRes.data?.voucher_no || "";
        } catch (error) {
          console.error(error);
        }
      }

      setBillContext({
        status,
        billNo: status?.bill_no || "",
        jvMonth: status?.pension_month ? String(status.pension_month) : "",
        jvYear: status?.pension_yr ? String(status.pension_yr) : "",
        voucherNo,
      });
    } catch (error) {
      console.error(error);
      setBillContext(null);
    } finally {
      if (showLoading) {
        setLoading(false);
      }
    }
  }, [employee?.emp_id]);

  useEffect(() => {
    reload({ showLoading: true });
  }, [reload]);

  return { billContext, loading, reload };
}
