import { createRootRoute, Outlet, redirect } from "@tanstack/react-router";

import { getSession } from "@/shared/session";

export const Route = createRootRoute({
  beforeLoad: ({ location }) => {
    const loggedIn = getSession() !== null;
    if (!loggedIn && location.pathname !== "/login") {
      throw redirect({ to: "/login" });
    }
    if (loggedIn && location.pathname === "/login") {
      throw redirect({ to: "/" });
    }
  },
  component: () => <Outlet />,
});
