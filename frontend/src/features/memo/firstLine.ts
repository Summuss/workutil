/**
 * The line a memo shows in the list.
 *
 * A memo has no title — being made to name one is friction, and that is the
 * whole point of the tool (CONTEXT.md). So the list cuts a line off the body
 * at display time instead; nothing here is stored.
 */
export function firstLine(body: string): string {
  return body.split("\n").find((line) => line.trim() !== "")?.trim() ?? "";
}
