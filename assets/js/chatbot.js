(function () {

  function norm(s) {
    return (s || "").toLowerCase().trim();
  }

  function tokens(s) {
    return norm(s).split(/[^a-z0-9äöüß\-\.]+/).filter(Boolean);
  }

  function scoreIndicator(query, ind) {
    let score = 0;
    const q = norm(query);

    // 1️⃣ Exakte ID (höchste Priorität)
    if (ind.id && q.includes(ind.id.replace("-", "."))) score += 50;

    // 2️⃣ Keywords
    if (ind.keywords) {
      ind.keywords.forEach(k => {
        if (q.includes(k)) score += 8;
      });
    }

    // 3️⃣ Name
    if (ind.name && q.includes(ind.name.toLowerCase())) score += 10;

    return score;
  }

  const Chatbot = {
    data: [],
    lang: "de",

    async init(cfg) {
      const resp = await fetch(cfg.dataPaths.indicators, { cache: "no-store" });
      this.data = await resp.json();
      this.mount();
    },

    mount() {
      const box = document.createElement("div");
      box.id = "chatbot";

      box.innerHTML = `
        <div class="cb-header">📊 Integrationsmonitoring-Chat</div>
        <div class="cb-messages" id="cb-msg"></div>
        <div class="cb-input">
          <input id="cb-q" placeholder="Frage eingeben…" />
          <button id="cb-send">Senden</button>
        </div>
      `;

      document.body.appendChild(box);

      document.getElementById("cb-send").onclick = () => this.ask();
      document.getElementById("cb-q").onkeydown = e => {
        if (e.key === "Enter") this.ask();
      };
    },

    ask() {
      const q = document.getElementById("cb-q").value;
      if (!q) return;

      const msg = document.getElementById("cb-msg");
      msg.innerHTML += `<div class="user">${q}</div>`;

      const scored = this.data
        .map(i => ({ i, s: scoreIndicator(q, i) }))
        .filter(x => x.s > 0)
        .sort((a,b) => b.s - a.s)
        .slice(0, 1);   // 🔥 NUR BESTER TREFFER

      if (!scored.length) {
        msg.innerHTML += `<div class="bot">Dazu liegen mir keine passenden Daten vor.</div>`;
        return;
      }

      const ind = scored[0].i;

      msg.innerHTML += `
        <div class="bot">
          <strong>${ind.id} – ${ind.name}</strong><br>
          ${ind.short_definition}<br><br>
          🔗 <a href="${ind.url}" target="_blank">Indikatorseite öffnen</a>
        </div>
      `;
    }
  };

  window.OpenSDGChatbot = Chatbot;

})();
