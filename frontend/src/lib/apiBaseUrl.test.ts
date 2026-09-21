import { resolveApiBaseUrl } from "./apiBaseUrl"

describe("resolveApiBaseUrl", () => {
  it("uses same-origin in the Vite dev server", () => {
    expect(resolveApiBaseUrl({ DEV: true, VITE_API_BASE_URL: "http://localhost:8000" })).toBe("")
  })

  it("uses VITE_API_BASE_URL in production builds", () => {
    expect(
      resolveApiBaseUrl({ DEV: false, VITE_API_BASE_URL: "https://yeogimalgo-backend.onrender.com/" }),
    ).toBe("https://yeogimalgo-backend.onrender.com")
  })

  it("falls back to localhost when the production env is empty", () => {
    expect(resolveApiBaseUrl({ DEV: false, VITE_API_BASE_URL: "" })).toBe("http://localhost:8000")
  })
})
