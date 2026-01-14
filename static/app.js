// ===================== STATE =====================
let currentUser = null;
let currentProject = null;
let projects = [];
let tasks = [];
let users = [];
let ws = null;
let draggedTask = null;

const API_BASE = '';

// ===================== UTILS =====================
function getToken() {
    return localStorage.getItem('token');
}

function setToken(token) {
    localStorage.setItem('token', token);
}

function clearToken() {
    localStorage.removeItem('token');
}

async function apiRequest(endpoint, options = {}) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json',
        ...options.headers
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const response = await fetch(`${API_BASE}${endpoint}`, {
        ...options,
        headers
    });
    
    if (response.status === 401) {
        clearToken();
        showAuthScreen();
        throw new Error('No autorizado');
    }
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Error en la solicitud');
    }
    
    return response.json();
}

function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const icons = {
        success: 'fa-check-circle',
        error: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.innerHTML = `
        <i class="fas ${icons[type]}"></i>
        <span>${message}</span>
    `;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideInRight 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

function formatDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-ES', { day: 'numeric', month: 'short' });
}

function formatDateTime(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('es-ES', { 
        day: 'numeric', 
        month: 'short',
        hour: '2-digit',
        minute: '2-digit'
    });
}

function getInitials(name) {
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
}

function isOverdue(dateStr) {
    if (!dateStr) return false;
    return new Date(dateStr) < new Date();
}

// ===================== AUTH =====================
function showAuthScreen() {
    document.getElementById('auth-screen').classList.remove('hidden');
    document.getElementById('main-app').classList.add('hidden');
}

function showMainApp() {
    document.getElementById('auth-screen').classList.add('hidden');
    document.getElementById('main-app').classList.remove('hidden');
}

document.querySelectorAll('.auth-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.auth-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        
        const formType = tab.dataset.tab;
        document.getElementById('login-form').classList.toggle('hidden', formType !== 'login');
        document.getElementById('register-form').classList.toggle('hidden', formType !== 'register');
    });
});

document.getElementById('login-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const email = document.getElementById('login-email').value;
    const password = document.getElementById('login-password').value;
    
    try {
        const data = await apiRequest('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });
        
        setToken(data.access_token);
        currentUser = data.user;
        showToast('¡Bienvenido!', 'success');
        initApp();
    } catch (error) {
        showToast(error.message, 'error');
    }
});

document.getElementById('register-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const name = document.getElementById('register-name').value;
    const email = document.getElementById('register-email').value;
    const password = document.getElementById('register-password').value;
    const avatar_color = document.getElementById('register-color').value;
    
    try {
        await apiRequest('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify({ name, email, password, avatar_color })
        });
        
        showToast('Cuenta creada. Inicia sesión.', 'success');
        document.querySelector('[data-tab="login"]').click();
    } catch (error) {
        showToast(error.message, 'error');
    }
});

document.getElementById('logout-btn').addEventListener('click', () => {
    clearToken();
    currentUser = null;
    if (ws) ws.close();
    showAuthScreen();
    showToast('Sesión cerrada', 'info');
});

// ===================== INIT =====================
async function initApp() {
    showMainApp();
    updateUserInfo();
    
    try {
        await Promise.all([
            loadProjects(),
            loadUsers(),
            loadDashboard()
        ]);
    } catch (error) {
        console.error('Error initializing:', error);
    }
}

function updateUserInfo() {
    if (!currentUser) return;
    
    const userInfo = document.getElementById('user-info');
    const avatar = userInfo.querySelector('.avatar');
    const userName = userInfo.querySelector('.user-name');
    const userEmail = userInfo.querySelector('.user-email');
    
    avatar.textContent = getInitials(currentUser.name);
    avatar.style.background = currentUser.avatar_color;
    userName.textContent = currentUser.name;
    userEmail.textContent = currentUser.email;
}

// ===================== NAVIGATION =====================
document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const view = item.dataset.view;
        switchView(view);
    });
});

