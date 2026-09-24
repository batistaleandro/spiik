import { Link, Navigate, NavLink, Route, Routes, useLocation } from "react-router-dom";
import type { ReactElement } from "react";
import { useAuth } from "./auth-context";
import AuthScreen from "./screens/AuthScreen";
import PracticeScreen from "./screens/PracticeScreen";
import ProfileScreen from "./screens/ProfileScreen";
import TrainerScreen from "./screens/TrainerScreen";
import WordsScreen from "./screens/WordsScreen";

function RequireAuth({ children }: { children: ReactElement }) {
  const { user, ready } = useAuth();
  const location = useLocation();
  if (!ready) {
    return (
      <main>
        <section className="card">
          <p className="message">…</p>
        </section>
      </main>
    );
  }
  if (!user) {
    return <Navigate to="/login" state={{ from: location.pathname }} replace />;
  }
  return children;
}

export default function App() {
  const { user } = useAuth();

  return (
    <div className="app">
      <header>
        <div className="header-row">
          <h1>
            <Link to="/" className="logo-link">
              spiik<span className="logo-dot">.</span>
            </Link>
          </h1>
          <nav className="main-nav">
            {user ? (
              <>
                <NavLink to="/" end>
                  Train
                </NavLink>
                <NavLink to="/practice">Practice</NavLink>
                <NavLink to="/words">Words</NavLink>
                <NavLink to="/profile">Profile</NavLink>
              </>
            ) : (
              <>
                <NavLink to="/" end>
                  Train
                </NavLink>
                <NavLink to="/login">Log in</NavLink>
              </>
            )}
          </nav>
        </div>
        <p className="tagline">
          learn pronunciation by hearing foreign words through your own language
        </p>
      </header>

      <Routes>
        <Route path="/" element={<TrainerScreen />} />
        <Route path="/login" element={<AuthScreen mode="login" />} />
        <Route path="/register" element={<AuthScreen mode="register" />} />
        <Route
          path="/practice"
          element={
            <RequireAuth>
              <PracticeScreen />
            </RequireAuth>
          }
        />
        <Route
          path="/words"
          element={
            <RequireAuth>
              <WordsScreen />
            </RequireAuth>
          }
        />
        <Route
          path="/profile"
          element={
            <RequireAuth>
              <ProfileScreen />
            </RequireAuth>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>

      <footer>
        espeak-ng · wav2vec2 · panphon · edge-tts — all phonetics compared in IPA
      </footer>
    </div>
  );
}
