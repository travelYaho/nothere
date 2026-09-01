import { FormEvent, useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { fetchHome, fetchMe, signup, type HomeResponse, type UserResponse } from "./lib/api";
import { supabase } from "./lib/supabase";

type Mode = "login" | "signup";

export default function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [mode, setMode] = useState<Mode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [nickname, setNickname] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [me, setMe] = useState<UserResponse | null>(null);
  const [home, setHome] = useState<HomeResponse | null>(null);

  useEffect(() => {
    supabase.auth.getSession().then(({ data }) => setSession(data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_event, next) => {
      setSession(next);
    });
    return () => sub.subscription.unsubscribe();
  }, []);

  useEffect(() => {
    if (!session?.access_token) {
      setMe(null);
      setHome(null);
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const [user, homeData] = await Promise.all([
          fetchMe(session.access_token),
          fetchHome(session.access_token),
        ]);
        if (!cancelled) {
          setMe(user);
          setHome(homeData);
          setError(null);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "데이터를 불러오지 못했습니다.");
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [session?.access_token]);

  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      if (mode === "signup") {
        const result = await signup({ email, password, nickname });
        if (result.accessToken && result.refreshToken) {
          await supabase.auth.setSession({
            access_token: result.accessToken,
            refresh_token: result.refreshToken,
          });
        } else {
          const { error: signInError } = await supabase.auth.signInWithPassword({
            email,
            password,
          });
          if (signInError) throw signInError;
        }
      } else {
        const { error: signInError } = await supabase.auth.signInWithPassword({
          email,
          password,
        });
        if (signInError) throw signInError;
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "인증에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function onLogout() {
    await supabase.auth.signOut();
  }

  return (
    <div className="app-shell">
      <h1 className="brand">여기말GO</h1>
      <p className="lead">여행 일정을 등록하고, 혼잡이 예상되는 장소를 바꿔 보세요.</p>

      {!session ? (
        <section className="panel">
          <h2>{mode === "login" ? "로그인" : "회원가입"}</h2>
          <form className="stack" onSubmit={onSubmit}>
            <label>
              이메일
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
              />
            </label>
            <label>
              비밀번호
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={6}
                autoComplete={mode === "login" ? "current-password" : "new-password"}
              />
            </label>
            {mode === "signup" && (
              <label>
                닉네임
                <input
                  value={nickname}
                  onChange={(e) => setNickname(e.target.value)}
                  required
                  maxLength={50}
                />
              </label>
            )}
            <div className="actions">
              <button type="submit" disabled={busy}>
                {busy ? "처리 중…" : mode === "login" ? "로그인" : "가입하기"}
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => setMode(mode === "login" ? "signup" : "login")}
              >
                {mode === "login" ? "회원가입으로" : "로그인으로"}
              </button>
            </div>
          </form>
          {error && <p className="error">{error}</p>}
        </section>
      ) : (
        <>
          <section className="panel">
            <h2>내 정보</h2>
            {me ? (
              <>
                <p>
                  <strong>{me.nickname}</strong> · {me.email}
                </p>
                <div className="actions">
                  <button type="button" className="secondary" onClick={onLogout}>
                    로그아웃
                  </button>
                </div>
              </>
            ) : (
              <p className="muted">불러오는 중…</p>
            )}
            {error && <p className="error">{error}</p>}
          </section>

          <section className="panel">
            <h2>홈 요약</h2>
            {!home ? (
              <p className="muted">불러오는 중…</p>
            ) : (
              <>
                <p className="muted">진행 중 일정</p>
                {home.draftSchedule ? (
                  <p>
                    {home.draftSchedule.title}{" "}
                    <span className="meta">
                      <span>{home.draftSchedule.status}</span>
                      <span>{home.draftSchedule.travelDate ?? "날짜 미정"}</span>
                    </span>
                  </p>
                ) : (
                  <p className="muted">진행 중 일정이 없습니다.</p>
                )}
                <p className="muted" style={{ marginTop: "1rem" }}>
                  최근 일정
                </p>
                {home.recentSchedules.length === 0 ? (
                  <p className="muted">최근 일정이 없습니다.</p>
                ) : (
                  <ul className="list">
                    {home.recentSchedules.map((item) => (
                      <li key={item.scheduleId}>
                        <strong>{item.title}</strong>
                        <div className="meta">
                          <span>{item.status}</span>
                          <span>{item.travelDate ?? "날짜 미정"}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </section>
        </>
      )}
    </div>
  );
}
