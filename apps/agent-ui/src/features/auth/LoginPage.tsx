import * as React from "react";
import { useNavigate } from "@tanstack/react-router";

import { ApiError } from "@/shared/http";

import { useAuth } from "./AuthProvider";

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof TypeError) return "无法连接服务器，请确认服务已启动";
  return "登录失败，请稍后重试";
}

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();

  const [username, setUsername] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [submitting, setSubmitting] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (submitting) return;

    const name = username.trim();
    if (!name) {
      setError("请输入用户名");
      return;
    }
    if (!password) {
      setError("请输入密码");
      return;
    }

    setSubmitting(true);
    setError(null);
    try {
      await login(name, password);
      void navigate({ to: "/", replace: true });
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page" data-testid="login-page">
      <form className="login-card" onSubmit={handleSubmit}>
        <div className="login-brand">
          <span className="brand-dot" />
          <span>苏格拉底式学习助手</span>
        </div>
        <p className="login-subtitle">登录后继续你的计算机网络学习</p>

        <label className="login-field" htmlFor="username">
          <span>用户名</span>
          <input
            id="username"
            name="username"
            autoComplete="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            disabled={submitting}
            data-testid="login-username"
            autoFocus
          />
        </label>

        <label className="login-field" htmlFor="password">
          <span>密码</span>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={submitting}
            data-testid="login-password"
          />
        </label>

        {error !== null && (
          <p className="login-error" role="alert" data-testid="login-error">
            {error}
          </p>
        )}

        <button
          type="submit"
          className="login-submit"
          disabled={submitting}
          data-testid="login-submit"
        >
          {submitting ? "登录中…" : "登录"}
        </button>

        <p className="login-hint">账号由老师分配，忘记密码请联系老师。</p>
      </form>
    </div>
  );
}
