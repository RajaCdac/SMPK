/** Shared bank code autocomplete helpers (FI_PM_MH_BANK). */

export function bankDisplayName(bank) {
  return bank?.bank_desc || bank?.bank_name || "";
}

export function resolveBankFromMaster(bankMaster, rawValue) {
  const value = String(rawValue || "").trim().toUpperCase();
  if (!value) return { bank_cd: "", bank_name: "" };

  const exact = bankMaster.find((b) => b.bank_cd === value);
  if (exact) {
    return {
      bank_cd: exact.bank_cd,
      bank_name: bankDisplayName(exact),
    };
  }

  const codePart = value.split("—")[0].split("-")[0].trim();
  const fromLabel = bankMaster.find((b) => b.bank_cd === codePart);
  if (fromLabel) {
    return {
      bank_cd: fromLabel.bank_cd,
      bank_name: bankDisplayName(fromLabel),
    };
  }

  return { bank_cd: value, bank_name: "" };
}

export async function lookupBankByCode(api, bankMaster, rawCode) {
  const code = String(rawCode || "").trim();
  if (!code) return { bank_cd: "", bank_name: "" };

  const local = resolveBankFromMaster(bankMaster, code);
  if (local.bank_name) return local;

  try {
    const res = await api.get(
      `first-pension/banks/${encodeURIComponent(code)}/`
    );
    const bank = res.data;
    if (bank?.bank_cd) {
      return {
        bank_cd: bank.bank_cd,
        bank_name: bankDisplayName(bank),
      };
    }
  } catch {
    // not found
  }
  return { bank_cd: code.toUpperCase(), bank_name: "" };
}