function switchView(view) {
    document.querySelectorAll('.nav-item').forEach(i => i.classList.remove('active'));
    document.querySelector(`[data-view="${view}"]`).classList.add('active');
    
    document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
    document.getElementById(`${view}-view`).classList.add('active');
    
    const titles = {
        'dashboard': 'Dashboard',
        'kanban': 'Tablero Kanban',
        'gantt': 'Diagrama Gantt',
        'my-tasks': 'Mis Tareas',
        'team': 'Equipo'
    };
    document.getElementById('page-title').textContent = titles[view] || view;
    
    if (view === 'my-tasks') loadMyTasks();
    if (view === 'team') loadTeam();
    if (view === 'gantt') renderGantt();
}

// ===================== PROJECTS =====================
async function loadProjects() {
    try {
        projects = await apiRequest('/api/projects');
        renderProjectList();
        updateProjectSelects();
    } catch (error) {
        showToast('Error cargando proyectos', 'error');
    }
}

function renderProjectList() {
    const list = document.getElementById('project-list');
    list.innerHTML = projects.map(p => `
        <div class="project-item ${currentProject?.id === p.id ? 'active' : ''}" data-id="${p.id}">
            <span class="project-dot" style="background: ${p.color}"></span>
            <span>${p.name}</span>
        </div>
    `).join('');
    
    list.querySelectorAll('.project-item').forEach(item => {
        item.addEventListener('click', () => selectProject(parseInt(item.dataset.id)));
    });
}

function updateProjectSelects() {
    const options = projects.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
    
    ['kanban-project-select', 'gantt-project-select'].forEach(id => {
        const select = document.getElementById(id);
        select.innerHTML = '<option value="">Seleccionar proyecto</option>' + options;
        if (currentProject) select.value = currentProject.id;
    });
}

async function selectProject(projectId) {
    currentProject = projects.find(p => p.id === projectId);
    
    document.querySelectorAll('.project-item').forEach(item => {
        item.classList.toggle('active', parseInt(item.dataset.id) === projectId);
    });
    
    ['kanban-project-select', 'gantt-project-select'].forEach(id => {
        document.getElementById(id).value = projectId;
    });
    
    await loadTasks();
    connectWebSocket();
}

document.getElementById('kanban-project-select').addEventListener('change', (e) => {
    if (e.target.value) selectProject(parseInt(e.target.value));
});

document.getElementById('gantt-project-select').addEventListener('change', (e) => {
    if (e.target.value) {
        selectProject(parseInt(e.target.value));
        renderGantt();
    }
});

// ===================== PROJECT MODAL =====================
document.getElementById('add-project-btn').addEventListener('click', () => {
    document.getElementById('project-id').value = '';
    document.getElementById('project-form').reset();
    document.getElementById('project-modal-title').textContent = 'Nuevo Proyecto';
    document.getElementById('project-color').value = '#6366f1';
    document.querySelectorAll('.color-option').forEach(c => c.classList.remove('selected'));
    document.querySelector('.color-option[data-color="#6366f1"]').classList.add('selected');
    openModal('project-modal');
});

document.querySelectorAll('#project-colors .color-option').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.color-option').forEach(c => c.classList.remove('selected'));
        btn.classList.add('selected');
        document.getElementById('project-color').value = btn.dataset.color;
    });
});

document.getElementById('project-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const projectId = document.getElementById('project-id').value;
    const projectData = {
        name: document.getElementById('project-name').value,
        description: document.getElementById('project-description').value,
        color: document.getElementById('project-color').value,
        start_date: document.getElementById('project-start').value || null,
        end_date: document.getElementById('project-end').value || null
    };
    
    try {
        if (projectId) {
            await apiRequest(`/api/projects/${projectId}`, {
                method: 'PUT',
                body: JSON.stringify(projectData)
            });
            showToast('Proyecto actualizado', 'success');
        } else {
            await apiRequest('/api/projects', {
                method: 'POST',
                body: JSON.stringify(projectData)
            });
            showToast('Proyecto creado', 'success');
        }
        
        closeModal('project-modal');
        await loadProjects();
        loadDashboard();
    } catch (error) {
        showToast(error.message, 'error');
    }
});

