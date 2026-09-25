import { useCallback, useEffect, useState, type ReactNode } from "react";
import {
  fetchMe,
  getToken,
  login as apiLogin,
  register as apiRegister,
  setToken,
  type User,
} from "./api";
import { AuthContext } from "./auth-context";

export function AuthProvider({ children }: { children: ReactNode }) {
  // no token means nothing to check — the app is usable immediately
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(() => !getToken());

  useEffect(() => {
    if (!getToken()) return;
    let alive = true;
    fetchMe()
      .then((me) => {
        if (alive) setUser(me);
      })
      .catch(() => setToken(null))
      .finally(() => {
        if (alive) setReady(true);
      });
    return () => {
      alive = false;
    };
  }, []);

  const login = useCallback(async (username: string, password: string) => {
    const res = await apiLogin(username, password);
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const register = useCallback(async (username: string, email: string, password: string) => {
    const res = await apiRegister(username, email, password);
    setToken(res.access_token);
    setUser(res.user);
  }, []);

  const logout = useCallback(() => {
    setToken(null);
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, ready, login, register, logout, setUser }}>
      {children}
    </AuthContext.Provider>
  );
}
