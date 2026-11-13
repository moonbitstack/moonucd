// The page scroll bar sits out of the way while the page is at the top and
// shows from the first pixel scrolled, keeping its width so nothing shifts.
const root = document.documentElement;
const mark = () => root.classList.toggle("at-top", scrollY === 0);
addEventListener("scroll", mark, { passive: true });
addEventListener("resize", mark, { passive: true });
mark();
