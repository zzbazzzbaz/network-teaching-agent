import type {
  ToolCallMessagePartComponent,
  ToolCallMessagePartProps,
} from "@assistant-ui/react";

function pretty(value: unknown): string {
  if (value === undefined) return "";
  if (typeof value === "string") return value;
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function statusLabel(status: ToolCallMessagePartProps["status"]): string {
  if (status.type === "running") return "运行中";
  if (status.type === "complete") return "完成";
  return "失败";
}

export const ToolCallCard: ToolCallMessagePartComponent = ({
  toolName,
  args,
  result,
  status,
  isError,
}) => {
  if (toolName === "ask_student") {
    return (
      <div className="tool-pending" data-testid="tool-ask-student-pending">
        {status.type === "running" ? "等待学生作答…" : "学生已作答"}
      </div>
    );
  }

  return (
    <details
      className={`tool-card${isError ? " tool-card-error" : ""}`}
      data-testid="tool-call"
    >
      <summary>
        <span className="tool-name">{toolName}</span>
        <span className={`tool-status tool-status-${status.type}`}>
          {isError ? "失败" : statusLabel(status)}
        </span>
      </summary>
      <div className="tool-section">
        <div className="tool-label">参数</div>
        <pre>{pretty(args)}</pre>
      </div>
      {result !== undefined && (
        <div className="tool-section">
          <div className="tool-label">结果</div>
          <pre>{pretty(result)}</pre>
        </div>
      )}
    </details>
  );
};
