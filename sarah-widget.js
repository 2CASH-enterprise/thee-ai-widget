/**
 * SARAH AI — Widget assistant immobilier
 * ========================================
 * Installation : colle ce script juste avant </body> sur le site de l'agence.
 *
 * <script
 *   src="https://agenc-ai.com/widget/sarah-widget.js"
 *   data-agency="nom-agence-slug"
 *   data-name="Nom complet de l'agence">
 * </script>
 */
(function () {
  const API_URL = "https://agenc-ai.com/thee-api"; // route backend (inchangée côté serveur)
  const scriptTag = document.currentScript;
  const agencyId = scriptTag?.dataset?.agency || "default";
  const agencyName = scriptTag?.dataset?.name || "notre agence";
  const primaryColor = scriptTag?.dataset?.color || "#1a56db";
  const sessionId = "sarah_" + Date.now() + "_" + Math.random().toString(36).slice(2, 9);

  // ── Styles ─────────────────────────────────────────────────────────────────
  const css = `
    #sarah-chat-btn {
      position: fixed; bottom: 24px; right: 24px; z-index: 999999;
      width: 60px; height: 60px; border-radius: 50%;
      background: ${primaryColor}; color: #fff; border: none;
      cursor: pointer; box-shadow: 0 4px 16px rgba(0,0,0,.25);
      display: flex; align-items: center; justify-content: center;
      transition: transform .2s;
    }
    #sarah-chat-btn:hover { transform: scale(1.08); }
    #sarah-chat-btn svg { width: 26px; height: 26px; }
    #sarah-chat-badge {
      position: absolute; top: -2px; right: -2px;
      width: 14px; height: 14px; background: #ef4444;
      border-radius: 50%; border: 2px solid #fff;
    }
    #sarah-chat-box {
      position: fixed; bottom: 96px; right: 24px; z-index: 999999;
      width: 370px; max-height: 560px;
      background: #fff; border-radius: 18px;
      box-shadow: 0 8px 40px rgba(0,0,0,.2);
      display: flex; flex-direction: column; overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      transition: opacity .25s ease, transform .25s ease;
    }
    #sarah-chat-box.hidden { opacity: 0; pointer-events: none; transform: translateY(16px) scale(.97); }
    #sarah-chat-header {
      background: ${primaryColor}; color: #fff; padding: 16px 18px;
      display: flex; align-items: center; gap: 10px;
    }
    #sarah-avatar {
      width: 34px; height: 34px; border-radius: 50%; background: rgba(255,255,255,.2);
      display: flex; align-items: center; justify-content: center; flex-shrink: 0; font-size: 16px;
    }
    #sarah-header-text { display: flex; flex-direction: column; gap: 1px; flex: 1; min-width: 0; }
    #sarah-header-text .name { font-weight: 600; font-size: 14px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    #sarah-header-text .status { font-size: 11px; opacity: .8; display: flex; align-items: center; gap: 4px; }
    #sarah-header-text .status::before { content: ''; width: 6px; height: 6px; background: #4ade80; border-radius: 50%; }
    #sarah-close-btn { background: none; border: none; color: #fff; opacity: .7; cursor: pointer; font-size: 18px; padding: 4px; }
    #sarah-close-btn:hover { opacity: 1; }
    #sarah-chat-messages {
      flex: 1; overflow-y: auto; padding: 18px; display: flex;
      flex-direction: column; gap: 11px; background: #f8f9fb;
    }
    .sarah-msg {
      max-width: 84%; padding: 11px 15px; border-radius: 15px;
      font-size: 14px; line-height: 1.5; word-wrap: break-word;
    }
    .sarah-msg.bot {
      align-self: flex-start; background: #fff; color: #1a1a2e;
      border: 1px solid #ececf1; border-bottom-left-radius: 4px;
    }
    .sarah-msg.user {
      align-self: flex-end; background: ${primaryColor}; color: #fff;
      border-bottom-right-radius: 4px;
    }
    .sarah-msg.typing { display: flex; gap: 4px; padding: 14px 16px; align-items: center; }
    .sarah-dot { width: 6px; height: 6px; background: #b0b0bb; border-radius: 50%; animation: sarah-bounce 1.2s infinite; }
    .sarah-dot:nth-child(2) { animation-delay: .15s; }
    .sarah-dot:nth-child(3) { animation-delay: .3s; }
    @keyframes sarah-bounce { 0%,60%,100%{transform:translateY(0)} 30%{transform:translateY(-5px)} }
    #sarah-input-area {
      display: flex; gap: 8px; padding: 14px; border-top: 1px solid #ececf1; background: #fff;
    }
    #sarah-input {
      flex: 1; border: 1px solid #e2e2e8; border-radius: 22px;
      padding: 10px 16px; font-size: 14px; outline: none; font-family: inherit;
    }
    #sarah-input:focus { border-color: ${primaryColor}; }
    #sarah-send-btn {
      background: ${primaryColor}; color: #fff; border: none; border-radius: 50%;
      width: 40px; height: 40px; cursor: pointer; flex-shrink: 0;
      display: flex; align-items: center; justify-content: center; transition: opacity .15s;
    }
    #sarah-send-btn:hover { opacity: .85; }
    #sarah-send-btn:disabled { opacity: .4; cursor: not-allowed; }
    #sarah-branding {
      text-align: center; font-size: 10px; color: #b0b0bb; padding: 6px 0 10px;
      background: #fff;
    }
    @media (max-width: 480px) {
      #sarah-chat-box { width: calc(100vw - 24px); right: 12px; bottom: 86px; max-height: 70vh; }
      #sarah-chat-btn { right: 16px; bottom: 16px; }
    }
  `;
  const styleEl = document.createElement("style");
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  // ── HTML ───────────────────────────────────────────────────────────────────
  const btn = document.createElement("button");
  btn.id = "sarah-chat-btn";
  btn.setAttribute("aria-label", "Ouvrir le chat");
  btn.innerHTML = `
    <svg viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>
    </svg>
    <span id="sarah-chat-badge"></span>
  `;

  const box = document.createElement("div");
  box.id = "sarah-chat-box";
  box.className = "hidden";
  box.innerHTML = `
    <div id="sarah-chat-header">
      <div id="sarah-avatar">🏠</div>
      <div id="sarah-header-text">
        <div class="name">${agencyName}</div>
        <div class="status">En ligne</div>
      </div>
      <button id="sarah-close-btn" aria-label="Fermer">✕</button>
    </div>
    <div id="sarah-chat-messages"></div>
    <div id="sarah-input-area">
      <input id="sarah-input" type="text" placeholder="Écrivez votre message…" autocomplete="off"/>
      <button id="sarah-send-btn" aria-label="Envoyer">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 2 11 13"/><path d="M22 2 15 22l-4-9-9-4 20-7z"/></svg>
      </button>
    </div>
    <div id="sarah-branding">Propulsé par Sarah AI</div>
  `;

  document.body.appendChild(btn);
  document.body.appendChild(box);

  // ── Logique ────────────────────────────────────────────────────────────────
  const messagesEl = box.querySelector("#sarah-chat-messages");
  const input = box.querySelector("#sarah-input");
  const sendBtn = box.querySelector("#sarah-send-btn");
  const closeBtn = box.querySelector("#sarah-close-btn");
  const badge = btn.querySelector("#sarah-chat-badge");
  let isOpen = false;
  let hasGreeted = false;

  function toggleChat(forceOpen) {
    isOpen = forceOpen !== undefined ? forceOpen : !isOpen;
    box.classList.toggle("hidden", !isOpen);
    badge.style.display = isOpen ? "none" : "block";
    if (isOpen && !hasGreeted) {
      hasGreeted = true;
      setTimeout(() => {
        addMessage("bot", `Bonjour ! Je suis Sarah, l'assistante de ${agencyName}. Vous cherchez à acheter, louer, ou vous avez une question sur un bien ? 🏠`);
      }, 400);
    }
    if (isOpen) setTimeout(() => input.focus(), 100);
  }

  function addMessage(role, text) {
    const el = document.createElement("div");
    el.className = `sarah-msg ${role}`;
    el.textContent = text;
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return el;
  }

  function showTyping() {
    const el = document.createElement("div");
    el.className = "sarah-msg bot typing";
    el.innerHTML = `<div class="sarah-dot"></div><div class="sarah-dot"></div><div class="sarah-dot"></div>`;
    messagesEl.appendChild(el);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return el;
  }

  async function sendMessage() {
    const text = input.value.trim();
    if (!text) return;
    input.value = "";
    sendBtn.disabled = true;
    addMessage("user", text);

    const typingEl = showTyping();

    try {
      const res = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: sessionId,
          message: text,
          agency_id: agencyId,
          agency_name: agencyName,
        }),
      });
      const data = await res.json();
      typingEl.remove();
      addMessage("bot", data.reply || "Désolé, je n'ai pas pu traiter votre demande.");
    } catch (err) {
      typingEl.remove();
      addMessage("bot", "Désolé, une erreur est survenue. Vous pouvez réessayer dans un instant.");
    } finally {
      sendBtn.disabled = false;
      input.focus();
    }
  }

  btn.addEventListener("click", () => toggleChat());
  closeBtn.addEventListener("click", () => toggleChat(false));
  sendBtn.addEventListener("click", sendMessage);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") sendMessage();
  });

  // Auto-ouverture après 30s d'inactivité sur la page (optionnel, désactivable)
  if (scriptTag?.dataset?.autoOpen === "true") {
    setTimeout(() => { if (!isOpen) toggleChat(true); }, 30000);
  }
})();
