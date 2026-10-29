import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { MeetingFormDialog } from "@/components/MeetingFormDialog"
import * as auth from "@/lib/auth"
import type { SavedAgenda } from "@/types"
import { mockFetch, renderWithQuery, sampleMeeting } from "@/test/utils"
const START = new Date(2026, 8, 28, 10)

async function setup(failFirstSave = false) {
  vi.stubEnv("VITE_AGENDA_PARSER_URL", "https://parser.example")
  vi.spyOn(auth, "getIdToken").mockResolvedValue("test-token")
  const suggestion = {
    agenda: {
      title: "Suggested meeting",
      starts_at: null,
      duration_minutes: 45,
      language: "uk",
      items: [
        { topic: "Plan", owner: "Олена", minutes: 15 },
        { topic: "Feedback", owner: "Taras", minutes: null },
        { topic: "Discount", owner: null, minutes: null },
      ],
      action_items: [{ task: "Compare prices", owner: "Taras", due: "2026-11-06" }],
    },
    model: "us.amazon.nova-micro-v1:0",
    prompt_version: "agenda-v1",
  }
  let saves = 0
  let stored: SavedAgenda | null = null
  const fetch = mockFetch((url, init) => {
    if (url === "https://parser.example") return { body: suggestion }
    if (url.endsWith("/agenda") && init?.method === "POST") {
      if (failFirstSave && ++saves === 1) return { status: 503 }
      stored = JSON.parse(String(init.body))
      return { body: stored }
    }
    if (url.endsWith("/agenda")) return { body: stored }
    if (init?.method === "POST" || init?.method === "PUT") return { body: sampleMeeting }
    return { body: [] }
  })
  const onClose = vi.fn()
  const view = renderWithQuery(
    <MeetingFormDialog open onOpenChange={onClose} initialStart={START} />,
  )
  await userEvent.click(screen.getByRole("button", { name: "Paste agenda / AI parser" }))
  await userEvent.type(screen.getByLabelText("Paste an agenda"), "Planning notes")
  await userEvent.click(screen.getByRole("button", { name: "Parse with AI" }))
  const title = await screen.findByDisplayValue("Suggested meeting")
  await userEvent.clear(title)
  await userEvent.type(title, "Reviewed meeting")
  await userEvent.click(screen.getByRole("button", { name: "Use reviewed agenda" }))
  expect(screen.getByLabelText("Title")).toHaveValue("Reviewed meeting")
  expect(fetch.mock.calls.some(([url]) => String(url).includes("/agenda"))).toBe(false)
  expect(
    fetch.mock.calls.some(
      ([url, init]) => String(url) === "/api/meetings" && init?.method === "POST",
    ),
  ).toBe(false)
  await userEvent.type(screen.getByLabelText("Place"), "Room 1")
  return { fetch, onClose, suggestion, view }
}

describe("New meeting agenda", () => {
  it("reviews before creation and preserves the original suggestion on explicit save", async () => {
    const { fetch, onClose, suggestion } = await setup()
    await userEvent.click(screen.getByRole("button", { name: "Paste agenda / AI parser" }))
    expect(screen.getByLabelText("Agenda title")).toHaveValue("Reviewed meeting")
    await userEvent.click(screen.getByRole("button", { name: "Use reviewed agenda" }))
    await userEvent.click(screen.getByRole("button", { name: "Create meeting" }))
    await waitFor(() => expect(onClose).toHaveBeenCalledWith(false))
    const save = fetch.mock.calls.find(
      ([url, init]) => String(url).endsWith("/agenda") && init?.method === "POST",
    )
    expect(JSON.parse(String(save?.[1]?.body))).toMatchObject({
      final_agenda: { title: "Reviewed meeting" },
      ai_suggestion: suggestion,
    })
  })
  it("reopens all saved reviewed topics and deadlines through the existing meeting editor", async () => {
    const { fetch, onClose, view } = await setup()
    await userEvent.click(screen.getByRole("button", { name: "Create meeting" }))
    await waitFor(() => expect(onClose).toHaveBeenCalledWith(false))
    view.unmount()
    renderWithQuery(<MeetingFormDialog open meeting={sampleMeeting} onOpenChange={() => {}} />)
    await userEvent.click(screen.getByRole("button", { name: "View agenda" }))
    expect(await screen.findByText("Reviewed meeting")).toBeInTheDocument()
    for (const topic of ["Plan", "Feedback", "Discount", "Compare prices"])
      expect(screen.getByText(topic)).toBeInTheDocument()
    expect(screen.getByText("Owner: Олена · Duration: 15 minutes")).toBeInTheDocument()
    expect(screen.getByText("Owner: Taras · Due: 2026-11-06")).toBeInTheDocument()
    expect(fetch.mock.calls.filter(([url]) => url === "https://parser.example")).toHaveLength(1)
    expect(
      fetch.mock.calls.filter(
        ([url, init]) => String(url).endsWith("/agenda") && init?.method === "POST",
      ),
    ).toHaveLength(1)
  })
  it("retries a failed agenda save without creating a duplicate meeting", async () => {
    const { fetch, onClose } = await setup(true)
    await userEvent.click(screen.getByRole("button", { name: "Create meeting" }))
    expect(await screen.findByRole("alert")).toHaveTextContent("without creating a duplicate")
    expect(onClose).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole("button", { name: "Create meeting" }))
    await waitFor(() => expect(onClose).toHaveBeenCalledWith(false))
    expect(
      fetch.mock.calls.filter(
        ([url, init]) => String(url) === "/api/meetings" && init?.method === "POST",
      ),
    ).toHaveLength(1)
  })
  it("cancels parsing UI and preserves a manual meeting draft without writes", async () => {
    const fetch = mockFetch(() => ({ body: [] }))
    renderWithQuery(<MeetingFormDialog open onOpenChange={() => {}} initialStart={START} />)
    await userEvent.type(screen.getByLabelText("Title"), "Manual draft")
    await userEvent.click(screen.getByRole("button", { name: "Paste agenda / AI parser" }))
    await userEvent.keyboard("{Escape}")
    expect(await screen.findByLabelText("Title")).toHaveValue("Manual draft")
    expect(fetch.mock.calls.some(([, init]) => init?.method === "POST")).toBe(false)
  })
})
