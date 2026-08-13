/* =========================================================
   BIM-CHATBOT  –  script.js
   ========================================================= */

(function () {
  'use strict';

  // ── DOM refs ──────────────────────────────────────────────
  const html         = document.documentElement;
  const modeToggle   = document.getElementById('modeToggle');
  const sendBtn      = document.getElementById('sendBtn');
  const chatInput    = document.getElementById('chatInput');
  const messageFeed  = document.getElementById('messageFeed');
  const typingInd    = document.getElementById('typingIndicator');
  const newChatBtn   = document.getElementById('newChatBtn');
  const historyList  = document.getElementById('historyList');
  const historyEmpty = document.getElementById('historyEmpty');
  const saveChatBtn  = document.getElementById('saveChatBtn');
  const saveChatInput= document.getElementById('saveChatInput');
  const eventsCard   = document.getElementById('eventsCardBtn');
  const menuBtn      = document.getElementById('menuBtn');
  const dotMenu      = document.getElementById('dotMenu');
  const exportChat   = document.getElementById('exportChat');
  const clearHistory = document.getElementById('clearHistory');
  const aboutBot     = document.getElementById('aboutBot');

  // ── State ─────────────────────────────────────────────────
  let chatSessions = [];
  let currentSessionId = null;
  let messageIdCounter = 100;

  // Bot reply stubs – cycled for demo purposes
  const botReplies = [
    "I've searched the BIM knowledge base and found relevant information for your query. Could you provide more context so I can give you a precise answer?",
    "Based on the documents available, here's what I found regarding your question. BIM standards in Barbados align with international best practices while incorporating local specifications.",
    "Great question! The Barbados Information Management framework covers this topic in section 4.2. Would you like me to retrieve the full document excerpt?",
    "I'm processing your request through the document retrieval system. This query relates to infrastructure compliance regulations — let me summarise the key points.",
    "According to the indexed knowledge base, there are three relevant provisions. Shall I walk you through each one in detail?",
    "Noted! I'll cross-reference this with the latest Barbados building standards and local government directives. One moment…",
  ];
  let replyIndex = 0;

  // ── Dark / Light Mode Toggle ──────────────────────────────
  function applyMode(mode) {
    html.classList.remove('light-mode', 'dark-mode');
    html.classList.add(mode);
    localStorage.setItem('bim-theme', mode);
    modeToggle.textContent = mode === 'dark-mode' ? '☀ LIGHT MODE' : '🌙 DARK MODE';
  }

  // Load saved preference
  const savedTheme = localStorage.getItem('bim-theme') || 'light-mode';
  applyMode(savedTheme);

  modeToggle.addEventListener('click', () => {
    const next = html.classList.contains('dark-mode') ? 'light-mode' : 'dark-mode';
    applyMode(next);
  });

  // ── Dot Menu ──────────────────────────────────────────────
  menuBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    dotMenu.classList.toggle('open');
  });

  document.addEventListener('click', () => dotMenu.classList.remove('open'));

  exportChat.addEventListener('click', () => {
    dotMenu.classList.remove('open');
    exportCurrentChat();
  });

  clearHistory.addEventListener('click', () => {
    dotMenu.classList.remove('open');
    if (confirm('Clear all chat history?')) {
      chatSessions = [];
      currentSessionId = null;
      renderHistoryList();
      clearMessageFeed();
    }
  });

  aboutBot.addEventListener('click', () => {
    dotMenu.classList.remove('open');
    addBotMessage("BIM-CHATBOT v1.0 — Powered by document retrieval AI. Built for Barbados Information Management. © 2025 BIM Team.");
  });

  // ── Messaging ─────────────────────────────────────────────
  function sendMessage() {
    const text = chatInput.value.trim();
    if (!text) return;

    ensureActiveSession();

    addUserMessage(text);
    chatInput.value = '';
    chatInput.focus();

    // Save to session
    getCurrentSession().messages.push({ role: 'user', text, id: ++messageIdCounter });

    // Show typing
    showTyping();

    // Simulate async bot response
    const delay = 900 + Math.random() * 800;
    setTimeout(() => {
      hideTyping();
      const reply = botReplies[replyIndex % botReplies.length];
      replyIndex++;
      addBotMessage(reply);
      getCurrentSession().messages.push({ role: 'bot', text: reply, id: ++messageIdCounter });
    }, delay);
  }

  sendBtn.addEventListener('click', sendMessage);

  chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });

  function addUserMessage(text) {
    const el = createMessageEl('user', text);
    messageFeed.appendChild(el);
    scrollToBottom();
  }

  function addBotMessage(text) {
    const el = createMessageEl('bot', text);
    messageFeed.appendChild(el);
    scrollToBottom();
  }

  function createMessageEl(role, text) {
    const wrapper = document.createElement('div');
    wrapper.className = `message ${role === 'bot' ? 'bot-message' : 'user-message'}`;

    const avatar = document.createElement('div');
    avatar.className = `avatar ${role === 'bot' ? 'bot-avatar' : 'user-avatar'}`;
    avatar.textContent = role === 'bot' ? 'B' : 'U';

    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.textContent = text;

    wrapper.appendChild(avatar);
    wrapper.appendChild(bubble);
    return wrapper;
  }

  function showTyping() {
    typingInd.style.display = 'flex';
    scrollToBottom();
  }

  function hideTyping() {
    typingInd.style.display = 'none';
  }

  function scrollToBottom() {
    requestAnimationFrame(() => {
      messageFeed.scrollTop = messageFeed.scrollHeight;
    });
  }

  function clearMessageFeed() {
    messageFeed.innerHTML = '';
  }

  // ── Sessions / History ────────────────────────────────────
  function getCurrentSession() {
    return chatSessions.find(s => s.id === currentSessionId) || null;
  }

  function ensureActiveSession() {
    if (currentSessionId && getCurrentSession()) return;
    const newSession = {
      id: Date.now(),
      name: `Chat ${chatSessions.length + 1}`,
      messages: [],
    };
    chatSessions.unshift(newSession);
    currentSessionId = newSession.id;
    renderHistoryList();
  }

  function renderHistoryList() {
    historyList.innerHTML = '';
    historyEmpty.style.display = chatSessions.length ? 'none' : 'block';
    chatSessions.forEach(session => {
      const li = document.createElement('li');
      li.className = `history-item${session.id === currentSessionId ? ' active' : ''}`;
      li.textContent = session.name;
      li.dataset.id = session.id;
      li.addEventListener('click', () => switchSession(session.id));
      historyList.appendChild(li);
    });
  }

  function switchSession(id) {
    currentSessionId = id;
    clearMessageFeed();
    const session = getCurrentSession();
    if (session && session.messages.length > 0) {
      session.messages.forEach(m => {
        if (m.role === 'user') addUserMessage(m.text);
        else addBotMessage(m.text);
      });
    }
    renderHistoryList();
    scrollToBottom();
  }

  newChatBtn.addEventListener('click', () => {
    const newSession = {
      id: Date.now(),
      name: `Chat ${chatSessions.length + 1}`,
      messages: [],
    };
    chatSessions.unshift(newSession);
    currentSessionId = newSession.id;
    clearMessageFeed();
    renderHistoryList();
    chatInput.focus();
  });

  // ── Save Chat ─────────────────────────────────────────────
  saveChatBtn.addEventListener('click', () => {
    const name = saveChatInput.value.trim();
    if (!name) { saveChatInput.focus(); return; }

    const session = getCurrentSession();
    if (!session) {
      saveChatInput.focus();
      return;
    }
    session.name = name;
    saveChatInput.value = '';
    renderHistoryList();

    // Brief visual feedback
    saveChatBtn.textContent = 'Saved ✓';
    saveChatBtn.style.color = '#f3c614';
    setTimeout(() => {
      saveChatBtn.textContent = '💾 Save Chat';
      saveChatBtn.style.color = '';
    }, 1800);
  });

  // ── Events Card ───────────────────────────────────────────
  eventsCard.addEventListener('click', () => {
    addBotMessage("Here are some upcoming Barbados events! Crop Over Festival (July–August), Holetown Festival (February), Independence Day Celebrations (November 30), and the Barbados Food & Rum Festival (October). Would you like more details on any of these?");
  });

  // ── Export Chat ───────────────────────────────────────────
  function exportCurrentChat() {
    const session = getCurrentSession();
    if (!session) {
      alert('No active chat to export yet.');
      return;
    }
    if (session.messages.length === 0) {
      alert('No messages to export in this session.');
      return;
    }
    const lines = session.messages.map(m => `[${m.role.toUpperCase()}]: ${m.text}`);
    const blob = new Blob([lines.join('\n\n')], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${session.name.replace(/\s+/g, '_')}_export.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // Initial state render
  renderHistoryList();

})();
