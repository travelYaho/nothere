/** Date -> "YYYY-MM-DD". toISOString()은 UTC 기준이라 로컬 날짜가 하루 밀릴 수 있어 직접 조합한다. */
export function toDateOnlyString(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}
