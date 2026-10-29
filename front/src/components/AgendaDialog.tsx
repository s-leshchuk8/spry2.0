import { useEffect, useRef, useState } from "react"
import { useFieldArray, useForm } from "react-hook-form"
import type { FieldPath } from "react-hook-form"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/lib/api"
import { agendaSchema, parseAgenda } from "@/lib/agenda"
import type { AISuggestion, Meeting, ParsedAgenda, SavedAgenda } from "@/types"

type Values = {
  title: string
  starts_at: string
  duration_minutes: string
  language: string
  items: { topic: string; owner: string; minutes: string }[]
  action_items: { task: string; owner: string; due: string }[]
}
const empty: Values = {
  title: "",
  starts_at: "",
  duration_minutes: "",
  language: "",
  items: [],
  action_items: [],
}
const nullable = (s: string) => (s === "" ? null : s)
const number = (s: string) => (s === "" ? null : Number(s))
function values(a: ParsedAgenda): Values {
  return {
    title: a.title ?? "",
    starts_at: a.starts_at ?? "",
    duration_minutes: String(a.duration_minutes ?? ""),
    language: a.language,
    items: a.items.map((i) => ({
      topic: i.topic,
      owner: i.owner ?? "",
      minutes: String(i.minutes ?? ""),
    })),
    action_items: a.action_items.map((i) => ({
      task: i.task,
      owner: i.owner ?? "",
      due: i.due ?? "",
    })),
  }
}

type AgendaDialogProps = { onClose: () => void; initialDraft?: SavedAgenda } & (
  | { meeting: Meeting; onConfirm?: never }
  | { meeting?: undefined; onConfirm: (draft: SavedAgenda) => void }
)

