export interface Todo {
  id: number;
  title: string;
  order: number;
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
}

export interface TodoUpdatePayload {
  title?: string;
}
