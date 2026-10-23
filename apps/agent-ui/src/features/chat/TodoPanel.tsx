import { useChatStream } from "./chat-stream-context";

type TodoStatus = "pending" | "in_progress" | "completed" | string;

type Todo = {
  content: string;
  status: TodoStatus;
};

function statusMark(status: TodoStatus): string {
  if (status === "completed") return "✓";
  if (status === "in_progress") return "◐";
  return "○";
}

export function TodoPanel() {
  const stream = useChatStream();
  const todos = (stream.values as { todos?: Todo[] }).todos;

  if (!Array.isArray(todos) || todos.length === 0) return null;

  const done = todos.filter((todo) => todo.status === "completed").length;

  return (
    <aside className="todos" data-testid="todo-panel">
      <div className="todos-header">
        <span>计划</span>
        <span className="todos-count">
          {done}/{todos.length}
        </span>
      </div>
      <ul className="todos-list">
        {todos.map((todo, index) => (
          <li
            key={`${index}-${todo.content}`}
            className={`todo todo-${todo.status}`}
            data-testid="todo-item"
          >
            <span className="todo-mark">{statusMark(todo.status)}</span>
            <span>{todo.content}</span>
          </li>
        ))}
      </ul>
    </aside>
  );
}
