import { z } from "zod"
import { getIdToken } from "@/lib/auth"
import type { AISuggestion } from "@/types"

export const agendaSchema = z.object({
  title: z.string().nullable(),
  starts_at: z.string().nullable(),
  duration_minutes: z.number().int().min(1).max(600).nullable(),
  items: z.array(
    z.object({
      topic: z.string().min(1),
      owner: z.string().nullable(),
      minutes: z.number().int().min(1).max(480).nullable(),
    }),
  ),
  action_items: z.array(
    z.object({
      task: z.string().min(1),
      owner: z.string().nullable(),
      due: z.iso.date().nullable(),
    }),
  ),
  language: z.string(),
})
const suggestionSchema = z.object({
  agenda: agendaSchema,
  model: z.string().min(1),
  prompt_version: z.string().min(1),
})

export function localDate(now = new Date()): string {
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`
}

export async function parseAgenda(text: string, signal: AbortSignal): Promise<AISuggestion> {
  if (!text.trim()) throw new Error("Paste some agenda text first")
  if (Array.from(text).length > 10_000) throw new Error("Paste at most 10,000 characters")
  const url = import.meta.env.VITE_AGENDA_PARSER_URL
  if (!url) throw new Error("Agenda parsing is not configured. Enter the agenda manually")
  const token = await getIdToken()
  if (!token) throw new Error("Sign in to parse an agenda")
  const res = await fetch(url, {
    method: "POST",
    signal,
    headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
    body: JSON.stringify({
      text,
      today: localDate(),
      tz: Intl.DateTimeFormat().resolvedOptions().timeZone,
    }),
  })
  const errors: Record<number, string> = {
    401: "Your session has expired. Sign in again",
    413: "Paste at most 10,000 characters",
    422: "The model could not find a valid agenda. Edit the text or enter it manually",
    429: "The parsing service is busy. Try again shortly",
    502: "The model could not parse this text. Try again or enter it manually",
    503: "The parsing service is unavailable. Enter the agenda manually",
  }
  if (!res.ok) throw new Error(errors[res.status] ?? `Parsing failed (${res.status})`)
  const result = suggestionSchema.safeParse(await res.json())
  if (!result.success)
    throw new Error(
      "The parsing service returned an invalid agenda. Try again or enter it manually",
    )
  return result.data
}
