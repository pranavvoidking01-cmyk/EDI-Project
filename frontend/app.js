const navTabs = document.querySelectorAll('.nav-tab');
const views = document.querySelectorAll('.view');
const chatList = document.querySelector('#chat-list');
const chatWindow = document.querySelector('#chat-window');
const messageForm = document.querySelector('#message-form');
const messageInput = document.querySelector('#message-input');
const sendButton = document.querySelector('#send-btn');
const muteToggle = document.querySelector('#mute-toggle');
const toastContainer = document.querySelector('#toast-container');
const taskForm = document.querySelector('#task-form');
const taskList = document.querySelector('#task-list');
const taskFilter = document.querySelector('#task-filter');
const vaultTableBody = document.querySelector('#audit-log-body');
const currentUserId = 1;
const chats = [
  { id: 1, name: 'EDI Project', meta: '10 members', initials: 'EP', avatar: 'avatar-green' },
  { id: 2, name: 'Design Review', meta: '8 members', initials: 'DR', avatar: 'avatar-blue' },
  { id: 3, name: 'Study Circle', meta: '14 members', initials: 'SC', avatar: 'avatar-yellow' },
  { id: 4, name: 'Launch Operations', meta: '6 members', initials: 'LO', avatar: 'avatar-pink' },
  { id: 5, name: 'Campus Community', meta: '24 members', initials: 'CC', avatar: 'avatar-purple' }
];
let activeGroupId = 1;
let groupMuted = false;
let editingMessageId = null;
let knownMessageIds = new Set();
let initialMessagesLoaded = false;
let cachedTasks = [];

const formatDate = (value) => value ? new Intl.DateTimeFormat([], { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value)) : 'No deadline';
const formatDateTime = (value) => value ? new Intl.DateTimeFormat([], { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(new Date(value)) : 'Unknown';
const cleanAlert = (content) => content.replace(/^\[NLP-ALERT\]\s*/, '');

function showToast(title, detail) {
  const toast = document.createElement('div');
  toast.className = 'alert-toast';
  const heading = document.createElement('strong');
  heading.textContent = title;
  const body = document.createElement('span');
  body.textContent = detail;
  toast.append(heading, body);
  toastContainer.append(toast);
  window.setTimeout(() => toast.remove(), 5500);
}

function switchView(viewId) {
  navTabs.forEach((tab) => tab.classList.toggle('active', tab.dataset.view === viewId));
  views.forEach((view) => { view.hidden = view.id !== viewId; view.classList.toggle('active-view', view.id === viewId); });
  if (viewId === 'messages-view') fetchMessages(activeGroupId);
  if (viewId === 'tasks-view') fetchTasks();
  if (viewId === 'vault-view') fetchLogs();
}
navTabs.forEach((tab) => tab.addEventListener('click', () => switchView(tab.dataset.view)));

function renderChatList() {
  chatList.replaceChildren();
  chats.forEach((chat) => {
    const button = document.createElement('button');
    button.className = `chat-item${chat.id === activeGroupId ? ' active' : ''}`;
    button.dataset.groupId = chat.id;
    button.innerHTML = `<span class="avatar ${chat.avatar}">${chat.initials}</span><span class="chat-item-copy"><strong>${chat.name}</strong><small>${chat.meta} · live</small></span><span class="unread">${String(chat.id).padStart(2, '0')}</span>`;
    button.addEventListener('click', () => {
      activeGroupId = chat.id;
      knownMessageIds = new Set();
      initialMessagesLoaded = false;
      document.querySelector('#active-chat-name').textContent = chat.name;
      document.querySelector('#active-channel-id').textContent = String(chat.id).padStart(2, '0');
      renderChatList();
      chatWindow.replaceChildren();
      const loading = document.createElement('div');
      loading.className = 'empty-state';
      loading.textContent = 'Loading channel...';
      chatWindow.append(loading);
      fetchMessages(activeGroupId);
    });
    chatList.append(button);
  });
}

function resetComposer() {
  editingMessageId = null;
  messageInput.value = '';
  sendButton.innerHTML = 'Send <span>↗</span>';
}

function renderMessages(messages) {
  const newAlerts = messages.filter((message) => message.content.startsWith('[NLP-ALERT]') && !knownMessageIds.has(message.id));
  if (initialMessagesLoaded) newAlerts.forEach((message) => showToast('Priority alert', cleanAlert(message.content)));
  chatWindow.replaceChildren();
  if (!messages.length) {
    const empty = document.createElement('div');
    empty.className = 'empty-state';
    empty.textContent = 'No messages in this channel yet.';
    chatWindow.append(empty);
  }
  messages.forEach((message) => {
    const article = document.createElement('article');
    const isMine = message.sender_id === currentUserId;
    const isAlert = message.content.startsWith('[NLP-ALERT]');
    article.className = `message${isMine ? ' mine' : ''}${isAlert ? ' nlp-alert' : ''}`;
    article.dataset.messageId = message.id;
    const bubble = document.createElement('div');
    bubble.className = 'message-bubble';
    bubble.textContent = cleanAlert(message.content);
    const timestamp = document.createElement('time');
    timestamp.className = 'message-meta';
    timestamp.textContent = formatDateTime(message.timestamp);
    article.append(bubble, timestamp);
    if (isMine) {
      const actions = document.createElement('div');
      actions.className = 'message-actions';
      const edit = document.createElement('button');
      edit.type = 'button'; edit.textContent = 'Edit';
      edit.addEventListener('click', () => { editingMessageId = message.id; messageInput.value = cleanAlert(message.content); sendButton.textContent = 'Update'; messageInput.focus(); });
      const remove = document.createElement('button');
      remove.type = 'button'; remove.textContent = 'Delete';
      remove.addEventListener('click', async () => {
        const response = await fetch(`/api/messages/${message.id}`, { method: 'DELETE' });
        if (!response.ok) return showToast('Action failed', 'Message could not be deleted.');
        article.remove();
      });
      actions.append(edit, remove);
      article.append(actions);
    }
    chatWindow.append(article);
  });
  knownMessageIds = new Set(messages.map((message) => message.id));
  initialMessagesLoaded = true;
  document.querySelector('#message-total').textContent = messages.length;
  chatWindow.scrollTop = chatWindow.scrollHeight;
}

async function fetchMessages(groupId = activeGroupId) {
  try {
    const response = await fetch(`/api/messages?group_id=${groupId}`);
    if (!response.ok) throw new Error('Message request failed');
    renderMessages(await response.json());
  } catch (error) {
    chatWindow.innerHTML = '<div class="empty-state">Message service unavailable.</div>';
    console.error(error);
  }
}

messageForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const content = messageInput.value.trim();
  if (!content) return;
  sendButton.disabled = true;
  const editing = editingMessageId !== null;
  try {
    const response = await fetch(editing ? `/api/messages/${editingMessageId}` : '/api/messages', {
      method: editing ? 'PUT' : 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(editing ? { content } : { group_id: activeGroupId, sender_id: currentUserId, content, group_muted: groupMuted })
    });
    if (!response.ok) throw new Error('Message save failed');
    resetComposer();
    await fetchMessages();
  } catch (error) { showToast('Message error', 'Your message could not be saved.'); console.error(error); }
  finally { sendButton.disabled = false; messageInput.focus(); }
});
muteToggle.addEventListener('click', () => {
  groupMuted = !groupMuted;
  muteToggle.setAttribute('aria-pressed', String(groupMuted));
  muteToggle.textContent = groupMuted ? 'Unmute' : 'Mute';
});

