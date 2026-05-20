"use client";

import { useMemo, useState } from "react";

type ClassificationResponse = {
  success: boolean;
  result?: unknown;
  message?: string;
};

export default function Home() {
  const [sender, setSender] = useState("");
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [resultText, setResultText] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [wakeStatus, setWakeStatus] = useState<string | null>(null);
  const [isWaking, setIsWaking] = useState(false);

  const apiBase =
    process.env.NEXT_PUBLIC_API_BASE?.replace(/\/$/, "") ??
    "https://api.kunal.engineer";

  const emailText = useMemo(() => {
    const trimmedBody = body.trim();
    return [
      sender ? `From: ${sender}` : null,
      subject ? `Subject: ${subject}` : null,
      trimmedBody || null,
    ]
      .filter(Boolean)
      .join("\n\n");
  }, [sender, subject, body]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setResultText(null);
    setIsSubmitting(true);

    try {
      const response = await fetch(`${apiBase}/classify`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email_text: emailText,
        }),
      });

      const data = (await response.json()) as ClassificationResponse;

      if (!response.ok || !data.success) {
        throw new Error(data.message ?? "Classification failed.");
      }

      try {
        setResultText(
          JSON.stringify(data.result ?? "No result returned.", null, 2)
        );
        console.log("Raw model output:", data.result);
      } catch {
        setResultText(String(data.result ?? "No result returned."));
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to reach the backend."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleWake = async () => {
    setWakeStatus("Waking service...");
    setIsWaking(true);

    try {
      const response = await fetch(`${apiBase}/wake`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
      });

      if (!response.ok) {
        throw new Error("Wake request failed.");
      }

      setWakeStatus("Backend awake. GPU hello-world completed.");
    } catch (err) {
      setWakeStatus(
        err instanceof Error
          ? err.message
          : "Wake request failed. Check the backend."
      );
    } finally {
      setIsWaking(false);
    }
  };

  const parsedLabel = useMemo(() => {
    if (!resultText) {
      return null;
    }

    try {
      const parsed = JSON.parse(resultText) as { label?: string };
      return parsed.label ?? null;
    } catch {
      return null;
    }
  }, [resultText]);

  return (
    <div className="mesh-bg flex min-h-screen flex-col items-center justify-center px-6 py-16">
      <main className="glass-card rise-in w-full max-w-5xl rounded-[32px] px-8 py-10 sm:px-12">
        <div className="flex flex-col gap-8 lg:flex-row lg:items-start">
          <section className="flex-1 space-y-6">
            <div className="space-y-3">
              <p className="text-xs uppercase tracking-[0.3em] text-[color:var(--accent)]">
                Email Trust Lab
              </p>
              <h1 className="text-4xl font-semibold leading-tight text-[color:var(--foreground)] sm:text-5xl">
                Classify suspicious emails in seconds.
              </h1>
              <p className="text-base leading-7 text-[color:var(--ink-soft)]">
                Submit sender, subject, and body. The backend assembles a single
                payload for the model and returns the classification result.
              </p>
            </div>

            <form
              className="space-y-5 rounded-3xl border border-black/10 bg-white/60 p-6"
              onSubmit={handleSubmit}
            >
              <div className="space-y-2">
                <label className="text-sm font-medium text-[color:var(--ink-soft)]">
                  Sender
                </label>
                <input
                  className="w-full rounded-2xl border border-black/10 bg-white px-4 py-3 text-sm shadow-sm focus:border-[color:var(--accent)] focus:outline-none"
                  placeholder="alerts@bank.example"
                  value={sender}
                  onChange={(event) => setSender(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-[color:var(--ink-soft)]">
                  Subject
                </label>
                <input
                  className="w-full rounded-2xl border border-black/10 bg-white px-4 py-3 text-sm shadow-sm focus:border-[color:var(--accent)] focus:outline-none"
                  placeholder="Action required: verify your account"
                  value={subject}
                  onChange={(event) => setSubject(event.target.value)}
                />
              </div>
              <div className="space-y-2">
                <label className="text-sm font-medium text-[color:var(--ink-soft)]">
                  Body
                </label>
                <textarea
                  className="min-h-[160px] w-full resize-none rounded-2xl border border-black/10 bg-white px-4 py-3 text-sm shadow-sm focus:border-[color:var(--accent)] focus:outline-none"
                  placeholder="Paste the email body here..."
                  value={body}
                  onChange={(event) => setBody(event.target.value)}
                />
              </div>
              <div className="flex flex-col gap-3 sm:flex-row">
                <button
                  className="glow-ring shine flex-1 rounded-full px-6 py-3 text-sm font-semibold text-[color:var(--accent-dark)] transition hover:translate-y-[-1px]"
                  type="submit"
                  disabled={isSubmitting || emailText.length === 0}
                >
                  {isSubmitting ? "Classifying..." : "Classify Email"}
                </button>
                <button
                  className="flex-1 rounded-full border border-black/15 px-6 py-3 text-sm font-semibold text-[color:var(--foreground)] transition hover:border-black/30"
                  type="button"
                  onClick={handleWake}
                  disabled={isWaking}
                >
                  {isWaking ? "Waking..." : "Wake Backend"}
                </button>
              </div>
              <p className="text-xs text-[color:var(--ink-soft)]">
                API base: <span className="font-mono">{apiBase}</span>
              </p>
            </form>
          </section>

          <aside className="flex w-full flex-col gap-6 lg:w-[320px]">
            <div className="rounded-3xl border border-black/10 bg-white/70 p-5">
              <p className="text-sm font-semibold text-[color:var(--foreground)]">
                Live Output
              </p>
              <div className="mt-3 min-h-[140px] rounded-2xl border border-dashed border-black/10 bg-white/70 p-4 text-sm text-[color:var(--ink-soft)]">
                {error && <p className="text-red-600">{error}</p>}
                {!error && resultText !== null && (
                  <div className="space-y-3">
                    {parsedLabel && (
                      <div className="rounded-2xl border border-black/10 bg-white px-4 py-3 text-center">
                        <p className="text-xs uppercase tracking-[0.2em] text-[color:var(--ink-soft)]">
                          Classification
                        </p>
                        <p className="text-2xl font-semibold text-[color:var(--foreground)]">
                          {parsedLabel}
                        </p>
                      </div>
                    )}
                    <pre className="whitespace-pre-wrap font-mono text-xs text-[color:var(--foreground)]">
                      {resultText}
                    </pre>
                  </div>
                )}
                {!error && resultText === null && (
                  <p>
                    Submit an email to see the model response from the backend.
                  </p>
                )}
              </div>
            </div>

            <div className="rounded-3xl border border-black/10 bg-white/70 p-5">
              <p className="text-sm font-semibold text-[color:var(--foreground)]">
                Wake Status
              </p>
              <p className="mt-2 text-sm text-[color:var(--ink-soft)]">
                {wakeStatus ??
                  "Send a lightweight health check and a hello-world GPU call."}
              </p>
            </div>
          </aside>
        </div>
      </main>
    </div>
  );
}
