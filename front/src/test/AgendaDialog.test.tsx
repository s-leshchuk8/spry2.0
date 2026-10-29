import { fireEvent, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { afterEach, describe, expect, it, vi } from "vitest"

import { AgendaDialog } from "@/components/AgendaDialog"
import * as auth from "@/lib/auth"
import { localDate } from "@/lib/agenda"
import { mockFetch, renderWithQuery, sampleMeeting } from "@/test/utils"

const suggestion = {
  agenda: {
    title: "Original",
    starts_at: null,
    duration_minutes: 45,
    language: "uk",
    items: [{ topic: "Нові тарифи Pro", owner: "Олена", minutes: 15 }],
    action_items: [{ task: "Compare prices", owner: "Taras", due: null }],
  },
  model: "anthropic.claude-opus-5-5",
  prompt_version: "agenda-v1",
}
function setup(status = 200, parsedSuggestion = suggestion) {
  vi.stubEnv("VITE_AGENDA_PARSER_URL", "https://parser.example")
  vi.spyOn(auth, "getIdToken").mockResolvedValue("test-token")
  const fetch = mockFetch((url, init) => {
    if (url === "https://parser.example") return { status, body: parsedSuggestion }
    return { body: init?.method === "POST" ? JSON.parse(String(init.body)) : null }
  })
  const onClose = vi.fn()
  renderWithQuery(<AgendaDialog meeting={sampleMeeting} onClose={onClose} />)
  return { fetch, onClose }
}
afterEach(() => vi.unstubAllEnvs())

describe("Agenda review", () => {
  it("parses, marks, edits and saves with the unchanged original suggestion", async () => {
    const { fetch, onClose } = setup()
    await userEvent.type(await screen.findByLabelText("Paste an agenda"), "Pricing — Олена")
    await userEvent.click(screen.getByRole("button", { name: "Parse with AI" }))
    const title = await screen.findByDisplayValue("Original")
    expect(screen.getAllByText("suggested").length).toBeGreaterThan(0)
    expect(screen.getByLabelText("Start (ISO 8601 with offset)")).toHaveValue("")
    await userEvent.clear(title)
    await userEvent.type(title, "Corrected")
    expect(screen.getByLabelText("Agenda title").parentElement).not.toHaveTextContent("suggested")
    expect(fetch.mock.calls.filter(([, init]) => init?.method === "POST")).toHaveLength(1)
    await userEvent.click(screen.getByRole("button", { name: "Save agenda" }))
    await waitFor(() => expect(onClose).toHaveBeenCalled())
    const save = fetch.mock.calls.find(
      ([url, init]) => String(url).includes("/agenda") && init?.method === "POST",
    )
    const body = JSON.parse(String(save?.[1]?.body))
    expect(body.final_agenda.title).toBe("Corrected")
    expect(body.ai_suggestion).toEqual(suggestion)
    const parse = fetch.mock.calls.find(([url]) => url === "https://parser.example")
    expect(parse?.[1]?.headers).toMatchObject({ Authorization: "Bearer test-token" })
    expect(JSON.parse(String(parse?.[1]?.body))).toMatchObject({
      today: localDate(),
      tz: expect.any(String),
    })
  })

  it("keeps a visible warning for local mock suggestions", async () => {
    setup(200, { ...suggestion, model: "mock" })
    await userEvent.type(await screen.findByLabelText("Paste an agenda"), "text")
    await userEvent.click(screen.getByRole("button", { name: "Parse with AI" }))
    expect(await screen.findByText(/MOCK suggestion — no model was called/)).toBeInTheDocument()
    await userEvent.clear(screen.getByLabelText(/Agenda title/))
    expect(screen.getByText(/MOCK suggestion — no model was called/)).toBeInTheDocument()
  })

  it("supports manual entry when parsing is unavailable", async () => {
    const { fetch } = setup(503)
    await userEvent.type(await screen.findByLabelText("Paste an agenda"), "text")
    await userEvent.click(screen.getByRole("button", { name: "Parse with AI" }))
    expect(await screen.findByRole("alert")).toHaveTextContent("unavailable")
    await userEvent.click(screen.getByRole("button", { name: "Add topic" }))
    await userEvent.type(screen.getByLabelText("Topic"), "Manual topic")
    await userEvent.click(screen.getByRole("button", { name: "Save agenda" }))
    await waitFor(() =>
      expect(
        fetch.mock.calls.some(
          ([url, init]) => String(url).includes("/agenda") && init?.method === "POST",
        ),
      ).toBe(true),
    )
    const save = fetch.mock.calls.find(
      ([url, init]) => String(url).includes("/agenda") && init?.method === "POST",
    )
    expect(JSON.parse(String(save?.[1]?.body)).ai_suggestion).toBeNull()
  })

  it("cancels the request and ignores a late response", async () => {
    const { fetch: fetchMock } = setup()
    const original = fetchMock.getMockImplementation()!
    let signal: AbortSignal | undefined
    let complete: ((value: Response) => void) | undefined
    fetchMock.mockImplementation((input, init) => {
      if (String(input) !== "https://parser.example") return original(input, init)
      signal = init?.signal ?? undefined
      return new Promise((resolve) => {
        complete = resolve
      })
    })
    await userEvent.type(await screen.findByLabelText("Paste an agenda"), "text")
    await userEvent.click(screen.getByRole("button", { name: "Parse with AI" }))
    expect(await screen.findByRole("status")).toHaveTextContent("Parsing")
    await userEvent.click(screen.getByRole("button", { name: "Cancel parsing" }))
    expect(signal?.aborted).toBe(true)
    complete?.(new Response(JSON.stringify(suggestion)))
    await waitFor(() => expect(screen.getByLabelText("Agenda title")).toHaveValue(""))
  })

  it("rejects long text before fetching and explains network failure", async () => {
    const { fetch: fetchMock } = setup()
    const textarea = await screen.findByLabelText("Paste an agenda")
    fireEvent.change(textarea, { target: { value: "x".repeat(10001) } })
    await userEvent.click(screen.getByRole("button", { name: "Parse with AI" }))
    expect(await screen.findByRole("alert")).toHaveTextContent("10,000")
    expect(fetchMock.mock.calls.some(([url]) => String(url) === "https://parser.example")).toBe(
      false,
    )
    const original = fetchMock.getMockImplementation()!
    fetchMock.mockImplementation((input, init) =>
      String(input) === "https://parser.example"
        ? Promise.reject(new TypeError("failed to fetch"))
        : original(input, init),
    )
    fireEvent.change(textarea, { target: { value: "text" } })
    await userEvent.click(screen.getByRole("button", { name: "Parse with AI" }))
    expect(await screen.findByRole("alert")).toHaveTextContent("Network error")
  })

  it("allows manual persistence after a 429 without automatically retrying the model", async () => {
    const { fetch, onClose } = setup(429)
    await userEvent.type(await screen.findByLabelText("Paste an agenda"), "Valid meeting notes")
    await userEvent.click(screen.getByRole("button", { name: "Parse with AI" }))
    expect(await screen.findByRole("alert")).toHaveTextContent("busy")
    expect(
      fetch.mock.calls.filter(([url]) => String(url) === "https://parser.example"),
    ).toHaveLength(1)
    await userEvent.click(screen.getByRole("button", { name: "Add topic" }))
    await userEvent.type(screen.getByLabelText("Topic"), "Manual fallback")
    await userEvent.click(screen.getByRole("button", { name: "Save agenda" }))
    await waitFor(() => expect(onClose).toHaveBeenCalled())
    const save = fetch.mock.calls.find(
      ([url, init]) => String(url).endsWith("/agenda") && init?.method === "POST",
    )
    expect(JSON.parse(String(save?.[1]?.body)).ai_suggestion).toBeNull()
    expect(
      fetch.mock.calls.filter(([url]) => String(url) === "https://parser.example"),
    ).toHaveLength(1)
  })

  it.each([
    [401, "session has expired"],
    [413, "10,000"],
    [422, "valid agenda"],
    [429, "busy"],
  ])("explains HTTP %s", async (status, message) => {
    setup(Number(status))
    await userEvent.type(await screen.findByLabelText("Paste an agenda"), "text")
    await userEvent.click(screen.getByRole("button", { name: "Parse with AI" }))
    expect(await screen.findByRole("alert")).toHaveTextContent(String(message))
  })
})
