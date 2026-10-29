import { screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"

import { MeetingFormDialog } from "@/components/MeetingFormDialog"
import { mockFetch, renderWithQuery, sampleMeeting } from "@/test/utils"

const agenda = {
  title: "Reviewed pricing sync",
  starts_at: "2026-11-02T10:00:00+02:00",
  duration_minutes: 45,
  language: "uk",
  items: [
    { topic: "Нові тарифи Pro", owner: "Олена", minutes: 15 },
    { topic: "Фідбек клієнтів", owner: "Taras", minutes: null },
    { topic: "Річна знижка", owner: null, minutes: null },
  ],
  action_items: [{ task: "Compare competitors", owner: "Taras", due: "2026-11-06" }],
}

function editMeeting() {
  return renderWithQuery(<MeetingFormDialog open meeting={sampleMeeting} onOpenChange={vi.fn()} />)
}

describe("Saved agenda in Edit meeting", () => {
  it("fetches on demand and displays every reviewed topic and action without parsing or writing", async () => {
    const fetch = mockFetch((url) => ({
      body: url.endsWith("/agenda") ? { final_agenda: agenda, ai_suggestion: null } : [],
    }))
    editMeeting()
    expect(fetch.mock.calls.some(([url]) => String(url).endsWith("/agenda"))).toBe(false)
    const title = screen.getByLabelText("Title")
    await userEvent.clear(title)
    await userEvent.type(title, "Unsaved meeting edit")
    await userEvent.click(screen.getByRole("button", { name: "View agenda" }))
    expect(await screen.findByText("Reviewed pricing sync")).toBeInTheDocument()
    for (const topic of agenda.items) expect(screen.getByText(topic.topic)).toBeInTheDocument()
    expect(screen.getByText("Owner: Олена · Duration: 15 minutes")).toBeInTheDocument()
    expect(screen.getByText("Owner: Taras · Duration: Not specified")).toBeInTheDocument()
    expect(screen.getByText("Owner: Not assigned · Duration: Not specified")).toBeInTheDocument()
    expect(screen.getByText("Compare competitors")).toBeInTheDocument()
    expect(screen.getByText("Owner: Taras · Due: 2026-11-06")).toBeInTheDocument()
    expect(screen.getByText(agenda.starts_at)).toBeInTheDocument()
    expect(screen.getByText("45 minutes")).toBeInTheDocument()
    expect(screen.getByLabelText("Title")).toHaveValue("Unsaved meeting edit")
    await userEvent.click(screen.getByRole("button", { name: "Hide agenda" }))
    expect(screen.queryByText("Compare competitors")).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole("button", { name: "View agenda" }))
    expect(await screen.findByText("Compare competitors")).toBeInTheDocument()
    expect(fetch.mock.calls.some(([, init]) => ["POST", "PUT"].includes(init?.method ?? ""))).toBe(
      false,
    )
    expect(fetch.mock.calls.every(([url]) => !String(url).includes("parser"))).toBe(true)
  })

  it("handles meetings without an agenda without changing the meeting editor", async () => {
    mockFetch((url) => ({ body: url.endsWith("/agenda") ? null : [] }))
    editMeeting()
    await userEvent.click(screen.getByRole("button", { name: "View agenda" }))
    expect(
      await screen.findByText("No agenda has been saved for this meeting."),
    ).toBeInTheDocument()
    expect(screen.getByLabelText("Title")).toHaveValue(sampleMeeting.title)
    expect(screen.getByRole("button", { name: "Save changes" })).toBeEnabled()
  })

  it("distinguishes a failed read from an absent agenda and retries only explicitly", async () => {
    let fail = true
    const fetch = mockFetch((url) =>
      url.endsWith("/agenda")
        ? fail
          ? { status: 503 }
          : { body: { final_agenda: { ...agenda, items: [], action_items: [] } } }
        : { body: [] },
    )
    editMeeting()
    await userEvent.click(screen.getByRole("button", { name: "View agenda" }))
    expect(await screen.findByRole("alert")).toHaveTextContent("Could not load the saved agenda")
    expect(screen.queryByText("No agenda has been saved for this meeting.")).not.toBeInTheDocument()
    expect(fetch.mock.calls.filter(([url]) => String(url).endsWith("/agenda"))).toHaveLength(1)
    fail = false
    await userEvent.click(screen.getByRole("button", { name: "Retry" }))
    await waitFor(() => expect(screen.getByText("No topics saved.")).toBeInTheDocument())
    expect(screen.getByText("No action items saved.")).toBeInTheDocument()
  })
})
