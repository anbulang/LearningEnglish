import { useState } from "react";
import type { AdminOperationsIssue, Language } from "../domain/types";
import { messages } from "../i18n/messages";

interface ActionDrawerProps {
  language: Language;
  issue: AdminOperationsIssue;
  isOpen: boolean;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (reason: string) => void | Promise<void>;
}

export function ActionDrawer({ language, issue, isOpen, isSubmitting, onClose, onSubmit }: ActionDrawerProps) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const copy = messages[language];
  const isUnavailable = issue.recommendedAction === "unavailable";

  if (!isOpen) {
    return null;
  }

  function handleSubmit() {
    const normalizedReason = reason.trim();
    if (!normalizedReason) {
      setError(copy["actionDrawer.reasonRequired"]);
      return;
    }
    setError("");
    void onSubmit(normalizedReason);
  }

  return (
    <div className="action-drawer-backdrop" role="presentation">
      <aside className="action-drawer" role="dialog" aria-modal="true" aria-label={copy["actionDrawer.title"]}>
        <div className="section-title">
          <div>
            <h2>{copy["actionDrawer.title"]}</h2>
            <p>{issue.reason}</p>
          </div>
          <button type="button" className="ghost-button" onClick={onClose}>
            {copy["actionDrawer.close"]}
          </button>
        </div>

        <dl className="detail-list compact">
          <dt>{copy["actionDrawer.status"]}</dt>
          <dd>{issue.statusLabel}</dd>
          <dt>{copy["actionDrawer.action"]}</dt>
          <dd>{issue.recommendedAction}</dd>
          <dt>{copy["actionDrawer.resource"]}</dt>
          <dd>{issue.relatedResource.type}</dd>
          <dt>{copy["actionDrawer.resourceId"]}</dt>
          <dd>{issue.relatedResource.id}</dd>
          <dt>{copy["actionDrawer.tenant"]}</dt>
          <dd>{issue.relatedResource.tenantId ?? ""}</dd>
        </dl>

        <div className="audit-preview">
          <strong>{copy["actionDrawer.auditPreview"]}</strong>
          <span>
            {issue.recommendedAction} / {issue.relatedResource.type} / {issue.severity}
          </span>
        </div>

        <label className="drawer-reason">
          {copy["actionDrawer.reason"]}
          <textarea
            aria-label={copy["actionDrawer.reason"]}
            value={reason}
            onChange={(event) => {
              setReason(event.target.value);
              if (error) {
                setError("");
              }
            }}
            disabled={isUnavailable || isSubmitting}
          />
        </label>
        {error && <p className="form-error">{error}</p>}
        {isUnavailable && <p className="form-error neutral">{copy["actionDrawer.unavailable"]}</p>}

        <div className="audit-actions">
          <button type="button" className="primary-button" onClick={handleSubmit} disabled={isUnavailable || isSubmitting}>
            {isSubmitting ? copy["actionDrawer.submitting"] : copy["actionDrawer.submit"]}
          </button>
          <button type="button" className="ghost-button" onClick={onClose}>
            {copy["actionDrawer.cancel"]}
          </button>
        </div>
      </aside>
    </div>
  );
}
