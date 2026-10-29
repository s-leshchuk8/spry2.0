import { useState } from "react"
import { useQuery } from "@tanstack/react-query"

import { Button } from "@/components/ui/button"
import { api } from "@/lib/api"

/** Read-only access to the reviewed agenda; opening it never invokes AI or saves anything. */
export function SavedAgendaSection({ meetingId }: { meetingId: string }) {
  const [expanded, setExpanded] = useState(false)
  const saved = useQuery({
    queryKey: ["agenda", meetingId],
    queryFn: () => api.getAgenda(meetingId),
    enabled: expanded,
    retry: false,
  })
  const agenda = saved.data?.final_agenda

  return (
    <section aria-label="Saved agenda" className="space-y-3 rounded border bg-muted/30 p-3">
      <Button
        type="button"
        variant="outline"
        aria-expanded={expanded}
        onClick={() => setExpanded((value) => !value)}
      >
        {expanded ? "Hide agenda" : "View agenda"}
      </Button>
      {expanded &&
        (saved.isPending ? (
          <p role="status">Loading saved agenda…</p>
        ) : saved.isError ? (
          <div role="alert">
            Could not load the saved agenda.
            <Button type="button" variant="outline" onClick={() => saved.refetch()}>
              Retry
            </Button>
          </div>
        ) : !agenda ? (
          <p className="text-sm text-muted-foreground">
            No agenda has been saved for this meeting.
          </p>
        ) : (
          <div className="space-y-3 text-sm">
            <h3 className="font-semibold">{agenda.title ?? "Saved agenda"}</h3>
            <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
              <dt>Start</dt>
              <dd>{agenda.starts_at ?? "Not specified"}</dd>
              <dt>Duration</dt>
              <dd>
                {agenda.duration_minutes === null
                  ? "Not specified"
                  : `${agenda.duration_minutes} minutes`}
              </dd>
              <dt>Language</dt>
              <dd>{agenda.language}</dd>
            </dl>
            <h4 className="font-semibold">Topics</h4>
            {agenda.items.length === 0 ? (
              <p>No topics saved.</p>
            ) : (
              <ol className="list-decimal space-y-2 pl-5">
                {agenda.items.map((item, index) => (
                  <li key={index}>
                    <p className="whitespace-pre-wrap">{item.topic}</p>
                    <p className="text-muted-foreground">
                      Owner: {item.owner ?? "Not assigned"} · Duration:{" "}
                      {item.minutes === null ? "Not specified" : `${item.minutes} minutes`}
                    </p>
                  </li>
                ))}
              </ol>
            )}
            <h4 className="font-semibold">Action items</h4>
            {agenda.action_items.length === 0 ? (
              <p>No action items saved.</p>
            ) : (
              <ul className="list-disc space-y-2 pl-5">
                {agenda.action_items.map((item, index) => (
                  <li key={index}>
                    <p className="whitespace-pre-wrap">{item.task}</p>
                    <p className="text-muted-foreground">
                      Owner: {item.owner ?? "Not assigned"} · Due: {item.due ?? "Not specified"}
                    </p>
                  </li>
                ))}
              </ul>
            )}
            <p className="text-muted-foreground">
              This is the saved, reviewed agenda. Editing meeting details does not change it.
            </p>
          </div>
        ))}
    </section>
  )
}
