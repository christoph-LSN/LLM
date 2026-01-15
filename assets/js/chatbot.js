/* assets/js/chatbot.js
 * OpenSDGChatbot – clientseitiger Wissens-Chatbot
 * Datenbasis: training_data.json
 * Kein Backend, GitHub Pages kompatibel
 */

(function () {

  /* =========================
     UI Texte
     ========================= */
  const T = {
    de: {
      title: "Chat Integrationsmonitoring",
      placeholder: "Frage stellen (z. B. „Was ist Bevölkerung in Niedersachsen?“)",
      send: "Senden",
      empty: "Dazu liegen mir keine Daten vor.",
      thinking: "Suche relevante Informationen …",
      close: "✕",
      source: "Quelle"
    }
  };

  /* =========================
     Hilfsfunktionen
     ========================= */
  function norm(s) {
    return (s || "")
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();
  }

  function tokens(s) {
    return norm(s)
      .split(/[^a-z0-9äöüß\-]+/)
      .filter(Boolean);
  }

  function scoreEntry(query, entry) {
    const qTok = tokens(query);

    const text = `
      ${entry.id || ""}
      ${entry.name || ""}
      ${entry.definition || ""}
      ${entry.methodology || ""}
      ${entry.additional_info || ""}
    `;

    const dTok = tokens(text);
    const setD = new Set(dTok);

    let score = 0;
    qTok.forEach(t => {
      if (setD.has(t)) score++;
    });

    // Bonus bei exakter ID
    if (entry.id && query.includes(entry.id)) {
      score += 5;
    }

    return score;
  }

  function buildAnswer(entry) {
    let out = `📊 ${entry.name || entry.id}\n\n`;

    if (entry.definition) {
      out += `🧾 Definition:\n${entry.definition}\n\n`;
    }

    if (entry.methodology) {
      out += `📐 Methodik:\n${entry.methodology}\n\n`;
    }

    if (Array.isArray(entry.csv_data) && entry.csv_data.length > 0) {
      const last = entry.csv_data[entry.csv_data.length - 1];
      if (last?.Value && last?.Year) {
        out += `📈 Beispielwert:\n`;
        out += `${last.Year}`;
        if (last.Gebietseinheit) {
          out += ` – ${last.Gebietseinheit}`;
        }
        out += `: ${last.Value}\n\n`;
      }
    }

    if (entry.url) {
      out += `🔗 ${T.de.source}: ${entry.url}`;
    }

    return out.trim();
  }

  /* =========================
     Hauptobjekt
     ========================= */
  const OpenSDGChatbot = {
    cfg: null,
    data: [],
    lang: "de",

    async init(cfg) {
      this.cfg = cfg || {};
      this.lang = cfg.lang || "de";

      try {
        const resp = await fetch(cfg.dataPaths.training, { cache: "no-store" });
        this.data = await resp.json();
      } catch (e) {
        console.error("training_data.json konnte nicht geladen werden", e);
        this.data = [];
      }

      this.mountUI(T[this.lang] || T.de);
    },

    mountUI(UI) {
      const container = document.createElement("div");
      container.id = "chatbot-container";
      container.innerHTML = `
        <div id="chatbot-header">
          ${UI.title}
          <button id="chatbot-close">${UI.close}</button>
        </div>
        <div id="chatbot-messages"></div>
        <div id="chatbot-input">
          <input type="text" placeholder="${UI.placeholder}" />
          <button>${UI.send}</button>
        </div>
      `;
      document.body.appendChild(container);

      const messages = container.querySelector("#chatbot-messages");
      const input = container.querySelector("input");
      const sendBtn = container.querySelector("#chatbot-input button");

      container.querySelector("#chatbot-close")
        .addEventListener("click", () => {
          container.style.display = "none";
        });

      const addMessage = (text, who) => {
        const div = document.createElement("div");
        div.className = `chatbot-msg ${who}`;
        div.textContent = text;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
      };

      const handleQuery = (q) => {
        addMessage(q, "user");
        addMessage(UI.thinking, "bot");

        setTimeout(() => {
          messages.lastChild.remove();

          const scored = this.data
            .map(e => ({ entry: e, score: scoreEntry(q, e) }))
            .sort((a, b) => b.score - a.score);

          if (!scored.length || scored[0].score === 0) {
            addMessage(UI.empty, "bot");
            return;
          }

          const answer = buildAnswer(scored[0].entry);
          addMessage(answer, "bot");

        }, 150);
      };

      sendBtn.addEventListener("click", () => {
        if (input.value.trim()) {
          handleQuery(input.value.trim());
          input.value = "";
        }
      });

      input.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && input.value.trim()) {
          handleQuery(input.value.trim());
          input.value = "";
        }
      });
    }
  };

  window.OpenSDGChatbot = OpenSDGChatbot;
})();
