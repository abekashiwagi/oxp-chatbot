/**
 * LeasingAI Chat Widget — single-screen conversational UI.
 */
(function () {
  'use strict';

  var API_URL = 'http://localhost:8000/chat';
  var HEALTH_URL = 'http://localhost:8000/health';
  var STORAGE_KEY = 'leasingai_conversation';
  var MIN_TYPING_MS = 500;
  var HEALTH_INTERVAL_MS = 10000;

  var GREETING = "Hi I'm ELI+, a virtual leasing agent for The Residences community. I can help with tours, pricing, availability, amenities and the application process. Would you like to book a tour to see the property?";

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
    } catch (e) {}
  }

  function loadState() {
    try {
      var saved = sessionStorage.getItem(STORAGE_KEY);
      if (saved) {
        var data = JSON.parse(saved);
        state.messages = data.messages || [];
        state.conversationId = data.conversationId || null;
      }
    } catch (e) {}
  }

  function buildHTML() {
    var container = document.createElement('div');
    container.id = 'leasing-ai-chat';
    container.innerHTML =
      '<div class="lai-panel">' +
        '<div class="lai-welcome-header">' +
          '<h1 class="lai-welcome-title">Welcome, I\'m ELI</h1>' +
          '<p class="lai-welcome-disclaimer">By using this feature, you accept our <a href="https://legal.entrata.com/prospect-portal-resident-portal-terms" target="_blank" rel="noopener noreferrer" class="lai-link">Terms</a> and our <a href="https://www.entrata.com/privacy-policy" target="_blank" rel="noopener noreferrer" class="lai-link">Privacy Policy</a>, that responses may be AI-generated, and that your conversation will be recorded for AI training.</p>' +
        '</div>' +
        '<div class="lai-messages"></div>' +
        '<div class="lai-composer-wrap">' +
          '<div class="lai-composer">' +
            '<input type="text" class="lai-input" placeholder="Type your message" aria-label="Message">' +
            '<button class="lai-send-btn" aria-label="Send message">' +
              '<svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>' +
            '</button>' +
          '</div>' +
        '</div>' +
        '<div class="lai-footer">' +
          '<svg viewBox="0 0 24 24" width="14" height="14"><rect x="2" y="3" width="20" height="14" rx="2" ry="2" fill="none" stroke="currentColor" stroke-width="2"/><line x1="8" y1="21" x2="16" y2="21" stroke="currentColor" stroke-width="2"/><line x1="12" y1="17" x2="12" y2="21" stroke="currentColor" stroke-width="2"/></svg>' +
          '<span>Powered by <strong>Entrata</strong></span>' +
        '</div>' +
      '</div>' +
      '<button class="lai-fab" aria-label="Open chat">' +
        '<span class="lai-fab-icon-wrap">' +
          '<svg class="lai-icon-chat" viewBox="0 0 24 24" stroke-width="0" fill="white">' +
            '<path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/>' +
          '</svg>' +
        '</span>' +
        '<svg class="lai-icon-close" viewBox="0 0 24 24" stroke="white" stroke-width="2.25" stroke-linecap="round" stroke-linejoin="round">' +
          '<line x1="6" y1="6" x2="18" y2="18"/><line x1="6" y1="18" x2="18" y2="6"/>' +
        '</svg>' +
        '<span class="lai-fab-label">Chat with us</span>' +
        '<span class="lai-unread-dot"></span>' +
      '</button>';

    document.body.appendChild(container);

    els.container = container;
    els.panel = container.querySelector('.lai-panel');
    els.messages = container.querySelector('.lai-messages');
    els.input = container.querySelector('.lai-input');
    els.sendBtn = container.querySelector('.lai-send-btn');
    els.fab = container.querySelector('.lai-fab');
  }

  function bindEvents() {
    els.fab.addEventListener('click', toggleChat);
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

  function addBotBubble(content) {
    var bubble = document.createElement('div');
    bubble.className = 'lai-bubble lai-bubble-bot';
    bubble.innerHTML = renderMarkdown(content);
    els.messages.appendChild(bubble);
    scrollToBottom();
  }

  function addUserBubble(content) {
    var bubble = document.createElement('div');
    bubble.className = 'lai-bubble lai-bubble-user';
    bubble.textContent = content;
    els.messages.appendChild(bubble);
    scrollToBottom();
  }

  function addMessage(role, content) {
    var msg = { role: role, content: content, timestamp: new Date().toISOString() };
    state.messages.push(msg);
    saveState();

    if (role === 'user') {
      addUserBubble(content);
    } else if (role === 'assistant') {
      addBotBubble(content);
    } else {
      var sys = document.createElement('div');
      sys.className = 'lai-bubble lai-bubble-system';
      sys.textContent = content;
      els.messages.appendChild(sys);
      scrollToBottom();
    }
  }

  function renderAllMessages() {
    els.messages.innerHTML = '';
    addBotBubble(GREETING);
    state.messages.forEach(function (msg) {
      if (msg.role === 'user') addUserBubble(msg.content);
      else if (msg.role === 'assistant') addBotBubble(msg.content);
    });
    scrollToBottom();
  }

  function showTyping() {
    var row = document.createElement('div');
    row.className = 'lai-typing';
    row.id = 'lai-typing-indicator';
    row.innerHTML = '<div class="lai-typing-dots"><div class="lai-typing-dot"></div><div class="lai-typing-dot"></div><div class="lai-typing-dot"></div></div>';
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
        }, remaining);
      });
  }

  function checkHealth() {
    fetch(HEALTH_URL, { method: 'GET' })
      .then(function (res) { return res.ok; })
      .catch(function () { return false; })
      .then(function (ok) {
        state.health = ok;
      });
  }

  function init() {
    loadState();
    buildHTML();
    bindEvents();

    addBotBubble(GREETING);
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
