import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it } from "vitest";
import { LanguageToggle } from "@/components/layout/LanguageToggle";
import { useLocaleStore } from "@/stores/localeStore";
import { useT } from "@/i18n";
import { en } from "./en";
import { ta } from "./ta";

function Probe() {
  const t = useT();
  return <p>{t("nav.today")}</p>;
}

describe("language toggle", () => {
  beforeEach(() => {
    useLocaleStore.setState({ locale: "en" });
  });

  it("switches visible strings, sets <html lang> and persists the choice", () => {
    render(
      <>
        <LanguageToggle />
        <Probe />
      </>
    );

    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "EN" })).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(screen.getByRole("button", { name: "தமிழ்" }));

    expect(screen.getByText("இன்று")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "தமிழ்" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "EN" })).toHaveAttribute("aria-pressed", "false");
    expect(document.documentElement.lang).toBe("ta");

    const stored = localStorage.getItem("livocrm-locale");
    expect(stored).not.toBeNull();
    expect(JSON.parse(stored ?? "{}")).toMatchObject({ state: { locale: "ta" } });
  });

  it("returns to English from Tamil", () => {
    useLocaleStore.setState({ locale: "ta" });
    render(
      <>
        <LanguageToggle />
        <Probe />
      </>
    );

    fireEvent.click(screen.getByRole("button", { name: "EN" }));

    expect(screen.getByText("Today")).toBeInTheDocument();
    expect(document.documentElement.lang).toBe("en");
  });

  it("has a Tamil string for every English key", () => {
    for (const key of Object.keys(en) as (keyof typeof en)[]) {
      expect(ta[key], key).toBeTruthy();
    }
  });
});
