export function groupIndianDigits(intDigits: string): string {
  if (intDigits.length <= 3) return intDigits;
  const last3 = intDigits.slice(-3);
  const rest = intDigits.slice(0, -3);
  return `${rest.replace(/\B(?=(\d{2})+(?!\d))/g, ',')},${last3}`;
}

export function formatIndianCurrencyInput(raw: string): string {
  let cleaned = raw.replace(/[^\d.]/g, '');
  const dotIndex = cleaned.indexOf('.');
  if (dotIndex !== -1) {
    cleaned = cleaned.slice(0, dotIndex + 1) + cleaned.slice(dotIndex + 1).replace(/\./g, '');
  }
  const [intRaw, decRaw = ''] = cleaned.split('.');
  const intDigits = intRaw.replace(/^0+(?=\d)/, '');
  const grouped = groupIndianDigits(intDigits);
  if (cleaned.includes('.')) return decRaw ? `${grouped}.${decRaw}` : `${grouped}.`;
  return grouped;
}

export function parseIndianCurrencyInput(value: string): number | null {
  const cleaned = value.replace(/[^\d.]/g, '');
  if (cleaned === '' || cleaned === '.') return null;
  const num = Number(cleaned);
  return Number.isFinite(num) ? num : null;
}