function renderTasks() {
  const selected = taskFilter.value;
  const tasks = selected === 'all' ? cachedTasks : cachedTasks.filter((task) => task.status === selected);
  taskList.replaceChildren();
  if (!tasks.length) { taskList.innerHTML = '<div class="empty-state">No tasks match this view.</div>'; return; }
  tasks.forEach((task) => {
    const row = document.createElement('article'); row.className = 'task-row';
    const checkbox = document.createElement('input'); checkbox.type = 'checkbox'; checkbox.className = 'task-check'; checkbox.checked = task.status === 'done';
    checkbox.addEventListener('change', () => saveTask({ ...task, status: checkbox.checked ? 'done' : 'todo' }));
    const description = document.createElement('span'); description.className = `task-description${task.status === 'done' ? ' done' : ''}`; description.textContent = task.description;
    const deadline = document.createElement('time'); deadline.className = 'task-deadline'; deadline.textContent = formatDate(task.deadline);
    const status = document.createElement('span'); status.className = `task-status status-${task.status}`; status.textContent = task.status.replace('-', ' ');
    const actions = document.createElement('div'); actions.className = 'task-actions';
    const edit = document.createElement('button'); edit.type = 'button'; edit.textContent = 'Edit'; edit.addEventListener('click', () => editTask(task));
    const remove = document.createElement('button'); remove.type = 'button'; remove.textContent = 'Delete'; remove.addEventListener('click', () => removeTask(task.id));
    actions.append(edit, remove); row.append(checkbox, description, deadline, status, actions); taskList.append(row);
  });
  document.querySelector('#task-total').textContent = cachedTasks.filter((task) => task.status !== 'done').length;
  document.querySelector('#task-done').textContent = cachedTasks.filter((task) => task.status === 'done').length;
}
async function fetchTasks() { const response = await fetch('/api/tasks'); cachedTasks = response.ok ? await response.json() : []; renderTasks(); }
async function saveTask(task) {
  await fetch(`/api/tasks/${task.id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ description: task.description, deadline: task.deadline, status: task.status }) });
  await fetchTasks();
}
async function removeTask(taskId) { await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' }); await fetchTasks(); }
function editTask(task) {
  const description = window.prompt('Task description', task.description); if (description === null || !description.trim()) return;
  saveTask({ ...task, description: description.trim() });
}
taskForm.addEventListener('submit', async (event) => {
  event.preventDefault();
  const description = document.querySelector('#task-description').value.trim();
  const rawDeadline = document.querySelector('#task-deadline').value;
  await fetch('/api/tasks', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ description, deadline: rawDeadline ? new Date(rawDeadline).toISOString() : null, status: 'todo' }) });
  taskForm.reset(); await fetchTasks();
});
taskFilter.addEventListener('change', renderTasks);

async function fetchLogs() {
  const response = await fetch('/api/priority-logs');
  const logs = response.ok ? await response.json() : [];
  vaultTableBody.replaceChildren();
  logs.forEach((log) => {
    const row = document.createElement('tr');
    row.innerHTML = `<td>${formatDateTime(log.original_timestamp)}</td><td><span class="audit-action">${log.action}</span></td><td></td><td>${formatDateTime(log.logged_at)}</td>`;
    row.children[2].textContent = cleanAlert(log.previous_content);
    vaultTableBody.append(row);
  });
  document.querySelector('#audit-total').textContent = logs.length;
}
document.querySelector('#refresh-vault').addEventListener('click', fetchLogs);

renderChatList();
fetchMessages();
