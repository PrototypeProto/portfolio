import { useState } from "react";
import { createThread } from "../services/forum/forumService";
import type { ThreadRead } from "../types/forumTypes";

interface UseCreateThreadResult {
  submitting: boolean;
  error: string | null;
  submit: (topicId: string, title: string, body: string) => Promise<ThreadRead | null>;
}

export function useCreateThread(): UseCreateThreadResult {
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(
    topicId: string,
    title: string,
    body: string,
  ): Promise<ThreadRead | null> {
    setSubmitting(true);
    setError(null);
    const res = await createThread(topicId, { title, body });
    setSubmitting(false);
    if (!res.ok || !res.data) {
      setError(res.error ?? "Failed to create thread");
      return null;
    }
    return res.data;
  }

  return { submitting, error, submit };
}