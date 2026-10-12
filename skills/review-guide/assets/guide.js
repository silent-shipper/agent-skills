(() => {
  const $ = (selector, root = document) => root.querySelector(selector);
  const $$ = (selector, root = document) => [...root.querySelectorAll(selector)];
  const storageKey = document.body.dataset.key;
  const reviewed = new Set(JSON.parse(localStorage.getItem(storageKey) || "[]"));
  const allPaths = [...new Set($$(".file[data-path]").map((card) => card.dataset.path))];

  const activeTab = () => $(".tab:not([hidden])");
  const save = () => localStorage.setItem(storageKey, JSON.stringify([...reviewed]));

  function expand(card) {
    card.classList.remove("collapsed");
    $(".lazy", card)?.remove();
  }

  function sync() {
    for (const card of $$(".file[data-path]")) {
      const done = reviewed.has(card.dataset.path);
      card.classList.toggle("reviewed", done);
      $("[data-review]", card).checked = done;
    }
    for (const row of $$(".frow")) row.classList.toggle("done", reviewed.has(row.dataset.path));
    for (const box of $$("[data-chapter]")) {
      const files = JSON.parse(box.closest(".chapter").dataset.files);
      box.checked = files.every((path) => reviewed.has(path));
    }
    const count = allPaths.filter((path) => reviewed.has(path)).length;
    $("#progress").textContent = `${count} / ${allPaths.length} reviewed`;
  }

  function setReviewed(paths, done) {
    for (const path of paths) {
      done ? reviewed.add(path) : reviewed.delete(path);
      for (const card of $$(".file[data-path]")) {
        if (card.dataset.path !== path) continue;
        if (done) card.classList.add("collapsed");
        else expand(card);
      }
    }
    save();
    sync();
  }

  function goToFile(path) {
    const card = $$(".file[data-path]", activeTab()).find((item) => item.dataset.path === path)
      || $$(".file[data-path]").find((item) => item.dataset.path === path);
    if (!card) return;
    if (card.closest(".tab").hidden) showTab(card.closest(".tab").dataset.tab);
    expand(card);
    card.scrollIntoView({ block: "start", behavior: "smooth" });
  }

  function showTab(name) {
    for (const tab of $$(".tab")) tab.hidden = tab.dataset.tab !== name;
    for (const button of $$(".tabs button")) button.classList.toggle("on", button.dataset.tab === name);
  }

  document.addEventListener("click", (event) => {
    const target = event.target;
    const tab = target.closest(".tabs button, [data-tab-link]");
    if (tab) {
      event.preventDefault();
      showTab(tab.dataset.tab || tab.dataset.tabLink);
      return window.scrollTo(0, 0);
    }

    const chev = target.closest(".chev");
    if (chev) {
      const card = chev.closest(".file");
      card.classList.contains("collapsed") ? expand(card) : card.classList.add("collapsed");
      return;
    }
    const lazy = target.closest(".lazy button");
    if (lazy) return expand(lazy.closest(".file"));

    const gap = target.closest(".gap.x");
    if (gap) {
      gap.nextElementSibling?.classList.add("open");
      gap.remove();
      return;
    }
    const row = target.closest(".frow");
    if (row) {
      event.preventDefault();
      return goToFile(row.dataset.path);
    }
    const jump = target.closest("[data-goto-file]");
    if (jump) {
      event.preventDefault();
      return goToFile(jump.dataset.gotoFile);
    }
    const copy = target.closest("[data-copy]");
    if (copy) {
      navigator.clipboard?.writeText(copy.dataset.copy);
      copy.textContent = "✓";
      setTimeout(() => (copy.textContent = "···"), 900);
    }
  });

  document.addEventListener("change", (event) => {
    const file = event.target.closest("[data-review]");
    if (file) return setReviewed([file.dataset.review], file.checked);
    const chapter = event.target.closest("[data-chapter]");
    if (chapter) setReviewed(JSON.parse(chapter.closest(".chapter").dataset.files), chapter.checked);
  });

  $("#theme").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = next;
    localStorage.setItem("review-guide-theme", next);
  });

  $("#collapse").addEventListener("click", () => {
    const cards = $$(".file", activeTab());
    const collapse = cards.some((card) => !card.classList.contains("collapsed"));
    for (const card of cards) collapse ? card.classList.add("collapsed") : expand(card);
  });

  const time = $("time[data-created]");
  const created = Date.parse(time.dataset.created);
  if (created) {
    const seconds = Math.max(0, (Date.now() - created) / 1000);
    const units = [["y", 31536000], ["w", 604800], ["d", 86400], ["h", 3600], ["m", 60]];
    const [unit, size] = units.find(([, size]) => seconds >= size) || ["s", 1];
    time.textContent = seconds < 60 ? "just now" : `${Math.floor(seconds / size)}${unit} ago`;
    time.title = new Date(created).toLocaleString();
  }

  for (const card of $$(".file[data-path]")) if (reviewed.has(card.dataset.path)) card.classList.add("collapsed");
  sync();

  const SVG = "http://www.w3.org/2000/svg";

  function rounded(points, radius = 6) {
    let path = `M${points[0][0]} ${points[0][1]}`;
    for (let i = 1; i < points.length - 1; i++) {
      const [px, py] = points[i - 1], [x, y] = points[i], [nx, ny] = points[i + 1];
      const r = Math.min(radius, Math.hypot(x - px, y - py) / 2, Math.hypot(nx - x, ny - y) / 2);
      path += ` L${x - Math.sign(x - px) * r} ${y - Math.sign(y - py) * r} Q${x} ${y} ${x + Math.sign(nx - x) * r} ${y + Math.sign(ny - y) * r}`;
    }
    const [lx, ly] = points[points.length - 1];
    return `${path} L${lx} ${ly}`;
  }

  function drawDiagram(diagram, index) {
    const svg = $(".dwires", diagram);
    if (!diagram.offsetParent) return;
    $$(".dlabel", diagram).forEach((label) => label.remove());
    const origin = diagram.getBoundingClientRect();
    const rowGap = parseFloat(getComputedStyle($(".dgrid", diagram)).rowGap) || 30;
    const box = (id) => {
      const node = $$(".dnode", diagram).find((item) => item.dataset.id === id);
      if (!node) return null;
      const r = node.getBoundingClientRect();
      const left = r.left - origin.left + diagram.scrollLeft, top = r.top - origin.top;
      return { l: left, r: left + r.width, t: top, b: top + r.height, y: top + r.height / 2 };
    };
    const marker = `arrow-${index}`;
    let paths = `<defs><marker id="${marker}" viewBox="0 0 8 8" refX="7.5" refY="4" markerWidth="8" markerHeight="8" orient="auto">`
      + `<path d="M2 1.2 L7 4 L2 6.8" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"/></marker></defs>`;
    const edges = JSON.parse(diagram.dataset.edges);
    const incoming = {};
    const wraps = {};
    for (const edge of edges) incoming[edge.to] = (incoming[edge.to] || 0) + 1;
    for (const edge of edges) {
      const s = box(edge.from), t = box(edge.to);
      if (!s || !t) continue;
      let points, label;
      const exit = s.r + 14;
      if (Math.abs(s.y - t.y) < 2 && t.l > s.r) {
        points = [[s.r, s.y], [t.l - 1, t.y]];
        label = [(s.r + t.l) / 2, s.y];
      } else if (t.l > exit + 24 && t.t > s.t) {
        points = [[s.r, s.y], [exit, s.y], [exit, t.y], [t.l - 1, t.y]];
        label = [(exit + t.l) / 2, t.y];
      } else {
        const offset = 8 * (wraps[edge.from] = (wraps[edge.from] ?? -1) + 1);
        const lane = (t.t > s.b ? t.t - rowGap / 2 : s.b + rowGap / 2) + offset;
        const shared = incoming[edge.to] > 1;
        const entry = t.l - (edge.label && !shared ? 46 : 22);
        points = [[s.r, s.y], [exit + offset, s.y], [exit + offset, lane], [entry, lane], [entry, t.y], [t.l - 1, t.y]];
        label = shared ? [exit + offset - 20, lane] : [entry + 22, t.y];
      }
      paths += `<path d="${rounded(points)}" fill="none" stroke="currentColor" marker-end="url(#${marker})"/>`;
      if (edge.label) {
        const tag = document.createElement("span");
        tag.className = "dlabel";
        tag.textContent = edge.label;
        tag.style.left = `${label[0]}px`;
        tag.style.top = `${label[1]}px`;
        diagram.append(tag);
      }
    }
    svg.innerHTML = paths;
  }

  $$(".diagram").forEach((diagram, index) => new ResizeObserver(() => drawDiagram(diagram, index)).observe(diagram));
})();
