/* assets/js/chatbot.js */
(function () {
  const T = {
    de: {
      title: "Chat Integrationsmonitoring",
      placeholder: "Frage eingeben (z. B. „Letzter Wert 3.1.2 seit 2015?“)…",
      send: "Senden",
      empty: "Dazu liegen mir keine Daten vor.",
      sources: "Quellen",
      thinking: "Suche relevante Informationen…",
      close: "Schließen",
    }
  };

  function norm(s) { return (s || "").toLowerCase().replace(/\s+/g, " ").trim(); }
  function tokens(s) { return norm(s).split(/[^a-z0-9äöüß\-\.]+/).filter(Boolean); }

  function scoreDoc(query, doc) {
    const qTok = tokens(query);
    const text = `${doc.title} ${doc.summary} ${doc.snippets?.join(" ") || ""}`;
    const dTok = tokens(text);
    const setD = new Set(dTok);
    let score = 0;
    qTok.forEach(t => { if (setD.has(t)) score += 1; });
    const idMatch = query.match(/\b\d+[.\-]\d+(?:[.\-]\d+)?[a-z]?\b/i);
    if (idMatch && (doc.id === idMatch[0] || text.includes(idMatch[0]))) score += 3;
    return score;
  }

  function trendSymbol(delta) { return delta > 0 ? "↗" : delta < 0 ? "↘" : "→"; }

  const OpenSDGChatbot = {
    cfg: null,
    facts: {},
    docs: [],
    lang: "de",

    async init(cfg) {
      this.cfg = cfg || {};
      this.lang = (cfg.lang || "de");
      const UI = T[this.lang] || T.de;

      try {
        const factsResp = await fetch(cfg.dataPaths.facts, { cache: "no-store" });
        const docsResp  = await fetch(cfg.dataPaths.docs,  { cache: "no-store" });
        this.facts = await factsResp.json();
        this.docs  = await docsResp.json();
      } catch (e) {
        console.error("Daten konnten nicht geladen werden:", e);
      }

      this.mountUI(UI);
    },

    mountUI(UI) {
      // Chat Container
      const container = document.createElement("div");
      container.id = "chatbot-container";
      container.innerHTML = `
        <div id="chatbot-header">${UI.title} <button id="chatbot-close">${UI.close}</button></div>
        <div id="chatbot-messages"></div>
        <div id="chatbot-input">
          <input type="text" placeholder="${UI.placeholder}" />
          <button>${UI.send}</button>
        </div>
      `;
      document.body.appendChild(container);

      // Events
      const messages = container.querySelector("#chatbot-messages");
      const input = container.querySelector("input");
      const sendBtn = container.querySelector("button");

      container.querySelector("#chatbot-close").addEventListener("click", () => {
        container.style.display = "none";
      });

      const addMessage = (text, from = "bot") => {
        const msg = document.createElement("div");
        msg.className = `chatbot-msg ${from}`;
        msg.textContent = text;
        messages.appendChild(msg);
        messages.scrollTop = messages.scrollHeight;
      };

      const handleQuery = (q) => {
        addMessage(q, "user");
        addMessage(UI.thinking, "bot");

        setTimeout(() => {
          const scored = this.docs.map(d => ({ doc: d, score: scoreDoc(q, d) }));
          scored.sort((a,b) => b.score - a.score);
          const best = scored[0];

          messages.lastChild.remove(); // remove "thinking"

          if (!best || best.score === 0) {
            addMessage(UI.empty, "bot");
          } else {
            const fact = this.facts[best.doc.id];
            let ans = `${best.doc.title}\n${best.doc.summary}`;
            if (fact && fact.series && fact.series.length) {
              const latest = fact.series[fact.series.length-1];
              ans += `\nLetzter Wert (${latest.year}): ${latest.value} ${fact.unit} ${trendSymbol(latest.value - (fact.series[fact.series.length-2]?.value || latest.value))}`;
            }
            ans += `\n${UI.sources}: ${fact?.source || best.doc.snippets.join(", ")}`;
            addMessage(ans, "bot");
          }
        }, 200); // simuliere kurze "Verarbeitung"
      };

      sendBtn.addEventListener("click", () => { 
        if (input.value.trim()) handleQuery(input.value); 
        input.value = "";
      });

      input.addEventListener("keypress", (e) => {
        if (e.key === "Enter" && input.value.trim()) {
          handleQuery(input.value);
          input.value = "";
        }
      });
    }
  };

  window.OpenSDGChatbot = OpenSDGChatbot;
})();
