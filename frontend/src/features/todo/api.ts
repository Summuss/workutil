import { del, get, patch, post } from "../../shared/api";
import type {
  MoveDirection,
  Todo,
  TodoCreatePayload,
  TodoListResponse,
  TodoUpdatePayload,
} from "./types";

export function listTodos(): Promise<TodoListResponse> {
  return get<TodoListResponse>("/todos");
}

export function createTodo(payload: TodoCreatePayload): Promise<Todo> {
  return post<Todo>("/todos", payload);
}

export function updateTodo(
  id: number,
  payload: TodoUpdatePayload,
): Promise<Todo> {
  return patch<Todo>(`/todos/${id}`, payload);
}

export function deleteTodo(id: number): Promise<void> {
  return del(`/todos/${id}`);
}

export function completeTodo(id: number): Promise<Todo> {
  return post<Todo>(`/todos/${id}/complete`);
}

export function reopenTodo(id: number): Promise<Todo> {
  return post<Todo>(`/todos/${id}/reopen`);
}

export function moveTodo(id: number, to: MoveDirection): Promise<Todo[]> {
  return post<Todo[]>(`/todos/${id}/move`, { to });
}
