const storageKey = (tripId: string) => `yeogimalgo.guidebookMade.${tripId}`

export function markGuidebookMade(tripId: string) {
  try {
    localStorage.setItem(storageKey(tripId), "1")
  } catch {
    // private mode / quota
  }
}

export function isGuidebookMade(tripId: string) {
  try {
    return localStorage.getItem(storageKey(tripId)) === "1"
  } catch {
    return false
  }
}
