export type DueDateStatus = "overdue" | "today" | "future" | "none";

export function getDueDateStatus(
  dueDate: string | null,
  referenceDate: Date = new Date(),
): DueDateStatus {
  if (!dueDate) return "none";
  const year = referenceDate.getFullYear();
  const month = String(referenceDate.getMonth() + 1).padStart(2, "0");
  const day = String(referenceDate.getDate()).padStart(2, "0");
  const todayStr = `${year}-${month}-${day}`;

  if (dueDate < todayStr) return "overdue";
  if (dueDate === todayStr) return "today";
  return "future";
}