// ===================== TASKS =====================
async function loadTasks() {
    if (!currentProject) {
        tasks = [];
        renderKanban();
        return;
    }
    
    try {
        tasks = await apiRequest(`/api/projects/${currentProject.id}/tasks`);
        renderKanban();
    } catch (error) {
        showToast('Error cargando tareas', 'error');
    }
}

function renderKanban() {
    const statuses = ['todo', 'in_progress', 'review', 'done'];
    
    statuses.forEach(status => {
        const column = document.getElementById(`column-${status}`);
        const statusTasks = tasks.filter(t => t.status === status);
        
        document.getElementById(`count-${status}`).textContent = statusTasks.length;
        
        column.innerHTML = statusTasks.map(task => {
            const assignee = users.find(u => u.id === task.assignee_id);
            const overdue = task.status !== 'done' && isOverdue(task.due_date);
            
            return `
                <div class="task-card" data-id="${task.id}" draggable="true">
                    <div class="task-card-header">
                        <span class="task-priority ${task.priority}">${task.priority}</span>
                    </div>
                    <div class="task-title">${task.title}</div>
                    ${task.description ? `<div class="task-description">${task.description}</div>` : ''}
                    <div class="task-footer">
                        ${task.due_date ? `
                            <span class="task-due ${overdue ? 'overdue' : ''}">
                                <i class="fas fa-calendar"></i>
                                ${formatDate(task.due_date)}
                            </span>
                        ` : '<span></span>'}
                        ${assignee ? `
                            <div class="task-assignee" style="background: ${assignee.avatar_color}" title="${assignee.name}">
                                ${getInitials(assignee.name)}
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        }).join('');
        
        // Add drag and drop listeners
        column.querySelectorAll('.task-card').forEach(card => {
            card.addEventListener('dragstart', handleDragStart);
            card.addEventListener('dragend', handleDragEnd);
            card.addEventListener('click', () => openTaskModal(parseInt(card.dataset.id)));
        });
    });
    
    // Column drop listeners
    document.querySelectorAll('.column-content').forEach(column => {
        column.addEventListener('dragover', handleDragOver);
        column.addEventListener('drop', handleDrop);
        column.addEventListener('dragleave', handleDragLeave);
    });
}

function handleDragStart(e) {
    draggedTask = e.target;
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
}

function handleDragEnd(e) {
    e.target.classList.remove('dragging');
    document.querySelectorAll('.column-content').forEach(c => c.classList.remove('drag-over'));
}

function handleDragOver(e) {
    e.preventDefault();
    e.currentTarget.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.currentTarget.classList.remove('drag-over');
}

