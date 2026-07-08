/**
 * LeasingAI Chat Widget — matches leasing-ai-ui production design.
 *
 * White header, "Leasing Agent" title, health dot, new-conversation
 * button, avatar bubbles, "Powered by Entrata" footer. No welcome
 * message, no quick replies — prospect types first.
 */
(function () {
  'use strict';

  var API_URL = 'http://localhost:8000/chat';
  var HEALTH_URL = 'http://localhost:8000/health';
  var STORAGE_KEY = 'leasingai_conversation';
  var MIN_TYPING_MS = 500;
  var HEALTH_INTERVAL_MS = 10000;

  var state = {
    open: false,
    messages: [],
    conversationId: null,
    waiting: false,
    health: null,
    hasUnread: false,
  };

  var els = {};
  var healthTimer = null;

  function generateId() {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function (c) {
      var r = (Math.random() * 16) | 0;
      var v = c === 'x' ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  }

  function formatRelative(iso) {
    var now = Date.now();
    var then = new Date(iso).getTime();
    var diff = Math.floor((now - then) / 1000);
    if (diff < 60) return 'just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    return new Date(iso).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  }

  function escapeHTML(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  function renderMarkdown(text) {
    var html = escapeHTML(text);

    html = html.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/(?<!\*)\*([^*]+?)\*(?!\*)/g, '<em>$1</em>');
    html = html.replace(/`([^`]+?)`/g, '<code>$1</code>');
    html = html.replace(/\[([^\]]+)\]\((https?:\/\/[^\)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>');

    var lines = html.split('\n');
    var result = [];
    var inUl = false;
    var inOl = false;

    for (var i = 0; i < lines.length; i++) {
      var line = lines[i];
      var bulletMatch = line.match(/^\s*[-*]\s+(.+)/);
      var orderedMatch = line.match(/^\s*\d+\.\s+(.+)/);

      if (bulletMatch) {
        if (inOl) { result.push('</ol>'); inOl = false; }
        if (!inUl) { result.push('<ul>'); inUl = true; }
        result.push('<li>' + bulletMatch[1] + '</li>');
      } else if (orderedMatch) {
        if (inUl) { result.push('</ul>'); inUl = false; }
        if (!inOl) { result.push('<ol>'); inOl = true; }
        result.push('<li>' + orderedMatch[1] + '</li>');
      } else {
        if (inUl) { result.push('</ul>'); inUl = false; }
        if (inOl) { result.push('</ol>'); inOl = false; }
        if (line.trim() === '') {
          result.push('<br>');
        } else {
          result.push('<p>' + line + '</p>');
        }
      }
    }
    if (inUl) result.push('</ul>');
    if (inOl) result.push('</ol>');

    return result.join('');
  }

  function saveState() {
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify({
        messages: state.messages,
        conversationId: state.conversationId,
      }));
    } catch (e) { /* private browsing */ }
  }

  function loadState() {
    try {
      var saved = sessionStorage.getItem(STORAGE_KEY);
      if (saved) {
        var data = JSON.parse(saved);
        state.messages = data.messages || [];
        state.conversationId = data.conversationId || null;
      }
    } catch (e) { /* corrupted */ }
  }

  function buildHTML() {
    var container = document.createElement('div');
    container.id = 'leasing-ai-chat';
    container.innerHTML =
      '<div class="lai-panel">' +
        '<div class="lai-header">' +
          '<button class="lai-header-back" aria-label="Close chat">' +
            '<svg viewBox="0 0 24 24"><polyline points="15 18 9 12 15 6"/></svg>' +
          '</button>' +
          '<div class="lai-header-info">' +
            '<div class="lai-header-title">Leasing Agent</div>' +
            '<div class="lai-header-subtitle">Typically replies in a few minutes</div>' +
          '</div>' +
          '<button class="lai-header-new" aria-label="Start new conversation" title="Start new conversation">' +
            '<svg viewBox="0 0 24 24"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4 12.5-12.5z"/></svg>' +
          '</button>' +
          '<span class="lai-health" title="Agent: Checking">' +
            '<span class="lai-health-dot lai-checking"></span>' +
            '<span class="lai-health-label">Checking</span>' +
          '</span>' +
        '</div>' +
        '<div class="lai-messages"></div>' +
        '<div class="lai-composer-wrap">' +
          '<div class="lai-composer">' +
            '<input type="text" class="lai-input" placeholder="Ask Leasing AI anything..." aria-label="Message">' +
            '<button class="lai-send-btn" aria-label="Send message">' +
              '<svg viewBox="0 0 16 16"><path d="M14.5 8 2 14l2.5-6L2 2l12.5 6Z"/></svg>' +
            '</button>' +
          '</div>' +
        '</div>' +
        '<div class="lai-footer">' +
          '<svg viewBox="0 0 24 24"><path d="M13 2 4 14h7l-1 8 9-12h-7l1-8z"/></svg>' +
          '<span>Powered by <strong>Entrata</strong></span>' +
        '</div>' +
      '</div>' +
      '<button class="lai-fab" aria-label="Open chat">' +
        '<svg class="lai-icon-chat" viewBox="0 0 24 24" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">' +
          '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>' +
        '</svg>' +
        '<svg class="lai-icon-close" viewBox="0 0 24 24" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round">' +
          '<line x1="6" y1="6" x2="18" y2="18"/><line x1="6" y1="18" x2="18" y2="6"/>' +
        '</svg>' +
        '<span class="lai-unread-dot"></span>' +
      '</button>';

    document.body.appendChild(container);

    els.container = container;
    els.panel = container.querySelector('.lai-panel');
    els.messages = container.querySelector('.lai-messages');
    els.input = container.querySelector('.lai-input');
    els.sendBtn = container.querySelector('.lai-send-btn');
    els.fab = container.querySelector('.lai-fab');
    els.backBtn = container.querySelector('.lai-header-back');
    els.newBtn = container.querySelector('.lai-header-new');
    els.healthDot = container.querySelector('.lai-health-dot');
    els.healthLabel = container.querySelector('.lai-health-label');
  }

  function bindEvents() {
    els.fab.addEventListener('click', toggleChat);
    els.backBtn.addEventListener('click', closeChat);
    els.newBtn.addEventListener('click', handleNewConversation);
    els.sendBtn.addEventListener('click', handleSend);
    els.input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && state.open) closeChat();
    });
  }

  function toggleChat() {
    state.open ? closeChat() : openChat();
  }

  function openChat() {
    state.open = true;
    state.hasUnread = false;
    els.container.classList.add('lai-open');
    els.container.classList.remove('lai-has-unread');
    setTimeout(function () { els.input.focus(); }, 200);
  }

  function closeChat() {
    state.open = false;
    els.container.classList.remove('lai-open');
  }

  function handleNewConversation() {
    if (state.waiting) return;
    var hasUserActivity = state.messages.some(function (m) { return m.role === 'user'; });
    if (hasUserActivity) {
      if (!window.confirm('Start a new conversation? Your current chat will be cleared.')) return;
    }
    state.messages = [];
    state.conversationId = null;
    saveState();
    els.messages.innerHTML = '';
  }

  function addMessage(role, content) {
    var msg = { role: role, content: content, timestamp: new Date().toISOString() };
    state.messages.push(msg);
    saveState();
    renderMessage(msg);
    scrollToBottom();
  }

  function renderMessage(msg) {
    if (msg.role === 'system') {
      var sys = document.createElement('div');
      sys.className = 'lai-msg-system';
      sys.innerHTML = '<div class="lai-msg-system-pill ' + (msg.error ? 'lai-error' : 'lai-info') + '">' + escapeHTML(msg.content) + '</div>';
      els.messages.appendChild(sys);
      return;
    }

    var isUser = msg.role === 'user';
    var row = document.createElement('div');
    row.className = 'lai-msg ' + (isUser ? 'lai-msg-user' : 'lai-msg-bot');

    var avatar = '<div class="lai-avatar ' + (isUser ? 'lai-avatar-user' : 'lai-avatar-agent') + '">' + (isUser ? 'Y' : 'L') + '</div>';
    var label = isUser ? '' : '<div class="lai-msg-label">Leasing AI <span>- Leasing Agent</span></div>';
    var bubble = '<div class="lai-msg-bubble">' + (isUser ? escapeHTML(msg.content) : renderMarkdown(msg.content)) + '</div>';
    var timeStr = formatRelative(msg.timestamp);
    var sent = isUser ? '<span class="lai-msg-sent">Sent</span>' : '';
    var time = '<div class="lai-msg-time">' + timeStr + sent + '</div>';

    if (isUser) {
      row.innerHTML = '<div class="lai-msg-col">' + bubble + time + '</div>' + avatar;
    } else {
      row.innerHTML = avatar + '<div class="lai-msg-col">' + label + bubble + time + '</div>';
    }

    els.messages.appendChild(row);
  }

  function renderAllMessages() {
    els.messages.innerHTML = '';
    state.messages.forEach(renderMessage);
    scrollToBottom();
  }

  function showTyping() {
    var row = document.createElement('div');
    row.className = 'lai-typing';
    row.id = 'lai-typing-indicator';
    row.innerHTML =
      '<div class="lai-avatar lai-avatar-agent">L</div>' +
      '<div class="lai-typing-dots"><div class="lai-typing-dot"></div><div class="lai-typing-dot"></div><div class="lai-typing-dot"></div></div>';
    els.messages.appendChild(row);
    scrollToBottom();
  }

  function hideTyping() {
    var el = document.getElementById('lai-typing-indicator');
    if (el) el.remove();
  }

  function setWaiting(w) {
    state.waiting = w;
    els.input.disabled = w;
    els.sendBtn.disabled = w;
    els.newBtn.disabled = w;
  }

  function scrollToBottom() {
    requestAnimationFrame(function () {
      els.messages.scrollTop = els.messages.scrollHeight;
    });
  }

  function handleSend() {
    var text = els.input.value.trim();
    if (!text || state.waiting) return;
    els.input.value = '';
    sendMessage(text);
  }

  function sendMessage(text) {
    addMessage('user', text);

    if (!state.conversationId) {
      state.conversationId = generateId();
      saveState();
    }

    setWaiting(true);
    showTyping();

    var startTime = Date.now();
    var payload = {
      message: text,
      conversation_id: state.conversationId,
      property_id: window.PROPERTY_ID || null,
      messages: state.messages.map(function (m) {
        return { role: m.role, content: m.content };
      }),
    };

    fetch(API_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    })
      .then(function (res) {
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.json();
      })
      .then(function (data) {
        var elapsed = Date.now() - startTime;
        var remaining = Math.max(0, MIN_TYPING_MS - elapsed);
        setTimeout(function () {
          hideTyping();
          setWaiting(false);
          if (data.conversation_id) state.conversationId = data.conversation_id;
          addMessage('assistant', data.response);
          if (!state.open) {
            state.hasUnread = true;
            els.container.classList.add('lai-has-unread');
          }
        }, remaining);
      })
      .catch(function () {
        var elapsed = Date.now() - startTime;
        var remaining = Math.max(0, MIN_TYPING_MS - elapsed);
        setTimeout(function () {
          hideTyping();
          setWaiting(false);
          addMessage('system', 'Sorry, I had trouble reaching the leasing system. Please try again.');
          state.messages[state.messages.length - 1].error = true;
        }, remaining);
      });
  }

  function checkHealth() {
    fetch(HEALTH_URL, { method: 'GET' })
      .then(function (res) { return res.ok; })
      .catch(function () { return false; })
      .then(function (ok) {
        state.health = ok;
        els.healthDot.className = 'lai-health-dot' + (ok ? '' : ' lai-offline');
        els.healthLabel.textContent = ok ? 'Online' : 'Offline';
        els.healthDot.parentElement.title = 'Agent: ' + (ok ? 'Online' : 'Offline');
      });
  }

  function init() {
    loadState();
    buildHTML();
    bindEvents();

    if (state.messages.length > 0) {
      renderAllMessages();
    }

    checkHealth();
    healthTimer = setInterval(checkHealth, HEALTH_INTERVAL_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