export function AgendaDialog({ meeting, onClose, onConfirm, initialDraft }: AgendaDialogProps) {
  const queryClient = useQueryClient()
  const [text, setText] = useState("")
  const [parsing, setParsing] = useState(false)
  const [error, setError] = useState("")
  const [suggestion, setSuggestion] = useState<AISuggestion | null | undefined>(
    initialDraft?.ai_suggestion,
  )
  const [marked, setMarked] = useState<Set<string>>(new Set())
  const abort = useRef<AbortController | null>(null)
  const form = useForm<Values>({
    defaultValues: initialDraft ? values(initialDraft.final_agenda) : empty,
  })
  const items = useFieldArray({ control: form.control, name: "items" })
  const actions = useFieldArray({ control: form.control, name: "action_items" })
  const saved = useQuery({
    queryKey: ["agenda", meeting?.id ?? "draft"],
    queryFn: () => api.getAgenda(meeting!.id),
    enabled: Boolean(meeting),
    retry: false,
  })
  const save = useMutation({
    mutationFn: (data: Parameters<typeof api.saveAgenda>[1]) => api.saveAgenda(meeting!.id, data),
  })
  useEffect(() => {
    if (saved.data) {
      form.reset(values(saved.data.final_agenda))
    }
  }, [saved.data, form])
  useEffect(() => () => abort.current?.abort(), [])
  const cancel = () => {
    abort.current?.abort()
    abort.current = null
    setParsing(false)
  }
  const run = async () => {
    cancel()
    const controller = new AbortController()
    abort.current = controller
    setParsing(true)
    setError("")
    try {
      const result = await parseAgenda(text, controller.signal)
      if (controller.signal.aborted) return
      setSuggestion(structuredClone(result))
      const next = values(result.agenda)
      form.reset(next)
      const paths = new Set<string>()
      for (const key of ["title", "starts_at", "duration_minutes", "language"] as const)
        if (next[key] !== "") paths.add(key)
      for (const key of ["items", "action_items"] as const)
        next[key].forEach((row, i) => {
          Object.entries(row).forEach(([field, value]) => {
            if (value !== "") paths.add(`${key}.${i}.${field}`)
          })
        })
      setMarked(paths)
    } catch (e) {
      if (!controller.signal.aborted)
        setError(
          e instanceof TypeError
            ? "Network error. Check your connection and try again"
            : e instanceof Error
              ? e.message
              : "Parsing failed",
        )
    } finally {
      if (abort.current === controller) {
        abort.current = null
        setParsing(false)
      }
    }
  }
  const removeMarks = (group: "items" | "action_items", index: number) => {
    setMarked(
      (old) =>
        new Set(
          [...old].flatMap((path) => {
            if (!path.startsWith(`${group}.`)) return [path]
            const [, row, fieldName] = path.split(".")
            const current = Number(row)
            if (current === index) return []
            return [`${group}.${current > index ? current - 1 : current}.${fieldName}`]
          }),
        ),
    )
  }
  const field = (name: FieldPath<Values>, label: string, type = "text") => (
    <label className="grid gap-1 text-sm" key={name}>
      <span>
        {label}{" "}
        {marked.has(name) && <span className="rounded bg-secondary px-1 text-xs">suggested</span>}
      </span>
      <Input
        type={type}
        {...form.register(name, {
          onChange: () =>
            setMarked((old) => {
              const next = new Set(old)
              next.delete(name)
              return next
            }),
        })}
      />
    </label>
  )
  const submit = form.handleSubmit(async (v) => {
    setError("")
    const parsed = agendaSchema.safeParse({
      title: nullable(v.title),
      starts_at: nullable(v.starts_at),
      duration_minutes: number(v.duration_minutes),
      language: v.language,
      items: v.items.map((i) => ({
        topic: i.topic,
        owner: nullable(i.owner),
        minutes: number(i.minutes),
      })),
      action_items: v.action_items.map((i) => ({
        task: i.task,
        owner: nullable(i.owner),
        due: nullable(i.due),
      })),
    })
    if (!parsed.success) {
      setError(parsed.error.issues.map((i) => `${i.path.join(".")}: ${i.message}`).join("; "))
      return
    }
    if (
      parsed.data.starts_at &&
      (!/[zZ]|[+-]\d{2}:\d{2}$/.test(parsed.data.starts_at) ||
        Number.isNaN(Date.parse(parsed.data.starts_at)))
    ) {
      setError("Start must be an ISO 8601 date and time including its UTC offset")
      return
    }
    try {
      const draft = {
        final_agenda: parsed.data,
        ai_suggestion: suggestion === undefined ? (saved.data?.ai_suggestion ?? null) : suggestion,
      }
      if (!meeting) {
        onConfirm(draft)
        return
      }
      await save.mutateAsync(draft)
      await queryClient.invalidateQueries({ queryKey: ["agenda", meeting?.id ?? "draft"] })
      toast.success("Agenda saved")
      onClose()
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save agenda")
    }
  })
  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) {
          cancel()
          onClose()
        }
      }}
    >
      <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            {meeting ? `Agenda for ${meeting.title}` : "Paste agenda / AI parser"}
          </DialogTitle>
          <DialogDescription>
            Paste text for suggestions, or enter an agenda manually. Review every field before
            saving.
          </DialogDescription>
        </DialogHeader>
        {(suggestion?.model ?? saved.data?.ai_suggestion?.model) === "mock" && (
          <p role="status">MOCK suggestion — no model was called. Review every field.</p>
        )}
        {meeting && saved.isPending ? (
          <p role="status">Loading agenda…</p>
        ) : meeting && saved.isError ? (
          <p role="alert">
            Could not load the saved agenda. <Button onClick={() => saved.refetch()}>Retry</Button>
          </p>
        ) : (
          <>
            <label className="grid gap-1">
              Paste an agenda
              <Textarea value={text} onChange={(e) => setText(e.target.value)} rows={4} />
            </label>
            <div className="flex gap-2">
              <Button onClick={run} disabled={parsing || save.isPending || !text.trim()}>
                Parse with AI
              </Button>
              {parsing && (
                <>
                  <p role="status">Parsing agenda…</p>
                  <Button variant="outline" onClick={cancel}>
                    Cancel parsing
                  </Button>
                </>
              )}
            </div>
            <form onSubmit={submit} className="space-y-3">
              <fieldset disabled={parsing || save.isPending} className="space-y-3">
                {field("title", "Agenda title")}
                {field("starts_at", "Start (ISO 8601 with offset)")}
                <div className="grid grid-cols-2 gap-3">
                  {field("duration_minutes", "Duration (minutes)", "number")}
                  {field("language", "Language")}
                </div>
                <h3>Agenda items</h3>
                {items.fields.map((item, i) => (
                  <div key={item.id} className="space-y-2 rounded border p-2">
                    {field(`items.${i}.topic`, "Topic")}
                    {field(`items.${i}.owner`, "Topic owner")}
                    {field(`items.${i}.minutes`, "Minutes", "number")}
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        items.remove(i)
                        removeMarks("items", i)
                      }}
                    >
                      Remove topic
                    </Button>
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => items.append({ topic: "", owner: "", minutes: "" })}
                >
                  Add topic
                </Button>
                <h3>Action items</h3>
                {actions.fields.map((item, i) => (
                  <div key={item.id} className="space-y-2 rounded border p-2">
                    {field(`action_items.${i}.task`, "Task")}
                    {field(`action_items.${i}.owner`, "Action owner")}
                    {field(`action_items.${i}.due`, "Due", "date")}
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        actions.remove(i)
                        removeMarks("action_items", i)
                      }}
                    >
                      Remove action
                    </Button>
                  </div>
                ))}
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => actions.append({ task: "", owner: "", due: "" })}
                >
                  Add action
                </Button>
                <p className="text-sm text-muted-foreground">
                  {meeting
                    ? "Agenda metadata is saved with this agenda; it does not change the meeting schedule."
                    : "Review this draft, then confirm the meeting details. Nothing is saved until you click Create meeting."}
                </p>
                <Button type="submit">
                  {save.isPending ? "Saving…" : meeting ? "Save agenda" : "Use reviewed agenda"}
                </Button>
              </fieldset>
            </form>
          </>
        )}
        {error && (
          <p role="alert" className="text-destructive">
            {error}
          </p>
        )}
      </DialogContent>
    </Dialog>
  )
}
