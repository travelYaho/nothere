/** Date -> "YYYY-MM-DD". toISOString()은 UTC 기준이라 로컬 날짜가 하루 밀릴 수 있어 직접 조합한다. */
export function toDateOnlyString(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, "0")
  const day = String(date.getDate()).padStart(2, "0")
  return `${year}-${month}-${day}`
}

const WEEKDAY_FULL_LABELS = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
]

const MONTH_FULL_LABELS = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
]

export function formatTimetableDate(travelDate: string) {
  const d = new Date(`${travelDate}T00:00:00`)
  return {
    monthLabel: MONTH_FULL_LABELS[d.getMonth()],
    dayPadded: String(d.getDate()).padStart(2, "0"),
    weekdayLabel: WEEKDAY_FULL_LABELS[d.getDay()],
  }
}