async function handleDrop(e) {
    e.preventDefault();
    e.currentTarget.classList.remove('drag-over');
    
    if (!draggedTask) return;
    
    const taskId = parseInt(draggedTask.dataset.id);
    const newStatus = e.currentTarget.id.replace('column-', '');
    
    try {
        await apiRequest(`/api/tasks/${taskId}`, {
            method: 'PUT',
            body: JSON.stringify({ status: newStatus })
        });
        
        await loadTasks();
        loadDashboard();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ===================== TASK MODAL =====================
document.getElementById('add-task-btn').addEventListener('click', () => {
    if (!currentProject) {
        showToast('Selecciona un proyecto primero', 'warning');
        return;
    }
    
    document.getElementById('task-id').value = '';
    document.getElementById('task-form').reset();
    document.getElementById('task-modal-title').textContent = 'Nueva Tarea';
    document.getElementById('delete-task-btn').style.display = 'none';
    document.getElementById('progress-value').textContent = '0';
    updateAssigneeSelect();
    openModal('task-modal');
});

function updateAssigneeSelect() {
    const select = document.getElementById('task-assignee');
    select.innerHTML = '<option value="">Sin asignar</option>' +
        users.map(u => `<option value="${u.id}">${u.name}</option>`).join('');
}

function openTaskModal(taskId) {
    const task = tasks.find(t => t.id === taskId);
    if (!task) return;
    
    document.getElementById('task-id').value = task.id;
    document.getElementById('task-title').value = task.title;
    document.getElementById('task-description').value = task.description || '';
    document.getElementById('task-status').value = task.status;
    document.getElementById('task-priority').value = task.priority;
    document.getElementById('task-start').value = task.start_date ? task.start_date.split('T')[0] : '';
    document.getElementById('task-due').value = task.due_date ? task.due_date.split('T')[0] : '';
    document.getElementById('task-progress').value = task.progress || 0;
    document.getElementById('progress-value').textContent = task.progress || 0;
    
    updateAssigneeSelect();
    document.getElementById('task-assignee').value = task.assignee_id || '';
    
    document.getElementById('task-modal-title').textContent = 'Editar Tarea';
    document.getElementById('delete-task-btn').style.display = 'block';
    
    openModal('task-modal');
}

document.getElementById('task-progress').addEventListener('input', (e) => {
    document.getElementById('progress-value').textContent = e.target.value;
});

document.getElementById('task-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const taskId = document.getElementById('task-id').value;
    const taskData = {
        title: document.getElementById('task-title').value,
        description: document.getElementById('task-description').value,
        status: document.getElementById('task-status').value,
        priority: document.getElementById('task-priority').value,
        assignee_id: document.getElementById('task-assignee').value || null,
        start_date: document.getElementById('task-start').value || null,
        due_date: document.getElementById('task-due').value || null,
        progress: parseInt(document.getElementById('task-progress').value)
    };
    
    try {
        if (taskId) {
            await apiRequest(`/api/tasks/${taskId}`, {
                method: 'PUT',
                body: JSON.stringify(taskData)
            });
            showToast('Tarea actualizada', 'success');
        } else {
            await apiRequest(`/api/projects/${currentProject.id}/tasks`, {
                method: 'POST',
                body: JSON.stringify(taskData)
            });
            showToast('Tarea creada', 'success');
        }
        
        closeModal('task-modal');
        await loadTasks();
        loadDashboard();
        if (document.getElementById('gantt-view').classList.contains('active')) {
            renderGantt();
        }
    } catch (error) {
        showToast(error.message, 'error');
    }
});

document.getElementById('delete-task-btn').addEventListener('click', async () => {
    const taskId = document.getElementById('task-id').value;
    if (!taskId) return;
    
    if (!confirm('¿Eliminar esta tarea?')) return;
    
    try {
        await apiRequest(`/api/tasks/${taskId}`, { method: 'DELETE' });
        showToast('Tarea eliminada', 'success');
        closeModal('task-modal');
        await loadTasks();
        loadDashboard();
    } catch (error) {
        showToast(error.message, 'error');
    }
});

// ===================== DASHBOARD =====================
async function loadDashboard() {
    try {
        const [stats, activities] = await Promise.all([
            apiRequest('/api/dashboard/stats'),
            apiRequest('/api/activities?limit=10')
        ]);
        
        renderStats(stats);
        renderActivities(activities);
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

function renderStats(stats) {
    document.getElementById('stat-projects').textContent = stats.total_projects;
    document.getElementById('stat-tasks').textContent = stats.total_tasks;
    document.getElementById('stat-completed').textContent = stats.completed_tasks;
    document.getElementById('stat-progress').textContent = stats.in_progress_tasks;
    document.getElementById('stat-overdue').textContent = stats.overdue_tasks;
    
    // Progress ring
    const rate = stats.completion_rate;
    document.getElementById('completion-rate').textContent = `${rate}%`;
    const circle = document.getElementById('progress-ring');
    const circumference = 2 * Math.PI * 80;
    circle.style.strokeDasharray = circumference;
    circle.style.strokeDashoffset = circumference - (rate / 100) * circumference;
    circle.style.stroke = `url(#gradient)`;
    
    // Add SVG gradient if not exists
    if (!document.getElementById('progress-gradient')) {
        const svg = circle.closest('svg');
        const defs = document.createElementNS('http://www.w3.org/2000/svg', 'defs');
        defs.innerHTML = `
            <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style="stop-color:#6366f1"/>
                <stop offset="100%" style="stop-color:#8b5cf6"/>
            </linearGradient>
        `;
        defs.id = 'progress-gradient';
        svg.insertBefore(defs, svg.firstChild);
    }
    
    // Priority bars
    const maxPriority = Math.max(stats.high_priority_tasks, stats.medium_priority_tasks, stats.low_priority_tasks, 1);
    document.getElementById('bar-high').style.width = `${(stats.high_priority_tasks / maxPriority) * 100}%`;
    document.getElementById('bar-medium').style.width = `${(stats.medium_priority_tasks / maxPriority) * 100}%`;
    document.getElementById('bar-low').style.width = `${(stats.low_priority_tasks / maxPriority) * 100}%`;
    document.getElementById('count-high').textContent = stats.high_priority_tasks;
    document.getElementById('count-medium').textContent = stats.medium_priority_tasks;
    document.getElementById('count-low').textContent = stats.low_priority_tasks;
}

function renderActivities(activities) {
    const list = document.getElementById('activity-list');
    
    const icons = {
        created: 'fa-plus',
        updated: 'fa-edit',
        moved: 'fa-arrows-alt',
        deleted: 'fa-trash'
    };
    
    list.innerHTML = activities.map(activity => {
        const user = users.find(u => u.id === activity.user_id);
        return `
            <div class="activity-item">
                <div class="activity-icon ${activity.action}">
                    <i class="fas ${icons[activity.action]}"></i>
                </div>
                <div class="activity-content">
                    <div class="activity-text">
                        <strong>${user?.name || 'Usuario'}</strong> 
                        ${activity.action === 'created' ? 'creó' : activity.action === 'moved' ? 'movió' : 'actualizó'} 
                        ${activity.entity_type === 'project' ? 'el proyecto' : 'la tarea'} 
                        "${activity.entity_name}"
                        ${activity.details ? `<br><small>${activity.details}</small>` : ''}
                    </div>
                    <div class="activity-time">${formatDateTime(activity.created_at)}</div>
                </div>
            </div>
        `;
    }).join('');
}

// ===================== GANTT =====================
let ganttScale = 40; // pixels per day

function renderGantt() {
    if (!currentProject || tasks.length === 0) {
        document.getElementById('gantt-timeline').innerHTML = '<p style="padding: 20px; color: var(--text-muted);">Selecciona un proyecto con tareas para ver el Gantt</p>';
        document.getElementById('gantt-tasks').innerHTML = '';
        return;
    }
    
    // Find date range
    const tasksWithDates = tasks.filter(t => t.start_date || t.due_date);
    if (tasksWithDates.length === 0) {
        document.getElementById('gantt-timeline').innerHTML = '<p style="padding: 20px; color: var(--text-muted);">Las tareas necesitan fechas para mostrar el Gantt</p>';
        document.getElementById('gantt-tasks').innerHTML = '';
        return;
    }
    
    let minDate = new Date();
    let maxDate = new Date();
    
    tasksWithDates.forEach(t => {
        if (t.start_date) {
            const start = new Date(t.start_date);
            if (start < minDate) minDate = start;
        }
        if (t.due_date) {
            const end = new Date(t.due_date);
            if (end > maxDate) maxDate = end;
        }
    });
    
    // Add padding
    minDate.setDate(minDate.getDate() - 3);
    maxDate.setDate(maxDate.getDate() + 7);
    
    // Render timeline
    const timeline = document.getElementById('gantt-timeline');
    const days = [];
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    for (let d = new Date(minDate); d <= maxDate; d.setDate(d.getDate() + 1)) {
        const isWeekend = d.getDay() === 0 || d.getDay() === 6;
        const isToday = d.getTime() === today.getTime();
        days.push(`
            <div class="gantt-day ${isWeekend ? 'weekend' : ''} ${isToday ? 'today' : ''}">
                ${d.getDate()}<br>
                <small>${d.toLocaleDateString('es-ES', { weekday: 'short' })}</small>
            </div>
        `);
    }
    timeline.innerHTML = days.join('');
    
    // Render task bars
    const taskRows = document.getElementById('gantt-tasks');
    const colors = {
        todo: '#64748b',
        in_progress: '#06b6d4',
        review: '#f59e0b',
        done: '#10b981'
    };
    
    taskRows.innerHTML = tasksWithDates.map(task => {
        const start = task.start_date ? new Date(task.start_date) : new Date(task.due_date);
        const end = task.due_date ? new Date(task.due_date) : new Date(task.start_date);
        
        const startOffset = Math.floor((start - minDate) / (1000 * 60 * 60 * 24)) * ganttScale;
        const duration = Math.max(1, Math.floor((end - start) / (1000 * 60 * 60 * 24)) + 1) * ganttScale;
        
        return `
            <div class="gantt-task-row">
                <div class="gantt-task-info">
                    <span class="priority-dot ${task.priority}"></span>
                    <span class="gantt-task-name">${task.title}</span>
                </div>
                <div class="gantt-task-bar-container">
                    <div class="gantt-task-bar" style="left: ${startOffset}px; width: ${duration}px; background: ${colors[task.status]};" data-id="${task.id}">
                        <div class="progress" style="width: ${task.progress}%"></div>
                        ${duration > 80 ? task.title : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    // Add click listeners
    taskRows.querySelectorAll('.gantt-task-bar').forEach(bar => {
        bar.addEventListener('click', () => openTaskModal(parseInt(bar.dataset.id)));
    });
}

document.getElementById('gantt-zoom-in').addEventListener('click', () => {
    ganttScale = Math.min(80, ganttScale + 10);
    renderGantt();
});

document.getElementById('gantt-zoom-out').addEventListener('click', () => {
    ganttScale = Math.max(20, ganttScale - 10);
    renderGantt();
});

document.getElementById('gantt-today').addEventListener('click', () => {
    const container = document.querySelector('.gantt-container');
    const today = document.querySelector('.gantt-day.today');
    if (today) {
        today.scrollIntoView({ behavior: 'smooth', inline: 'center' });
    }
});

// ===================== MY TASKS =====================
async function loadMyTasks() {
    if (!currentUser) return;
    
    try {
        // Load all tasks from all projects
        let allTasks = [];
        for (const project of projects) {
            const projectTasks = await apiRequest(`/api/projects/${project.id}/tasks`);
            allTasks = allTasks.concat(projectTasks.map(t => ({ ...t, project })));
        }
        
        // Filter by current user
        const myTasks = allTasks.filter(t => t.assignee_id === currentUser.id);
        renderMyTasks(myTasks);
    } catch (error) {
        showToast('Error cargando tareas', 'error');
    }
}

function renderMyTasks(taskList) {
    const list = document.getElementById('my-tasks-list');
    const filter = document.querySelector('.filter-tab.active').dataset.filter;
    
    let filtered = taskList;
    if (filter !== 'all') {
        filtered = taskList.filter(t => t.status === filter);
    }
    
    list.innerHTML = filtered.map(task => `
        <div class="task-list-item" data-id="${task.id}">
            <div class="task-checkbox ${task.status === 'done' ? 'checked' : ''}" data-task-id="${task.id}">
                <i class="fas fa-check"></i>
            </div>
            <div class="task-list-content">
                <div class="task-list-title ${task.status === 'done' ? 'completed' : ''}">${task.title}</div>
                <div class="task-list-meta">
                    <span class="task-list-project">
                        <span class="dot" style="background: ${task.project.color}"></span>
                        ${task.project.name}
                    </span>
                    ${task.due_date ? `
                        <span class="${isOverdue(task.due_date) && task.status !== 'done' ? 'overdue' : ''}">
                            <i class="fas fa-calendar"></i> ${formatDate(task.due_date)}
                        </span>
                    ` : ''}
                    <span class="task-priority ${task.priority}">${task.priority}</span>
                </div>
            </div>
        </div>
    `).join('');
    
    list.querySelectorAll('.task-checkbox').forEach(checkbox => {
        checkbox.addEventListener('click', async (e) => {
            e.stopPropagation();
            const taskId = parseInt(checkbox.dataset.taskId);
            const newStatus = checkbox.classList.contains('checked') ? 'todo' : 'done';
            
            try {
                await apiRequest(`/api/tasks/${taskId}`, {
                    method: 'PUT',
                    body: JSON.stringify({ status: newStatus })
                });
                loadMyTasks();
                loadDashboard();
            } catch (error) {
                showToast(error.message, 'error');
            }
        });
    });
}

document.querySelectorAll('.filter-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        loadMyTasks();
    });
});

// ===================== TEAM =====================
async function loadUsers() {
    try {
        users = await apiRequest('/api/users');
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

async function loadTeam() {
    const grid = document.getElementById('team-grid');
    
    // Count tasks per user
    let allTasks = [];
    for (const project of projects) {
        try {
            const projectTasks = await apiRequest(`/api/projects/${project.id}/tasks`);
            allTasks = allTasks.concat(projectTasks);
        } catch (e) {}
    }
    
    grid.innerHTML = users.map(user => {
        const userTasks = allTasks.filter(t => t.assignee_id === user.id);
        const completedTasks = userTasks.filter(t => t.status === 'done').length;
        
        return `
            <div class="team-card">
                <div class="team-avatar" style="background: ${user.avatar_color}">
                    ${getInitials(user.name)}
                </div>
                <div class="team-name">${user.name}</div>
                <div class="team-email">${user.email}</div>
                <div class="team-stats">
                    <div class="team-stat">
                        <div class="team-stat-value">${userTasks.length}</div>
                        <div class="team-stat-label">Tareas</div>
                    </div>
                    <div class="team-stat">
                        <div class="team-stat-value">${completedTasks}</div>
                        <div class="team-stat-label">Completadas</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ===================== WEBSOCKET =====================
function connectWebSocket() {
    if (!currentProject) return;
    
    if (ws) ws.close();
    
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    ws = new WebSocket(`${protocol}//${window.location.host}/ws/${currentProject.id}`);
    
    ws.onopen = () => {
        document.getElementById('connection-status').classList.remove('disconnected');
        document.getElementById('connection-status').innerHTML = '<i class="fas fa-wifi"></i><span>Conectado</span>';
    };
    
    ws.onclose = () => {
        document.getElementById('connection-status').classList.add('disconnected');
        document.getElementById('connection-status').innerHTML = '<i class="fas fa-wifi"></i><span>Desconectado</span>';
        
        // Reconnect after 3 seconds
        setTimeout(() => {
            if (currentProject) connectWebSocket();
        }, 3000);
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
            case 'task_created':
            case 'task_updated':
            case 'task_deleted':
                loadTasks();
                loadDashboard();
                break;
        }
    };
}

// ===================== MODALS =====================
function openModal(modalId) {
    document.getElementById(modalId).classList.add('active');
}

function closeModal(modalId) {
    document.getElementById(modalId).classList.remove('active');
}

document.querySelectorAll('.modal-close').forEach(btn => {
    btn.addEventListener('click', () => {
        btn.closest('.modal-overlay').classList.remove('active');
    });
});

document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.classList.remove('active');
        }
    });
});

// ===================== SEARCH =====================
document.getElementById('search-input').addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase();
    
    document.querySelectorAll('.task-card').forEach(card => {
        const title = card.querySelector('.task-title').textContent.toLowerCase();
        const desc = card.querySelector('.task-description')?.textContent.toLowerCase() || '';
        const matches = title.includes(query) || desc.includes(query);
        card.style.display = matches ? 'block' : 'none';
    });
});

// ===================== MOBILE MENU =====================
document.querySelector('.mobile-menu-toggle').addEventListener('click', () => {
    document.querySelector('.sidebar').classList.toggle('open');
});

// ===================== INIT ON LOAD =====================
document.addEventListener('DOMContentLoaded', async () => {
    const token = getToken();
    
    if (token) {
        try {
            currentUser = await apiRequest('/api/auth/me');
            initApp();
        } catch (error) {
            showAuthScreen();
        }
    } else {
        showAuthScreen();
    }
});
