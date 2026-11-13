// The theme: the first visit follows the system, and a reader who picks one
// keeps it for the rest of the visit (sessionStorage), so moving between pages
// does not flip the colours back and forth.
//
// This file is a plain script in the head so the chosen theme is on the root
// element before the first paint; the button it drives arrives with the body,
// so the listener waits for it.
const root = document.documentElement;
const KEY = "moonucd-theme";
const saved = sessionStorage.getItem(KEY);
if (saved === "dark" || saved === "light") root.dataset.theme = saved;

function current() {
  const chosen = root.dataset.theme;
  if (chosen === "dark" || chosen === "light") return chosen;
  return matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
}

function wire() {
  const button = document.querySelector(".theme-toggle");
  if (!button) return;
  const relabel = () => {
    const next = current() === "dark" ? "light" : "dark";
    const text = `Switch to the ${next} theme`;
    button.setAttribute("aria-label", text);
    button.setAttribute("title", text);
  };
  relabel();
  button.addEventListener("click", () => {
    const next = current() === "dark" ? "light" : "dark";
    root.dataset.theme = next;
    sessionStorage.setItem(KEY, next);
    relabel();
  });
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", wire, { once: true });
} else {
  wire();
}
