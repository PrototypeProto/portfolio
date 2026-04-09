import { useState } from "react";
import { useCreateThread } from "../../hooks/useCreateThread";
import type { ThreadRead } from "../../types/forumTypes";
import "./NewThreadForm.css";

interface NewThreadFormProps {
  topicId: string;
  onCreated: (thread: ThreadRead) => void;
  onCancel: () => void;
}

export default function NewThreadForm({
  topicId,
  onCreated,
  onCancel,
}: NewThreadFormProps) {
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const { submitting, error, submit } = useCreateThread();

  const titleLimit = 200;
  const titleTooLong = title.length > titleLimit;
  const canSubmit =
    title.trim().length > 0 && body.trim().length > 0 && !titleTooLong;

  async function handleSubmit() {
    if (!canSubmit) return;
    const thread = await submit(topicId, title.trim(), body.trim());
    if (thread) onCreated(thread);
  }

  return (
    <div className="ntf-backdrop" onClick={onCancel}>
      <div className="ntf-modal" onClick={(e) => e.stopPropagation()}>
        <div className="ntf-header">
          <h2 className="ntf-title">New Thread</h2>
          <button className="ntf-close" onClick={onCancel} aria-label="Close">
            ✕
          </button>
        </div>

        <div className="ntf-body">
          <label className="ntf-label" htmlFor="ntf-thread-title">
            Title
            <span
              className={`ntf-char-count ${titleTooLong ? "ntf-char-count--over" : ""}`}
            >
              {title.length}/{titleLimit}
            </span>
          </label>
          <input
            id="ntf-thread-title"
            className={`ntf-input ${titleTooLong ? "ntf-input--error" : ""}`}
            type="text"
            placeholder="What's this thread about?"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            disabled={submitting}
            autoFocus
          />

          <label className="ntf-label" htmlFor="ntf-thread-body">
            Body
          </label>
          <textarea
            id="ntf-thread-body"
            className="ntf-textarea"
            placeholder="Write your post…"
            value={body}
            onChange={(e) => setBody(e.target.value)}
            disabled={submitting}
            rows={8}
          />

          {error && <p className="ntf-error">{error}</p>}
        </div>

        <div className="ntf-footer">
          <button
            className="ntf-btn ntf-btn--cancel"
            onClick={onCancel}
            disabled={submitting}
          >
            Cancel
          </button>
          <button
            className="ntf-btn ntf-btn--submit"
            onClick={handleSubmit}
            disabled={!canSubmit || submitting}
          >
            {submitting ? "Posting…" : "Post Thread"}
          </button>
        </div>
      </div>
    </div>
  );
}
