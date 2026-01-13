
/* assets/js/chatbot.js */
/* OpenSDGChatbot – rein clientseitiges RAG-Widget für Open SDG
 * Architektur A: Statisch, ohne Serverdienste.
 * Abhängigkeiten: keine. Lädt facts.json + docs.json.
 */
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
    // Optional: weitere Sprachen hier ergänzen
  };

  // Einfache Normalisierung & Tokenisierung
  function norm(s) { return (s || "").toLowerCase().replace(/\s+/g, " ").trim(); }
  function tokens(s) { return norm(s).split(/[^a-z0-9äöüß\-\.]+/).filter(Boolean); }

  // sehr einfache Punktwertung: gemeinsame Token, Bonus für genaue ID-Treffer
  function scoreDoc(query, doc) {
    const qTok = tokens(query);
    const text = `${doc.title} ${doc.summary} ${doc.snippets?.join(" ") || ""}`;
    const dTok = tokens(text);
    const setD = new Set(dTok);
    let score = 0;
    qTok.forEach(t => { if (setD.has(t)) score += 1; });
    // Bonus: exakte Indikator-ID im Text/ID
    const idMatch = query.match(/\b\d+[.\-]\d+(?:[.\-]\d+)?[a-z]?\b/i);
    if (idMatch && (doc.id === idMatch[0] || text.includes(idMatch[0]))) score += 3;
    return score;
  }

  // Trendpfeil
  function trendSymbol(delta) { return delta > 0 ? "↗" : delta < 0 ? "↘" : "→"; }

  // Hauptobjekt
  const OpenSDGChatbot = {
    cfg: null,
    facts: {},     // { id: {unit, source, url, series:[{year,value},…]} }
    docs: [],      // [{ id, title, summary, snippets[], url }]
    lang: "de",

    async init(cfg) {
      this.cfg = cfg || {};
      this.lang = (cfg.lang || "de");
      const UI = T[this.lang] || T.de;

      try {
        // Daten laden
        const factsResp = await fetch(cfg.dataPaths.facts, { cache: "no-store" });
        const docsResp  = await fetch(cfg.dataPaths.docs,  { cache: "no-store" });
        this.facts = await factsResp.json();
        this.docs  = await docsResp.json();
      } catch (e) {
        console.error("Daten konnten nicht geladen werden:", e);
      }

      // UI bauen
      this.mountUI(UI);
    },

    mountUI(UI) {
