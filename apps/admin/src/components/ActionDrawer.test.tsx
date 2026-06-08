import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { mockOperationsData } from "../domain/mockData";
import type { AdminOperationsIssue } from "../domain/types";
import { ActionDrawer } from "./ActionDrawer";

const issue = mockOperationsData.issues[0];

describe("ActionDrawer", () => {
  it("renders issue context and audit preview", () => {
    render(<ActionDrawer language="en" issue={issue} isOpen={true} isSubmitting={false} onClose={vi.fn()} onSubmit={vi.fn()} />);

    expect(screen.getByRole("dialog", { name: "Action review" })).toBeInTheDocument();
    expect(screen.getByText("Parse failed")).toBeInTheDocument();
    expect(screen.getByText("retry_material_job")).toBeInTheDocument();
    expect(screen.getByText("material_parse_job")).toBeInTheDocument();
    expect(screen.getByText("Audit preview")).toBeInTheDocument();
  });

  it("requires a reason before submitting", async () => {
    const onSubmit = vi.fn();
    render(<ActionDrawer language="en" issue={issue} isOpen={true} isSubmitting={false} onClose={vi.fn()} onSubmit={onSubmit} />);

    await userEvent.click(screen.getByRole("button", { name: "Submit action" }));

    expect(onSubmit).not.toHaveBeenCalled();
    expect(screen.getByText("Reason is required.")).toBeInTheDocument();

    await userEvent.type(screen.getByLabelText("Audit reason"), "OCR provider recovered.");
    await userEvent.click(screen.getByRole("button", { name: "Submit action" }));

    expect(onSubmit).toHaveBeenCalledWith("OCR provider recovered.");
  });

  it("disables submit for unavailable actions", () => {
    const unavailableIssue: AdminOperationsIssue = {
      ...issue,
      recommendedAction: "unavailable"
    };

    render(
      <ActionDrawer
        language="en"
        issue={unavailableIssue}
        isOpen={true}
        isSubmitting={false}
        onClose={vi.fn()}
        onSubmit={vi.fn()}
      />
    );

    expect(screen.getByRole("button", { name: "Submit action" })).toBeDisabled();
    expect(screen.getByText("Action is not available from this console.")).toBeInTheDocument();
  });
});
