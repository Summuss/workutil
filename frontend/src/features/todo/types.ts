export interface Todo {
  id: number;
  title: string;
  order: number;
  due_date: string | null;
  source_memo_id: number | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

export type MoveDirection = "up" | "down" | "top" | "bottom";

export interface TodoListResponse {
  todos: Todo[];
  completed: Todo[];
}

export interface TodoCreatePayload {
  title: string;
  due_date?: string | null;
  source_memo_id?: number | null;
}

export interface TodoUpdatePayload {
  title?: string;
  due_date?: string | null;
}
