// forge-chat.js — Phase 16 (FB-D) chat panel client.
// D-02/D-03: messages list both ways. D-06: per-tab JS state.
// D-07: tool-call transparency (collapsed <details>).
// D-09: error banner copy. D-10: Enter sends, Shift+Enter newline.
// D-11: escape-first markdown renderer (no new dep).

(function () {
  "use strict";

  // ----- Markdown renderer (D-11) -----------------------------------------
  // Security order: HTML-escape FIRST, THEN re-render specific patterns.
  // Reject javascript:, data:, and any other non-http(s) URL scheme.

  function escapeHtml(s) {
    return s
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function renderMarkdown(rawText) {
    if (typeof rawText !== "string") return "";

    // Step 1 — escape the entire string.
    let html = escapeHtml(rawText);

    // Step 2 — re-render fenced code blocks ```...```
    // Match across newlines; keep monospace, do not re-render anything inside.
    html = html.replace(
      /```([\s\S]*?)```/g,
      (_, body) => `<pre class="chat-code"><code>${body}</code></pre>`
    );

    // Step 3 — re-render inline code `...`
    html = html.replace(
      /`([^`\n]+)`/g,
      (_, body) => `<code class="chat-inline-code">${body}</code>`
    );

    // Step 4 — re-render bold **...**
    html = html.replace(
      /\*\*([^\n*]+)\*\*/g,
      (_, body) => `<strong>${body}</strong>`
    );

    // Step 5 — re-render http(s)-only links [label](url)
    // Reject any URL that does not start with http:// or https://
    html = html.replace(
      /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
      (_, label, url) =>
        `<a href="${url}" rel="noopener noreferrer" target="_blank">${label}</a>`
    );

    // Step 6 — preserve newlines as <br> for plain text
    html = html.replace(/\n/g, "<br>");

    return html;
  }

  // ----- Alpine factory ---------------------------------------------------

  function chatPanel() {
    return {
      messages: [],   // [{id, role, content, toolPreview?}]
      draft: "",
      inflight: false,
      error: "",

      init() {
        // D-06 per-tab: nothing to restore. Cleared on tab close.
      },

      // For Alpine class binding on each message bubble.
      messageClass(msg) {
        const base = "chat-message";
        const role = msg && msg.role;
        if (role === "user")      return base + " chat-message--user";
        if (role === "assistant") return base + " chat-message--assistant";
        if (role === "tool")      return base + " chat-message--tool";
        return base;
      },

      // Hide system messages from display, surface user/assistant/tool only.
      renderableMessages() {
        return this.messages.filter(
          (m) => m && (m.role === "user" || m.role === "assistant" || m.role === "tool")
        );
      },

      // Wire-up for the assistant content x-html — escape-first markdown.
      renderContent(content) {
        return renderMarkdown(content);
      },

      // D-10: Enter sends, Shift+Enter inserts newline.
      onEnter(ev) {
        if (ev.shiftKey) {
          // Allow default newline insertion.
          return;
        }
        ev.preventDefault();
        this.send();
      },

      // POST /api/v1/chat — D-02 wire shape.
      async send() {
        const draft = this.draft.trim();
        if (!draft || this.inflight) return;

        const userMsg = {
          id: (crypto.randomUUID && crypto.randomUUID()) || String(Date.now()),
          role: "user",
          content: draft,
        };
        this.messages.push(userMsg);
        this.draft = "";
        this.inflight = true;
        this.error = "";

        // Build the wire payload — strip client-side ids so the server
        // contract stays {role, content, tool_call_id?}.
        const wireMessages = this.messages.map((m) => {
          const out = { role: m.role, content: m.content };
          if (m.tool_call_id) out.tool_call_id = m.tool_call_id;
          return out;
        });

        try {
          const r = await fetch("/api/v1/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ messages: wireMessages }),
          });
          let body;
          try {
            body = await r.json();
          } catch (_e) {
            body = {};
          }

          if (r.status === 429) {
            // D-09: prescribed copy. Server already includes Retry-After.
            const ra = r.headers.get("Retry-After") || "?";
            this.error = (body && body.error && body.error.message) ||
              `Rate limit reached — wait ${ra}s before retrying.`;
          } else if (r.status === 504) {
            this.error = "Response timed out — try a simpler question or fewer tools.";
          } else if (r.status === 422) {
            const msg = (body && body.error && body.error.message) || "validation error";
            this.error = "Invalid request — " + msg;
          } else if (!r.ok) {
            this.error = "Chat error — check console for details.";
          } else {
            // D-03 success — replace local state with the echoed history.
            // Stamp client-side ids so Alpine's :key tracker is stable.
            this.messages = (body.messages || []).map((m, i) => ({
              id: i + ":" + ((crypto.randomUUID && crypto.randomUUID()) || String(Date.now() + i)),
              role: m.role,
              content: m.content,
              tool_call_id: m.tool_call_id,
            }));
          }
        } catch (e) {
          this.error = "Chat error — check console for details.";
        } finally {
          this.inflight = false;
        }
      },
    };
  }

  // Expose the factory globally so Alpine x-data="chatPanel()" can call it.
  window.chatPanel = chatPanel;
})();
