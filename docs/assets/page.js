const stops = [...document.querySelectorAll(".itinerary a[href^='#']")];
const seen = new IntersectionObserver((entries) => {
  for (const e of entries) {
    if (!e.isIntersecting) continue;
    for (const a of stops) a.parentElement.classList.toggle("on", a.getAttribute("href") === `#${e.target.id}`);
  }
}, { rootMargin: "-25% 0px -65% 0px" });
for (const a of stops) {
  const target = document.getElementById(a.getAttribute("href").slice(1));
  if (target) seen.observe(target);
}
