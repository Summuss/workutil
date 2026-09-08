export interface Todo {
  id: number;
  title: string;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
}

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
