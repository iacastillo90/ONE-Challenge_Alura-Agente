import { describe, it, expect } from "vitest"
import { render, screen } from "@testing-library/react"
import { MemoryRouter } from "react-router-dom"
import App from "../App"

describe("App", () => {
  it("renders login page at /login", () => {
    render(
      <MemoryRouter initialEntries={["/login"]}>
        <App />
      </MemoryRouter>,
    )
    expect(screen.getByText(/iniciar sesión/i)).toBeInTheDocument()
  })

  it("renders 404 for unknown routes", () => {
    render(
      <MemoryRouter initialEntries={["/nonexistent"]}>
        <App />
      </MemoryRouter>,
    )
    expect(screen.getByText(/404/i)).toBeInTheDocument()
  })
})
