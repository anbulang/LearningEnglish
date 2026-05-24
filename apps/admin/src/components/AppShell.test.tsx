import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { App } from "../App";

describe("AppShell", () => {
  it("shows tenant scope and switches language", async () => {
    render(<App />);
    expect(screen.getByText("所有租户")).toBeInTheDocument();
    expect(screen.getByText("指挥台")).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "English" }));

    expect(screen.getByText("All tenants")).toBeInTheDocument();
    expect(screen.getByText("Command Center")).toBeInTheDocument();
  });
});
