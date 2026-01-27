// ===================== STATE =====================
let currentUser = null;
let currentProject = null;
let projects = [];
let tasks = [];
let users = [];
let stages = [];  // Etapas del proyecto actual
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
        const user = await apiRequest('/api/auth/register', {
            method: 'POST',
            body: JSON.stringify({ name, email, password, avatar_color })
        });
        
        if (user.is_approved) {
            // Primer usuario (admin) - puede iniciar sesión directamente
            showToast('¡Cuenta de administrador creada! Inicia sesión.', 'success');
        } else {
            // Otros usuarios - necesitan aprobación
            showToast('Solicitud enviada. Un administrador debe aprobar tu cuenta.', 'warning');
        }
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
    setupAdminUI();
    
    try {
        await Promise.all([
            loadProjects(),
            loadUsers(),
            loadDashboard()
        ]);
        
        // Si es admin, cargar usuarios pendientes
        if (currentUser && currentUser.is_admin) {
            loadPendingUsers();
        }
    } catch (error) {
        console.error('Error initializing:', error);
    }
}

function setupAdminUI() {
    if (!currentUser) return;
    
    // Aplicar clase según rol
    if (currentUser.is_admin) {
        document.body.classList.remove('user-role');
        document.body.classList.add('admin-role');
    } else {
        document.body.classList.remove('admin-role');
        document.body.classList.add('user-role');
    }
    
    // Mostrar/ocultar opción de administración
    const adminNav = document.querySelector('.nav-item[data-view="admin"]');
    if (currentUser.is_admin) {
        adminNav.classList.remove('hidden');
    } else {
        adminNav.classList.add('hidden');
    }
    
    // Setup admin tabs
    document.querySelectorAll('.admin-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            console.log('Tab clicked:', tab.dataset.tab);
            document.querySelectorAll('.admin-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            
            const tabName = tab.dataset.tab;
            const adminPending = document.getElementById('admin-pending');
            const adminAllUsers = document.getElementById('admin-all-users');
            const adminTemplates = document.getElementById('admin-templates');
            const adminTeams = document.getElementById('admin-teams');
            
            console.log('Elementos encontrados:', {
                pending: !!adminPending,
                allUsers: !!adminAllUsers,
                templates: !!adminTemplates,
                teams: !!adminTeams
            });
            
            adminPending?.classList.toggle('hidden', tabName !== 'pending');
            adminAllUsers?.classList.toggle('hidden', tabName !== 'all-users');
            adminTemplates?.classList.toggle('hidden', tabName !== 'templates');
            adminTeams?.classList.toggle('hidden', tabName !== 'teams');
            
            if (tabName === 'pending') {
                loadPendingUsers();
            } else if (tabName === 'all-users') {
                loadAllUsersAdmin();
            } else if (tabName === 'templates') {
                console.log('Cargando plantillas...');
                loadTemplates();
            } else if (tabName === 'teams') {
                loadAdminTeams();
            }
        });
    });
    
    // Setup progress form
    setupProgressForm();
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
    
    // Mostrar badge de admin
    if (currentUser.is_admin) {
        userName.innerHTML = `${currentUser.name} <span class="user-badge admin" style="font-size:0.7rem;">Admin</span>`;
    }
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
        'team': 'Equipo',
        'admin': 'Administración'
    };
    document.getElementById('page-title').textContent = titles[view] || view;
    
    if (view === 'my-tasks') loadMyTasks();
    if (view === 'team') loadTeam();
    if (view === 'gantt') renderGantt();
    if (view === 'admin') loadPendingUsers();
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
    const isAdmin = currentUser && currentUser.is_admin;
    
    list.innerHTML = projects.map(p => `
        <div class="project-item ${currentProject?.id === p.id ? 'active' : ''}" data-id="${p.id}">
            <div class="project-item-main">
                <span class="project-dot" style="background: ${p.color}"></span>
                <span class="project-name">${p.name}</span>
            </div>
            ${isAdmin ? `
                <button class="btn-edit-project" onclick="event.stopPropagation(); editProject(${p.id})" title="Editar proyecto">
                    <i class="fas fa-pen"></i>
                </button>
            ` : ''}
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
    
    // Cargar etapas del proyecto
    if (currentProject) {
        stages = await loadProjectStages(projectId);
        updateStageSelect();
    } else {
        stages = [];
    }
    
    // Actualizar botón de reporte de proyecto
    updateProjectReportButton();
    
    await loadTasks();
    connectWebSocket();
}

function updateStageSelect() {
    const select = document.getElementById('task-stage');
    if (!select) return;
    
    select.innerHTML = '<option value="">Sin etapa</option>' + 
        stages.map(s => `<option value="${s.id}">${s.name} (${s.percentage}%)</option>`).join('');
}

document.getElementById('kanban-project-select').addEventListener('change', (e) => {
    if (e.target.value) selectProject(parseInt(e.target.value));
});

document.getElementById('gantt-project-select').addEventListener('change', async (e) => {
    if (e.target.value) {
        await selectProject(parseInt(e.target.value));
        renderGantt();
    }
});

// ===================== PROJECT MODAL =====================
function renderMembersSelector(selectedIds = []) {
    const container = document.getElementById('project-members-selector');
    if (!container) return;
    
    // Solo mostrar usuarios aprobados
    const approvedUsers = users.filter(u => u.is_approved);
    
    container.innerHTML = approvedUsers.map(user => `
        <label class="member-checkbox ${selectedIds.includes(user.id) ? 'selected' : ''}">
            <input type="checkbox" value="${user.id}" ${selectedIds.includes(user.id) ? 'checked' : ''}>
            <div class="avatar-small" style="background: ${user.avatar_color}">
                ${getInitials(user.name)}
            </div>
            <span>${user.name}</span>
        </label>
    `).join('');
    
    // Agregar eventos de cambio
    container.querySelectorAll('input[type="checkbox"]').forEach(cb => {
        cb.addEventListener('change', () => {
            cb.closest('.member-checkbox').classList.toggle('selected', cb.checked);
        });
    });
}

function getSelectedMemberIds() {
    const checkboxes = document.querySelectorAll('#project-members-selector input[type="checkbox"]:checked');
    return Array.from(checkboxes).map(cb => parseInt(cb.value));
}

// ===================== ETAPAS DEL PROYECTO =====================
let tempStages = [];  // Etapas temporales al crear/editar proyecto

function renderStagesEditor(existingStages = []) {
    tempStages = existingStages.map(s => ({...s}));
    renderStagesList();
}

function renderStagesList() {
    const container = document.getElementById('project-stages-container');
    if (!container) return;
    
    container.innerHTML = tempStages.map((stage, index) => `
        <div class="stage-item" data-index="${index}">
            <div class="stage-item-header">
                <input type="text" placeholder="Nombre de la etapa" value="${stage.name || ''}" 
                       onchange="updateTempStage(${index}, 'name', this.value)">
                <button type="button" class="btn-remove-stage" onclick="removeTempStage(${index})">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
            <div class="stage-item-row">
                <input type="date" value="${stage.start_date ? stage.start_date.split('T')[0] : ''}" 
                       placeholder="Inicio" onchange="updateTempStage(${index}, 'start_date', this.value)">
                <input type="date" value="${stage.end_date ? stage.end_date.split('T')[0] : ''}" 
                       placeholder="Fin" onchange="updateTempStage(${index}, 'end_date', this.value)">
                <div class="stage-percentage">
                    <input type="number" min="1" max="100" value="${stage.percentage || ''}" 
                           placeholder="%" onchange="updateTempStage(${index}, 'percentage', parseFloat(this.value))">
                </div>
            </div>
        </div>
    `).join('');
    
    updateStagesTotalDisplay();
}

function updateTempStage(index, field, value) {
    if (tempStages[index]) {
        tempStages[index][field] = value;
        if (field === 'percentage') {
            updateStagesTotalDisplay();
        }
    }
}

function removeTempStage(index) {
    tempStages.splice(index, 1);
    renderStagesList();
}

function addTempStage() {
    tempStages.push({
        name: '',
        percentage: 0,
        start_date: '',
        end_date: ''
    });
    renderStagesList();
}

function updateStagesTotalDisplay() {
    const total = tempStages.reduce((sum, s) => sum + (parseFloat(s.percentage) || 0), 0);
    const display = document.getElementById('stages-total-percentage');
    if (display) {
        display.textContent = `${total}%`;
        display.style.color = total === 100 ? 'var(--success)' : total > 100 ? 'var(--danger)' : 'var(--warning)';
    }
}

function getValidStages() {
    return tempStages.filter(s => s.name && s.percentage > 0).map(s => ({
        name: s.name,
        description: s.description || null,
        percentage: s.percentage,
        start_date: s.start_date || null,
        end_date: s.end_date || null
    }));
}

// Cargar etapas de un proyecto existente
async function loadProjectStages(projectId) {
    try {
        const stagesData = await apiRequest(`/api/projects/${projectId}/stages`);
        return stagesData;
    } catch (error) {
        console.error('Error loading stages:', error);
        return [];
    }
}

// Event listener para agregar etapa
document.getElementById('add-stage-btn')?.addEventListener('click', addTempStage);

document.getElementById('add-project-btn').addEventListener('click', () => {
    document.getElementById('project-id').value = '';
    document.getElementById('project-form').reset();
    document.getElementById('project-modal-title').textContent = 'Nuevo Proyecto';
    document.getElementById('project-color').value = '#6366f1';
    document.querySelectorAll('.color-option').forEach(c => c.classList.remove('selected'));
    document.querySelector('.color-option[data-color="#6366f1"]').classList.add('selected');
    
    // Seleccionar al usuario actual por defecto
    renderMembersSelector([currentUser.id]);
    
    // Inicializar etapas vacías
    renderStagesEditor([]);
    
    openModal('project-modal');
});

// Función para abrir modal de editar proyecto
async function editProject(projectId) {
    const project = projects.find(p => p.id === projectId);
    if (!project) return;
    
    document.getElementById('project-id').value = project.id;
    document.getElementById('project-name').value = project.name;
    document.getElementById('project-description').value = project.description || '';
    document.getElementById('project-start').value = project.start_date ? project.start_date.split('T')[0] : '';
    document.getElementById('project-end').value = project.end_date ? project.end_date.split('T')[0] : '';
    document.getElementById('project-color').value = project.color;
    document.getElementById('project-modal-title').textContent = 'Editar Proyecto';
    
    document.querySelectorAll('.color-option').forEach(c => c.classList.remove('selected'));
    const colorBtn = document.querySelector(`.color-option[data-color="${project.color}"]`);
    if (colorBtn) colorBtn.classList.add('selected');
    
    // Cargar miembros actuales
    const memberIds = project.members ? project.members.map(m => m.id) : [];
    renderMembersSelector(memberIds);
    
    // Cargar etapas existentes
    const existingStages = await loadProjectStages(projectId);
    renderStagesEditor(existingStages);
    
    openModal('project-modal');
}

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
    const startDate = document.getElementById('project-start').value;
    const endDate = document.getElementById('project-end').value;
    const memberIds = getSelectedMemberIds();
    const stagesToSave = getValidStages();
    
    // Validar que las etapas sumen 100% si hay etapas
    if (stagesToSave.length > 0) {
        const totalPercentage = stagesToSave.reduce((sum, s) => sum + s.percentage, 0);
        if (totalPercentage !== 100) {
            showToast(`Las etapas deben sumar 100% (actual: ${totalPercentage}%)`, 'warning');
            return;
        }
    }
    
    const projectData = {
        name: document.getElementById('project-name').value,
        description: document.getElementById('project-description').value || null,
        color: document.getElementById('project-color').value,
        start_date: startDate ? new Date(startDate).toISOString() : null,
        end_date: endDate ? new Date(endDate).toISOString() : null,
        member_ids: memberIds
    };
    
    try {
        let savedProjectId = projectId;
        
        if (projectId) {
            await apiRequest(`/api/projects/${projectId}`, {
                method: 'PUT',
                body: JSON.stringify(projectData)
            });
            showToast('Proyecto actualizado', 'success');
        } else {
            const newProject = await apiRequest('/api/projects', {
                method: 'POST',
                body: JSON.stringify(projectData)
            });
            savedProjectId = newProject.id;
            showToast('Proyecto creado', 'success');
        }
        
        // Guardar etapas
        if (savedProjectId && stagesToSave.length > 0) {
            // Obtener etapas existentes
            const existingStages = await loadProjectStages(savedProjectId);
            
            // Eliminar etapas que ya no están
            for (const existing of existingStages) {
                const stillExists = tempStages.find(s => s.id === existing.id);
                if (!stillExists) {
                    await apiRequest(`/api/stages/${existing.id}`, { method: 'DELETE' });
                }
            }
            
            // Crear o actualizar etapas
            for (let i = 0; i < stagesToSave.length; i++) {
                const stageData = {
                    ...stagesToSave[i],
                    position: i,
                    start_date: stagesToSave[i].start_date ? new Date(stagesToSave[i].start_date).toISOString() : null,
                    end_date: stagesToSave[i].end_date ? new Date(stagesToSave[i].end_date).toISOString() : null
                };
                
                const existingStage = tempStages[i];
                if (existingStage && existingStage.id) {
                    await apiRequest(`/api/stages/${existingStage.id}`, {
                        method: 'PUT',
                        body: JSON.stringify(stageData)
                    });
                } else {
                    await apiRequest(`/api/projects/${savedProjectId}/stages`, {
                        method: 'POST',
                        body: JSON.stringify(stageData)
                    });
                }
            }
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
        renderGantt();
        return;
    }
    
    try {
        tasks = await apiRequest(`/api/projects/${currentProject.id}/tasks`);
        console.log('Tareas cargadas:', tasks.length, tasks);
        renderKanban();
        renderGantt();
    } catch (error) {
        console.error('Error cargando tareas:', error);
        showToast('Error cargando tareas', 'error');
    }
}

function renderKanban() {
    const statuses = ['todo', 'in_progress', 'review', 'done'];
    const isAdmin = currentUser && currentUser.is_admin;
    
    statuses.forEach(status => {
        const column = document.getElementById(`column-${status}`);
        const statusTasks = tasks.filter(t => t.status === status);
        
        document.getElementById(`count-${status}`).textContent = statusTasks.length;
        
        column.innerHTML = statusTasks.map(task => {
            const assignee = users.find(u => u.id === task.assignee_id);
            const overdue = task.status !== 'done' && isOverdue(task.due_date);
            const isMyTask = task.assignee_id === currentUser?.id;
            const canUpdateProgress = isMyTask || isAdmin;
            
            return `
                <div class="task-card" data-id="${task.id}" draggable="${isAdmin}">
                    <div class="task-card-header">
                        <span class="task-priority ${task.priority}">${task.priority}</span>
                        ${task.progress > 0 ? `<span class="task-progress-badge">${task.progress}%</span>` : ''}
                    </div>
                    <div class="task-title">${task.title}</div>
                    ${task.description ? `<div class="task-description">${task.description}</div>` : ''}
                    ${task.progress > 0 ? `
                        <div class="task-progress-bar">
                            <div class="task-progress-fill" style="width: ${task.progress}%"></div>
                        </div>
                    ` : ''}
                    <div class="task-footer">
                        ${task.due_date ? `
                            <span class="task-due ${overdue ? 'overdue' : ''}">
                                <i class="fas fa-calendar"></i>
                                ${formatDate(task.due_date)}
                            </span>
                        ` : '<span></span>'}
                        <div class="task-footer-right">
                            ${canUpdateProgress && !isAdmin ? `
                                <button class="btn-progress" onclick="event.stopPropagation(); openProgressModal(tasks.find(t => t.id === ${task.id}))" title="Registrar avance">
                                    <i class="fas fa-chart-line"></i>
                                </button>
                            ` : ''}
                            ${assignee ? `
                                <div class="task-assignee" style="background: ${assignee.avatar_color}" title="${assignee.name}">
                                    ${getInitials(assignee.name)}
                                </div>
                            ` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        // Add drag and drop listeners (solo para admin)
        column.querySelectorAll('.task-card').forEach(card => {
            if (isAdmin) {
                card.addEventListener('dragstart', handleDragStart);
                card.addEventListener('dragend', handleDragEnd);
            }
            card.addEventListener('click', (e) => {
                // Evitar abrir modal si se hizo clic en el botón de progreso
                if (e.target.closest('.btn-progress')) return;
                
                const taskId = parseInt(card.dataset.id);
                const task = tasks.find(t => t.id === taskId);
                
                if (isAdmin) {
                    openTaskModal(taskId);
                } else if (task.assignee_id === currentUser?.id) {
                    openProgressModal(task);
                }
            });
        });
    });
    
    // Column drop listeners (solo para admin)
    if (isAdmin) {
        document.querySelectorAll('.column-content').forEach(column => {
            column.addEventListener('dragover', handleDragOver);
            column.addEventListener('drop', handleDrop);
            column.addEventListener('dragleave', handleDragLeave);
        });
    }
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
    document.getElementById('view-history-btn').style.display = 'none'; // Ocultar historial para tareas nuevas
    document.getElementById('progress-value').textContent = '0';
    updateAssigneeSelect();
    updateStageSelect();
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
    
    updateStageSelect();
    document.getElementById('task-stage').value = task.stage_id || '';
    
    document.getElementById('task-modal-title').textContent = 'Editar Tarea';
    
    // Configurar visibilidad según rol
    const isAdmin = currentUser && currentUser.is_admin;
    const isMyTask = task.assignee_id === currentUser?.id;
    
    // Mostrar botón de historial (siempre visible para tareas existentes)
    document.getElementById('view-history-btn').style.display = 'inline-flex';
    
    // Mostrar/ocultar botón eliminar (solo admin)
    document.getElementById('delete-task-btn').style.display = isAdmin ? 'inline-flex' : 'none';
    
    // Campos que solo admin puede editar
    document.getElementById('task-title').disabled = !isAdmin;
    document.getElementById('task-priority').disabled = !isAdmin;
    document.getElementById('task-start').disabled = !isAdmin;
    document.getElementById('task-due').disabled = !isAdmin;
    document.getElementById('task-assignee').disabled = !isAdmin;
    
    // Campos que usuarios normales pueden editar (si es su tarea)
    const canEdit = isAdmin || isMyTask;
    document.getElementById('task-status').disabled = !canEdit;
    document.getElementById('task-description').disabled = !canEdit;
    document.getElementById('task-progress').disabled = !canEdit;
    document.getElementById('task-stage').disabled = !canEdit;
    
    // Mostrar botón guardar solo si puede editar algo
    const submitBtn = document.querySelector('#task-form button[type="submit"]');
    if (submitBtn) {
        submitBtn.style.display = canEdit ? 'block' : 'none';
    }
    
    openModal('task-modal');
}

document.getElementById('task-progress').addEventListener('input', (e) => {
    document.getElementById('progress-value').textContent = e.target.value;
});

document.getElementById('task-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const taskId = document.getElementById('task-id').value;
    const isAdmin = currentUser && currentUser.is_admin;
    
    let taskData;
    
    if (isAdmin) {
        // Admin puede enviar todos los campos
        const assigneeValue = document.getElementById('task-assignee').value;
        const stageValue = document.getElementById('task-stage').value;
        const startDateValue = document.getElementById('task-start').value;
        const dueDateValue = document.getElementById('task-due').value;
        
        taskData = {
            title: document.getElementById('task-title').value,
            description: document.getElementById('task-description').value || null,
            status: document.getElementById('task-status').value,
            priority: document.getElementById('task-priority').value,
            assignee_id: assigneeValue ? parseInt(assigneeValue) : null,
            stage_id: stageValue ? parseInt(stageValue) : null,
            start_date: startDateValue ? new Date(startDateValue).toISOString() : null,
            due_date: dueDateValue ? new Date(dueDateValue).toISOString() : null,
            progress: parseInt(document.getElementById('task-progress').value) || 0
        };
    } else {
        // Usuario normal solo puede enviar: estado, descripción, progreso, etapa
        const stageValue = document.getElementById('task-stage').value;
        
        taskData = {
            status: document.getElementById('task-status').value,
            description: document.getElementById('task-description').value || null,
            progress: parseInt(document.getElementById('task-progress').value) || 0,
            stage_id: stageValue ? parseInt(stageValue) : null
        };
    }
    
    try {
        if (taskId) {
            await apiRequest(`/api/tasks/${taskId}`, {
                method: 'PUT',
                body: JSON.stringify(taskData)
            });
            showToast('Tarea actualizada', 'success');
        } else {
            // Solo admin puede crear tareas
            if (!isAdmin) {
                showToast('Solo administradores pueden crear tareas', 'error');
                return;
            }
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

// ===================== HISTORIAL DE CAMBIOS =====================
let currentTaskForHistory = null;

document.getElementById('view-history-btn').addEventListener('click', async () => {
    const taskId = document.getElementById('task-id').value;
    if (!taskId) {
        showToast('Primero guarda la tarea para ver el historial', 'info');
        return;
    }
    
    // Guardar referencia a la tarea actual
    currentTaskForHistory = tasks.find(t => t.id === parseInt(taskId));
    
    // Mostrar modal de historial
    openHistoryModal(taskId);
});

async function openHistoryModal(taskId) {
    const modal = document.getElementById('history-modal');
    const container = document.getElementById('history-container');
    const titleEl = document.getElementById('history-task-title');
    
    // Mostrar título de la tarea
    if (currentTaskForHistory) {
        titleEl.textContent = currentTaskForHistory.title;
    }
    
    // Mostrar loading
    container.innerHTML = '<div class="history-loading"><i class="fas fa-spinner fa-spin"></i> Cargando historial...</div>';
    
    modal.classList.add('active');
    
    try {
        const history = await apiRequest(`/api/tasks/${taskId}/history`);
        
        if (history.length === 0) {
            container.innerHTML = `
                <div class="history-empty">
                    <i class="fas fa-clipboard-list"></i>
                    <p>No hay cambios registrados para esta tarea</p>
                    <span>Los cambios se registrarán cuando edites la tarea</span>
                </div>
            `;
            return;
        }
        
        // Agrupar por fecha
        const groupedHistory = {};
        history.forEach(entry => {
            const date = new Date(entry.created_at);
            const dateKey = date.toLocaleDateString('es-ES', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
            if (!groupedHistory[dateKey]) {
                groupedHistory[dateKey] = [];
            }
            groupedHistory[dateKey].push(entry);
        });
        
        container.innerHTML = Object.entries(groupedHistory).map(([date, entries]) => `
            <div class="history-date-group">
                <div class="history-date">${date}</div>
                ${entries.map(entry => {
                    const time = new Date(entry.created_at).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
                    return `
                        <div class="history-entry">
                            <div class="history-user">
                                <div class="history-avatar" style="background: ${entry.user_avatar_color || '#6366f1'}">
                                    ${entry.user_name.charAt(0).toUpperCase()}
                                </div>
                                <div class="history-user-info">
                                    <span class="history-user-name">${entry.user_name}</span>
                                    <span class="history-time">${time}</span>
                                </div>
                            </div>
                            <div class="history-change">
                                <span class="history-field">${entry.field_name}</span>
                                <div class="history-values">
                                    ${entry.old_value ? `<span class="history-old">${entry.old_value}</span>` : '<span class="history-old empty">Sin valor</span>'}
                                    <i class="fas fa-arrow-right"></i>
                                    <span class="history-new">${entry.new_value || 'Sin valor'}</span>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `).join('');
        
    } catch (error) {
        container.innerHTML = `
            <div class="history-error">
                <i class="fas fa-exclamation-circle"></i>
                <p>Error al cargar el historial</p>
            </div>
        `;
        console.error('Error loading history:', error);
    }
}

// ===================== DASHBOARD =====================
async function loadDashboard() {
    try {
        const [stats, activities] = await Promise.all([
            apiRequest('/api/dashboard/stats'),
            apiRequest('/api/activities?limit=10')
        ]);
        
        renderStats(stats);
        renderActivities(activities);
        renderEffectivenessProjectSelect();
    } catch (error) {
        console.error('Error loading dashboard:', error);
    }
}

function renderEffectivenessProjectSelect() {
    const select = document.getElementById('effectiveness-project-select');
    if (!select) return;
    
    select.innerHTML = '<option value="">Seleccionar proyecto</option>' + 
        projects.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
}

async function loadProjectEffectiveness(projectId) {
    if (!projectId) {
        document.getElementById('effectiveness-value').textContent = '--%';
        document.getElementById('scheduled-value').textContent = '0%';
        document.getElementById('actual-value').textContent = '0%';
        document.getElementById('scheduled-bar').style.width = '0%';
        document.getElementById('actual-bar').style.width = '0%';
        document.getElementById('effectiveness-status').className = 'effectiveness-status';
        document.getElementById('effectiveness-status').innerHTML = '<i class="fas fa-clock"></i><span>Selecciona un proyecto</span>';
        return;
    }
    
    try {
        const data = await apiRequest(`/api/projects/${projectId}/effectiveness`);
        const metrics = data.metrics;
        
        document.getElementById('effectiveness-value').textContent = `${metrics.effectiveness}%`;
        document.getElementById('scheduled-value').textContent = `${metrics.scheduled_progress}%`;
        document.getElementById('actual-value').textContent = `${metrics.actual_progress}%`;
        document.getElementById('scheduled-bar').style.width = `${metrics.scheduled_progress}%`;
        document.getElementById('actual-bar').style.width = `${metrics.actual_progress}%`;
        
        const statusEl = document.getElementById('effectiveness-status');
        statusEl.className = `effectiveness-status ${metrics.status}`;
        
        const statusIcons = {
            adelantado: 'fa-rocket',
            en_tiempo: 'fa-check-circle',
            atrasado: 'fa-exclamation-triangle'
        };
        
        // Usar diferencia de porcentaje en lugar de días
        const diff = metrics.progress_difference;
        let statusText = '';
        if (diff > 0) {
            statusText = `¡Adelantado! +${Math.abs(diff)}%`;
        } else if (diff >= -10) {
            statusText = `En tiempo (${diff}%)`;
        } else {
            statusText = `Atrasado ${Math.abs(diff)}%`;
        }
        
        statusEl.innerHTML = `<i class="fas ${statusIcons[metrics.status]}"></i><span>${statusText}</span>`;
    } catch (error) {
        console.error('Error loading effectiveness:', error);
    }
}

// Event listener para el selector de efectividad
document.getElementById('effectiveness-project-select')?.addEventListener('change', (e) => {
    loadProjectEffectiveness(e.target.value);
});

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

async function updateGanttEffectiveness() {
    const stagesContainer = document.getElementById('gantt-stages-effectiveness');
    
    if (!currentProject) {
        document.getElementById('gantt-scheduled').textContent = '--%';
        document.getElementById('gantt-actual').textContent = '--%';
        document.getElementById('gantt-effectiveness-value').textContent = '--%';
        document.getElementById('gantt-status-text').textContent = 'Selecciona un proyecto';
        stagesContainer.innerHTML = '';
        return;
    }
    
    try {
        const data = await apiRequest(`/api/projects/${currentProject.id}/effectiveness`);
        const metrics = data.metrics;
        
        document.getElementById('gantt-scheduled').textContent = `${metrics.scheduled_progress}%`;
        document.getElementById('gantt-actual').textContent = `${metrics.actual_progress}%`;
        document.getElementById('gantt-effectiveness-value').textContent = `${metrics.effectiveness}%`;
        
        // Mostrar diferencia de porcentaje
        const diff = metrics.progress_difference;
        let statusText = '';
        if (diff > 0) {
            statusText = `🚀 ¡Adelantado! +${Math.abs(diff)}%`;
        } else if (diff >= -10) {
            statusText = `✅ En tiempo (${diff}%)`;
        } else {
            statusText = `⚠️ Atrasado ${Math.abs(diff)}%`;
        }
        document.getElementById('gantt-status-text').textContent = statusText;
        
        // Colorear según estado
        const effectivenessEl = document.getElementById('gantt-effectiveness-value');
        effectivenessEl.style.color = metrics.status === 'adelantado' ? 'var(--success)' : 
                                       metrics.status === 'atrasado' ? 'var(--danger)' : 'var(--warning)';
        
        // Mostrar etapas con efectividad
        if (data.stages && data.stages.length > 0) {
            stagesContainer.innerHTML = `
                <div class="stages-effectiveness-title">
                    <i class="fas fa-layer-group"></i> Efectividad por Etapa
                </div>
                <div class="stages-effectiveness-grid">
                    ${data.stages.map(stage => {
                        const stageEffectiveness = stage.scheduled_progress > 0 
                            ? Math.round((stage.actual_progress / stage.scheduled_progress) * 100) 
                            : (stage.actual_progress > 0 ? 100 : 100);
                        
                        let statusClass = 'adelantado';
                        let statusIcon = '🚀';
                        if (stageEffectiveness < 90) {
                            statusClass = 'atrasado';
                            statusIcon = '⚠️';
                        } else if (stageEffectiveness < 100) {
                            statusClass = 'en-tiempo';
                            statusIcon = '✅';
                        }
                        
                        const stageDiff = stage.actual_progress - stage.scheduled_progress;
                        
                        return `
                            <div class="stage-effectiveness-card ${statusClass}">
                                <div class="stage-header">
                                    <span class="stage-name">${stage.name}</span>
                                    <span class="stage-weight">${stage.percentage}%</span>
                                </div>
                                <div class="stage-metrics">
                                    <div class="stage-metric">
                                        <span class="metric-label">📅 Prog.</span>
                                        <span class="metric-value scheduled">${stage.scheduled_progress}%</span>
                                    </div>
                                    <div class="stage-metric">
                                        <span class="metric-label">✅ Real</span>
                                        <span class="metric-value actual">${stage.actual_progress}%</span>
                                    </div>
                                    <div class="stage-metric">
                                        <span class="metric-label">📊 Efect.</span>
                                        <span class="metric-value effectiveness ${statusClass}">${statusIcon} ${stageEffectiveness}%</span>
                                    </div>
                                </div>
                                <div class="stage-progress-bar">
                                    <div class="progress-scheduled" style="width: ${stage.scheduled_progress}%"></div>
                                    <div class="progress-actual" style="width: ${stage.actual_progress}%"></div>
                                </div>
                                <div class="stage-diff ${stageDiff >= 0 ? 'positive' : 'negative'}">
                                    ${stageDiff >= 0 ? '+' : ''}${stageDiff.toFixed(1)}%
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        } else {
            stagesContainer.innerHTML = '';
        }
    } catch (error) {
        console.error('Error updating gantt effectiveness:', error);
    }
}

function renderGantt() {
    console.log('renderGantt llamado - Proyecto:', currentProject?.name, '- Tareas:', tasks.length);
    
    // Actualizar efectividad
    updateGanttEffectiveness();
    
    // Siempre mostrar el timeline de fechas
    const timeline = document.getElementById('gantt-timeline');
    const taskRows = document.getElementById('gantt-tasks');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    // Definir rango de fechas: si hay tareas con fechas usarlas, si no mostrar 3 meses desde hoy
    let minDate, maxDate;
    let tasksWithDates = [];
    
    if (currentProject && tasks.length > 0) {
        tasksWithDates = tasks.filter(t => t.start_date || t.due_date);
    }
    
    if (tasksWithDates.length > 0) {
        // Usar fechas de las tareas
        minDate = new Date('2099-12-31');
        maxDate = new Date('1970-01-01');
        
        tasksWithDates.forEach(t => {
            if (t.start_date) {
                const start = new Date(t.start_date);
                if (start < minDate) minDate = new Date(start);
                if (start > maxDate) maxDate = new Date(start);
            }
            if (t.due_date) {
                const end = new Date(t.due_date);
                if (end > maxDate) maxDate = new Date(end);
                if (end < minDate) minDate = new Date(end);
            }
        });
        
        minDate.setDate(minDate.getDate() - 7);
        maxDate.setDate(maxDate.getDate() + 90);
    } else {
        // Sin tareas: mostrar 3 meses desde el inicio del mes actual
        minDate = new Date(today.getFullYear(), today.getMonth(), 1);
        maxDate = new Date(today.getFullYear(), today.getMonth() + 3, 0);
    }
    
    // Asegurar mínimo 90 días de visualización
    const diffDays = Math.floor((maxDate - minDate) / (1000 * 60 * 60 * 24));
    if (diffDays < 90) {
        maxDate.setDate(maxDate.getDate() + (90 - diffDays));
    }
    
    // Render timeline - SIEMPRE mostrar las fechas
    const days = [];
    const monthNames = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic'];
    const dayNames = ['Dom', 'Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb'];
    
    let todayIndex = -1;
    let dayIndex = 0;
    
    for (let d = new Date(minDate); d <= maxDate; d.setDate(d.getDate() + 1)) {
        const isWeekend = d.getDay() === 0 || d.getDay() === 6;
        const isToday = d.toDateString() === today.toDateString();
        if (isToday) todayIndex = dayIndex;
        
        days.push(`
            <div class="gantt-day ${isWeekend ? 'weekend' : ''} ${isToday ? 'today' : ''}" data-index="${dayIndex}" style="width: ${ganttScale}px; min-width: ${ganttScale}px;">
                <span class="gantt-day-date">${d.getDate()} ${monthNames[d.getMonth()]}</span>
                <span class="gantt-day-name">${dayNames[d.getDay()]}</span>
            </div>
        `);
        dayIndex++;
    }
    timeline.innerHTML = days.join('');
    
    const totalDays = dayIndex;
    
    // Mostrar mensaje si no hay proyecto o tareas
    if (!currentProject) {
        taskRows.innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text-muted);"><i class="fas fa-hand-pointer" style="font-size: 2rem; margin-bottom: 10px; display: block;"></i>Selecciona un proyecto para ver las tareas</div>';
        return;
    }
    
    if (tasks.length === 0) {
        taskRows.innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text-muted);"><i class="fas fa-tasks" style="font-size: 2rem; margin-bottom: 10px; display: block;"></i>Este proyecto no tiene tareas</div>';
        return;
    }
    
    if (tasksWithDates.length === 0) {
        taskRows.innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text-muted);"><i class="fas fa-calendar-plus" style="font-size: 2rem; margin-bottom: 10px; display: block;"></i>Las tareas necesitan fechas para mostrar el Gantt</div>';
        return;
    }
    
    // Render task bars
    const colors = {
        todo: '#64748b',
        in_progress: '#06b6d4',
        review: '#f59e0b',
        done: '#10b981'
    };
    
    console.log('Total días:', totalDays, 'Scale:', ganttScale);
    console.log('Total días:', totalDays, 'Scale:', ganttScale);
    
    taskRows.innerHTML = tasksWithDates.map(task => {
        const start = task.start_date ? new Date(task.start_date) : new Date(task.due_date);
        const end = task.due_date ? new Date(task.due_date) : new Date(task.start_date);
        
        // Calcular posición y duración
        const startDayOffset = Math.floor((start - minDate) / (1000 * 60 * 60 * 24));
        const endDayOffset = Math.floor((end - minDate) / (1000 * 60 * 60 * 24));
        const durationDays = Math.max(1, endDayOffset - startDayOffset + 1);
        
        const startOffset = startDayOffset * ganttScale;
        const duration = durationDays * ganttScale;
        
        // CALCULAR AVANCE PROGRAMADO DE ESTA TAREA
        let scheduledProgress = 0;
        const startDate = new Date(start);
        const endDate = new Date(end);
        startDate.setHours(0, 0, 0, 0);
        endDate.setHours(23, 59, 59, 999);
        
        if (today >= endDate) {
            // Ya pasó la fecha de fin, debería estar al 100%
            scheduledProgress = 100;
        } else if (today >= startDate) {
            // Estamos dentro del rango de la tarea
            // Calcular días totales (incluye día inicio y fin)
            const totalDaysTask = Math.floor((endDate - startDate) / (1000 * 60 * 60 * 24)) + 1;
            // Días transcurridos desde el inicio hasta hoy
            const elapsedDays = Math.floor((today - startDate) / (1000 * 60 * 60 * 24)) + 1;
            scheduledProgress = Math.min(100, Math.round((elapsedDays / totalDaysTask) * 100));
        }
        // Si today < startDate, scheduledProgress = 0 (aún no ha comenzado)
        
        // CALCULAR EFECTIVIDAD DE LA TAREA
        let taskEffectiveness = 100;
        if (scheduledProgress > 0) {
            taskEffectiveness = Math.round((task.progress / scheduledProgress) * 100);
        } else if (task.progress > 0) {
            taskEffectiveness = 100; // Adelantado si tiene progreso antes de empezar
        }
        
        // Determinar color de efectividad
        let effectivenessColor = '#10b981'; // verde
        let effectivenessIcon = '🚀';
        if (taskEffectiveness < 100) {
            effectivenessColor = '#ef4444'; // rojo
            effectivenessIcon = '⚠️';
        } else if (taskEffectiveness === 100) {
            effectivenessColor = '#f59e0b'; // amarillo/naranja
            effectivenessIcon = '✅';
        }
        
        console.log(`Tarea: ${task.title}, Start: ${start.toDateString()}, End: ${end.toDateString()}, Programado: ${scheduledProgress}%, Real: ${task.progress}%, Efectividad: ${taskEffectiveness}%`);
        
        // Get assignee name
        const assignee = task.assignee_id ? users.find(u => u.id === task.assignee_id) : null;
        const assigneeName = assignee ? assignee.name : 'Sin asignar';
        
        // Formatear fechas para mostrar
        const startDateStr = task.start_date ? new Date(task.start_date).toLocaleDateString('es-ES', {day: '2-digit', month: 'short'}) : '';
        const endDateStr = task.due_date ? new Date(task.due_date).toLocaleDateString('es-ES', {day: '2-digit', month: 'short'}) : '';
        
        // Color según estado
        const barColor = colors[task.status] || '#64748b';
        
        return `
            <div class="gantt-task-row">
                <div class="gantt-task-info">
                    <span class="priority-dot ${task.priority}"></span>
                    <div class="gantt-task-details">
                        <span class="gantt-task-name">${task.title}</span>
                        <span class="gantt-task-assignee"><i class="fas fa-user"></i> ${assigneeName}</span>
                        <span class="gantt-task-dates"><i class="fas fa-calendar"></i> ${startDateStr} - ${endDateStr}</span>
                    </div>
                </div>
                <div class="gantt-task-bar-container" style="width: ${totalDays * ganttScale}px;">
                    ${todayIndex >= 0 ? `<div class="gantt-today-line" style="left: ${(todayIndex * ganttScale) + (ganttScale / 2)}px;"></div>` : ''}
                    <div style="position: absolute; left: ${startOffset}px; width: ${duration}px; height: 36px; top: 2px; background: ${barColor}; border-radius: 6px; display: flex; flex-direction: column; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.2); overflow: hidden;" 
                         class="gantt-task-bar"
                         data-id="${task.id}" 
                         title="📅 Prog: ${scheduledProgress}% | ✅ Real: ${task.progress}% | ${effectivenessIcon} Efect: ${taskEffectiveness}%">
                        <!-- Barra de progreso programado (fondo gris más oscuro) -->
                        <div style="position: absolute; left: 0; top: 0; height: 100%; width: ${scheduledProgress}%; background: rgba(0,0,0,0.3); border-radius: 6px 0 0 6px;"></div>
                        <!-- Barra de progreso real (overlay brillante) -->
                        <div style="position: absolute; left: 0; top: 0; height: 100%; width: ${task.progress}%; background: rgba(255,255,255,0.35); border-radius: 6px 0 0 6px;"></div>
                        <!-- Indicadores de texto -->
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 2px 8px; position: relative; z-index: 1; height: 100%;">
                            <span style="color: rgba(255,255,255,0.8); font-size: 0.65rem; text-shadow: 0 1px 2px rgba(0,0,0,0.5);">📅${scheduledProgress}%</span>
                            <span style="color: white; font-size: 0.8rem; font-weight: bold; text-shadow: 0 1px 2px rgba(0,0,0,0.5);">${task.progress}%</span>
                        </div>
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

// ===================== ADMIN FUNCTIONS =====================
async function loadPendingUsers() {
    if (!currentUser || !currentUser.is_admin) return;
    
    try {
        const pending = await apiRequest('/api/admin/pending-users');
        renderPendingUsers(pending);
        updatePendingBadge(pending.length);
    } catch (error) {
        console.error('Error loading pending users:', error);
    }
}

async function loadAllUsersAdmin() {
    if (!currentUser || !currentUser.is_admin) return;
    
    try {
        const allUsers = await apiRequest('/api/admin/all-users');
        renderAllUsersAdmin(allUsers);
    } catch (error) {
        console.error('Error loading users:', error);
    }
}

function renderPendingUsers(users) {
    const container = document.getElementById('pending-users-list');
    
    if (users.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-check-circle"></i>
                <p>No hay usuarios pendientes de aprobación</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = users.map(user => `
        <div class="user-card" data-user-id="${user.id}">
            <div class="user-card-info">
                <div class="avatar" style="background: ${user.avatar_color}">
                    ${getInitials(user.name)}
                </div>
                <div class="user-card-details">
                    <h4>${user.name}</h4>
                    <p>${user.email}</p>
                    <div class="user-card-meta">
                        <span class="user-badge pending">Pendiente</span>
                        <small>Registrado: ${formatDateTime(user.created_at)}</small>
                    </div>
                </div>
            </div>
            <div class="user-card-actions">
                <button class="btn-approve" onclick="approveUser(${user.id})">
                    <i class="fas fa-check"></i> Aprobar
                </button>
                <button class="btn-reject" onclick="rejectUser(${user.id})">
                    <i class="fas fa-times"></i> Rechazar
                </button>
            </div>
        </div>
    `).join('');
}

function renderAllUsersAdmin(allUsers) {
    const container = document.getElementById('all-users-list');
    
    container.innerHTML = allUsers.map(user => {
        const isCurrentUser = user.id === currentUser.id;
        
        return `
        <div class="user-card" data-user-id="${user.id}">
            <div class="user-card-info">
                <div class="avatar" style="background: ${user.avatar_color}">
                    ${getInitials(user.name)}
                </div>
                <div class="user-card-details">
                    <h4>${user.name} ${isCurrentUser ? '<small>(Tú)</small>' : ''}</h4>
                    <p>${user.email}</p>
                    <div class="user-card-meta">
                        ${user.is_admin ? '<span class="user-badge admin">Administrador</span>' : '<span class="user-badge user">Usuario</span>'}
                        ${user.is_approved ? '' : '<span class="user-badge pending">Pendiente</span>'}
                    </div>
                </div>
            </div>
            <div class="user-card-actions">
                <button class="btn-edit-user" onclick="openEditUserModal(${user.id}, '${user.name.replace(/'/g, "\\'") }', '${user.email}', ${user.is_admin})">
                    <i class="fas fa-edit"></i> Editar
                </button>
                ${!isCurrentUser && user.is_approved ? `
                    ${user.is_admin ? `
                        <button class="btn-remove-admin" onclick="removeAdmin(${user.id})">
                            <i class="fas fa-user"></i> Quitar Admin
                        </button>
                    ` : `
                        <button class="btn-make-admin" onclick="makeAdmin(${user.id})">
                            <i class="fas fa-crown"></i> Hacer Admin
                        </button>
                    `}
                ` : ''}
                ${!isCurrentUser ? `
                    <button class="btn-reject" onclick="deleteUser(${user.id})">
                        <i class="fas fa-trash"></i>
                    </button>
                ` : ''}
            </div>
        </div>
    `}).join('');
}

function updatePendingBadge(count) {
    const badge = document.querySelector('.nav-item[data-view="admin"] .badge');
    const pendingBadge = document.getElementById('pending-badge');
    
    if (count > 0) {
        badge.textContent = count;
        badge.classList.remove('hidden');
        pendingBadge.textContent = count;
    } else {
        badge.classList.add('hidden');
        pendingBadge.textContent = '0';
    }
}

async function approveUser(userId) {
    try {
        await apiRequest(`/api/admin/users/${userId}/approve`, {
            method: 'PUT',
            body: JSON.stringify({ approved: true })
        });
        showToast('Usuario aprobado correctamente', 'success');
        loadPendingUsers();
        loadUsers();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function rejectUser(userId) {
    if (!confirm('¿Seguro que deseas rechazar y eliminar este usuario?')) return;
    
    try {
        await apiRequest(`/api/admin/users/${userId}/approve`, {
            method: 'PUT',
            body: JSON.stringify({ approved: false })
        });
        showToast('Usuario rechazado', 'warning');
        loadPendingUsers();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function makeAdmin(userId) {
    if (!confirm('¿Seguro que deseas hacer administrador a este usuario?')) return;
    
    try {
        await apiRequest(`/api/admin/users/${userId}/make-admin`, {
            method: 'PUT'
        });
        showToast('Usuario promovido a administrador', 'success');
        loadAllUsersAdmin();
        loadUsers();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function removeAdmin(userId) {
    if (!confirm('¿Seguro que deseas quitar el rol de administrador a este usuario?')) return;
    
    try {
        await apiRequest(`/api/admin/users/${userId}/remove-admin`, {
            method: 'PUT'
        });
        showToast('Rol de administrador removido', 'success');
        loadAllUsersAdmin();
        loadUsers();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// Editar Usuario
function openEditUserModal(userId, name, email, isAdmin) {
    document.getElementById('edit-user-id').value = userId;
    document.getElementById('edit-user-name').value = name;
    document.getElementById('edit-user-email').value = email;
    document.getElementById('edit-user-password').value = '';
    document.getElementById('edit-user-role').value = isAdmin ? 'admin' : 'user';
    
    // Si es el usuario actual, deshabilitar el cambio de rol
    const roleSelect = document.getElementById('edit-user-role');
    if (userId === currentUser.id) {
        roleSelect.disabled = true;
        roleSelect.title = 'No puedes cambiar tu propio rol';
    } else {
        roleSelect.disabled = false;
        roleSelect.title = '';
    }
    
    document.getElementById('edit-user-modal').classList.add('active');
}

async function saveUserChanges(e) {
    e.preventDefault();
    
    const userId = document.getElementById('edit-user-id').value;
    const name = document.getElementById('edit-user-name').value;
    const email = document.getElementById('edit-user-email').value;
    const password = document.getElementById('edit-user-password').value;
    const isAdmin = document.getElementById('edit-user-role').value === 'admin';
    
    try {
        const updateData = { name, email, is_admin: isAdmin };
        if (password) {
            updateData.password = password;
        }
        
        await apiRequest(`/api/admin/users/${userId}`, {
            method: 'PUT',
            body: JSON.stringify(updateData)
        });
        
        showToast('Usuario actualizado correctamente', 'success');
        document.getElementById('edit-user-modal').classList.remove('active');
        loadAllUsersAdmin();
        loadUsers();
        
        // Si el usuario editado es el actual, actualizar la UI
        if (parseInt(userId) === currentUser.id) {
            currentUser.name = name;
            currentUser.email = email;
            document.querySelector('#user-info .user-name').textContent = name;
            document.querySelector('#user-info .user-email').textContent = email;
        }
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function deleteUser(userId) {
    if (!confirm('¿Seguro que deseas eliminar este usuario? Esta acción no se puede deshacer.')) return;
    
    try {
        await apiRequest(`/api/admin/users/${userId}`, {
            method: 'DELETE'
        });
        showToast('Usuario eliminado', 'success');
        loadAllUsersAdmin();
        loadPendingUsers();
        loadUsers();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ===================== PROGRESS FUNCTIONS =====================
let currentProgressTaskId = null;

function setupProgressForm() {
    const progressSlider = document.getElementById('new-progress');
    if (progressSlider) {
        progressSlider.addEventListener('input', (e) => {
            document.getElementById('new-progress-value').textContent = e.target.value;
        });
    }
    
    const progressForm = document.getElementById('progress-form');
    if (progressForm) {
        progressForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await submitProgress();
        });
    }
    
    const editUserForm = document.getElementById('edit-user-form');
    if (editUserForm) {
        editUserForm.addEventListener('submit', saveUserChanges);
    }
}

function openProgressModal(task) {
    currentProgressTaskId = task.id;
    document.getElementById('progress-task-id').value = task.id;
    document.getElementById('progress-task-title').textContent = task.title;
    document.getElementById('progress-current').querySelector('span').textContent = `${task.progress || 0}%`;
    document.getElementById('new-progress').value = task.progress || 0;
    document.getElementById('new-progress-value').textContent = task.progress || 0;
    document.getElementById('progress-comment').value = '';
    
    openModal('progress-modal');
}

async function submitProgress() {
    const taskId = document.getElementById('progress-task-id').value;
    const progress = parseFloat(document.getElementById('new-progress').value);
    const comment = document.getElementById('progress-comment').value;
    
    try {
        await apiRequest(`/api/tasks/${taskId}/progress`, {
            method: 'POST',
            body: JSON.stringify({ progress, comment })
        });
        
        showToast('Avance registrado correctamente', 'success');
        closeModal('progress-modal');
        loadTasks();
        loadDashboard();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function openProgressHistory() {
    if (!currentProgressTaskId) return;
    
    try {
        const history = await apiRequest(`/api/tasks/${currentProgressTaskId}/progress`);
        renderProgressHistory(history);
        closeModal('progress-modal');
        openModal('history-modal');
    } catch (error) {
        showToast('Error cargando historial', 'error');
    }
}

function renderProgressHistory(history) {
    const container = document.getElementById('history-content');
    
    if (history.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-clipboard-list"></i>
                <p>No hay registros de avance</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = history.map(item => `
        <div class="history-item">
            <div class="history-avatar" style="background: ${getRandomColor(item.user_name)}">
                ${getInitials(item.user_name)}
            </div>
            <div class="history-details">
                <div class="history-header">
                    <span class="history-user">${item.user_name}</span>
                    <span class="history-date">${formatDateTime(item.created_at)}</span>
                </div>
                <div class="history-progress">
                    <div class="history-progress-change">
                        <span class="old">${item.previous_progress}%</span>
                        <span class="arrow">→</span>
                        <span class="new">${item.new_progress}%</span>
                    </div>
                </div>
                ${item.comment ? `<div class="history-comment">"${item.comment}"</div>` : ''}
            </div>
        </div>
    `).join('');
}

function getRandomColor(name) {
    const colors = ['#6366f1', '#8b5cf6', '#ec4899', '#ef4444', '#f59e0b', '#10b981', '#06b6d4', '#3b82f6'];
    const index = name.charCodeAt(0) % colors.length;
    return colors[index];
}

document.querySelectorAll('.modal-overlay').forEach(overlay => {
    overlay.addEventListener('click', (e) => {
        if (e.target === overlay) {
            overlay.classList.remove('active');
        }
    });
});

// ===================== SEARCH =====================
document.getElementById('search-input').addEventListener('input', (e) => {
    const query = e.target.value.toLowerCase().trim();
    
    // Si no hay búsqueda, mostrar todas las tarjetas
    if (!query) {
        document.querySelectorAll('.task-card').forEach(card => {
            card.style.display = 'flex';
        });
        return;
    }
    
    // Buscar en las tarjetas del Kanban
    document.querySelectorAll('.task-card').forEach(card => {
        const titleEl = card.querySelector('.task-title');
        const descEl = card.querySelector('.task-description');
        
        const title = titleEl ? titleEl.textContent.toLowerCase() : '';
        const desc = descEl ? descEl.textContent.toLowerCase() : '';
        
        const matches = title.includes(query) || desc.includes(query);
        card.style.display = matches ? 'flex' : 'none';
    });
    
    // También buscar en la lista de "Mis Tareas"
    document.querySelectorAll('.my-task-item').forEach(item => {
        const titleEl = item.querySelector('.my-task-title');
        const descEl = item.querySelector('.my-task-desc');
        
        const title = titleEl ? titleEl.textContent.toLowerCase() : '';
        const desc = descEl ? descEl.textContent.toLowerCase() : '';
        
        const matches = title.includes(query) || desc.includes(query);
        item.style.display = matches ? 'flex' : 'none';
    });
});

// ===================== MOBILE MENU =====================
document.querySelector('.mobile-menu-toggle').addEventListener('click', () => {
    document.querySelector('.sidebar').classList.toggle('open');
});

// ===================== REPORTES PDF =====================
async function downloadReport(url, filename) {
    const token = getToken();
    
    try {
        const response = await fetch(url, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error('Error al generar el reporte');
        }
        
        const blob = await response.blob();
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);
        
        showToast('Reporte descargado exitosamente', 'success');
    } catch (error) {
        showToast('Error al descargar el reporte: ' + error.message, 'error');
    }
}

document.getElementById('download-general-report').addEventListener('click', async function() {
    const btn = this;
    const originalContent = btn.innerHTML;
    
    btn.classList.add('downloading');
    btn.innerHTML = '<i class="fas fa-spinner"></i><span>Generando...</span>';
    
    const fecha = new Date().toISOString().split('T')[0].replace(/-/g, '');
    await downloadReport('/api/reports/general', `Reporte_General_${fecha}.pdf`);
    
    btn.classList.remove('downloading');
    btn.innerHTML = originalContent;
});

document.getElementById('download-project-report').addEventListener('click', async function() {
    if (!currentProject) {
        showToast('Selecciona un proyecto primero', 'warning');
        return;
    }
    
    const btn = this;
    const originalContent = btn.innerHTML;
    
    btn.classList.add('downloading');
    btn.innerHTML = '<i class="fas fa-spinner"></i><span>Generando...</span>';
    
    const fecha = new Date().toISOString().split('T')[0].replace(/-/g, '');
    const projectName = currentProject.name.replace(/\s+/g, '_');
    await downloadReport(`/api/reports/project/${currentProject.id}`, `Reporte_${projectName}_${fecha}.pdf`);
    
    btn.classList.remove('downloading');
    btn.innerHTML = originalContent;
});

// Mostrar/ocultar botón de reporte de proyecto según el contexto
function updateProjectReportButton() {
    const btn = document.getElementById('download-project-report');
    if (currentProject) {
        btn.style.display = 'flex';
    } else {
        btn.style.display = 'none';
    }
}

// ===================== GANTT NAVIGATION =====================
let ganttCurrentDate = new Date();

function updateGanttDateDisplay() {
    const monthNames = ['Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio', 'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];
    document.getElementById('gantt-date-display').textContent = `${monthNames[ganttCurrentDate.getMonth()]} ${ganttCurrentDate.getFullYear()}`;
}

document.getElementById('gantt-prev-month').addEventListener('click', () => {
    const container = document.querySelector('.gantt-container');
    const scrollAmount = ganttScale * 30; // Aproximadamente un mes
    container.scrollBy({ left: -scrollAmount, behavior: 'smooth' });
    ganttCurrentDate.setMonth(ganttCurrentDate.getMonth() - 1);
    updateGanttDateDisplay();
});

document.getElementById('gantt-next-month').addEventListener('click', () => {
    const container = document.querySelector('.gantt-container');
    const scrollAmount = ganttScale * 30;
    container.scrollBy({ left: scrollAmount, behavior: 'smooth' });
    ganttCurrentDate.setMonth(ganttCurrentDate.getMonth() + 1);
    updateGanttDateDisplay();
});

// Habilitar scroll horizontal con shift+wheel
document.querySelector('.gantt-container')?.addEventListener('wheel', (e) => {
    if (e.shiftKey) {
        e.preventDefault();
        const container = e.currentTarget;
        container.scrollLeft += e.deltaY;
    }
});

// Inicializar display de fecha del Gantt
updateGanttDateDisplay();

// ===================== TEMPLATES =====================
let stageTemplates = [];
let taskTemplates = [];

async function loadTemplates() {
    try {
        console.log('Cargando plantillas...');
        stageTemplates = await apiRequest('/api/templates/stages');
        console.log('Plantillas de etapas:', stageTemplates);
        taskTemplates = await apiRequest('/api/templates/tasks');
        console.log('Plantillas de tareas:', taskTemplates);
        renderStageTemplates();
        renderTaskTemplates();
    } catch (error) {
        console.error('Error loading templates:', error);
        // Mostrar mensaje de error en la UI
        const stageContainer = document.getElementById('stage-templates-list');
        const taskContainer = document.getElementById('task-templates-list');
        const errorHtml = `
            <div class="empty-state">
                <i class="fas fa-exclamation-triangle" style="color: var(--warning);"></i>
                <p>Error al cargar plantillas</p>
                <small style="color: var(--text-muted);">Verifica la conexión con el servidor</small>
            </div>
        `;
        if (stageContainer) stageContainer.innerHTML = errorHtml;
        if (taskContainer) taskContainer.innerHTML = errorHtml;
    }
}

function renderStageTemplates() {
    const container = document.getElementById('stage-templates-list');
    if (!container) {
        console.error('Container stage-templates-list no encontrado');
        return;
    }
    if (!stageTemplates.length) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-folder-open"></i>
                <p>No hay plantillas de etapas</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = stageTemplates.map(template => `
        <div class="template-card">
            <div class="template-card-header">
                <h5>${template.name}</h5>
                <div class="template-card-actions">
                    <button class="btn-icon" onclick="openApplyTemplateModal(${template.id}, 'stage')" title="Aplicar">
                        <i class="fas fa-play"></i>
                    </button>
                    <button class="btn-icon" onclick="deleteStageTemplate(${template.id})" title="Eliminar">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <p class="template-card-description">${template.description || 'Sin descripción'}</p>
            <div class="template-card-items">
                ${template.stages.slice(0, 4).map(s => `<span class="template-item-badge">${s.name} (${s.percentage}%)</span>`).join('')}
                ${template.stages.length > 4 ? `<span class="template-item-badge">+${template.stages.length - 4} más</span>` : ''}
            </div>
            <div class="template-card-footer">
                <span class="template-card-meta">${template.stages.length} etapas</span>
                <button class="btn btn-sm btn-primary" onclick="openApplyTemplateModal(${template.id}, 'stage')">
                    <i class="fas fa-copy"></i> Aplicar
                </button>
            </div>
        </div>
    `).join('');
}

function renderTaskTemplates() {
    const container = document.getElementById('task-templates-list');
    if (!container) {
        console.error('Container task-templates-list no encontrado');
        return;
    }
    if (!taskTemplates.length) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-folder-open"></i>
                <p>No hay plantillas de tareas</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = taskTemplates.map(template => `
        <div class="template-card">
            <div class="template-card-header">
                <h5>${template.name}</h5>
                <div class="template-card-actions">
                    <button class="btn-icon" onclick="openApplyTemplateModal(${template.id}, 'task')" title="Aplicar">
                        <i class="fas fa-play"></i>
                    </button>
                    <button class="btn-icon" onclick="deleteTaskTemplate(${template.id})" title="Eliminar">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <p class="template-card-description">${template.description || 'Sin descripción'}</p>
            <div class="template-card-items">
                ${template.tasks.slice(0, 3).map(t => `<span class="template-item-badge">${t.title}</span>`).join('')}
                ${template.tasks.length > 3 ? `<span class="template-item-badge">+${template.tasks.length - 3} más</span>` : ''}
            </div>
            <div class="template-card-footer">
                <span class="template-card-meta">${template.tasks.length} tareas</span>
                <button class="btn btn-sm btn-primary" onclick="openApplyTemplateModal(${template.id}, 'task')">
                    <i class="fas fa-copy"></i> Aplicar
                </button>
            </div>
        </div>
    `).join('');
}

// Stage Template Modal
function openStageTemplateModal() {
    document.getElementById('stage-template-name').value = '';
    document.getElementById('stage-template-description').value = '';
    document.getElementById('stage-template-items').innerHTML = '';
    document.getElementById('stage-template-total').textContent = '0';
    addStageTemplateItem();
    document.getElementById('stage-template-modal').classList.add('active');
}

function addStageTemplateItem() {
    const container = document.getElementById('stage-template-items');
    const item = document.createElement('div');
    item.className = 'template-item-row';
    item.innerHTML = `
        <input type="text" placeholder="Nombre de la etapa" class="stage-item-name" required>
        <input type="number" placeholder="%" class="stage-item-percentage" min="0" max="100" step="0.5" onchange="updateStageTotal()">
        <button type="button" class="btn-icon" onclick="this.parentElement.remove(); updateStageTotal();">
            <i class="fas fa-times"></i>
        </button>
    `;
    container.appendChild(item);
}

function updateStageTotal() {
    const percentages = document.querySelectorAll('.stage-item-percentage');
    let total = 0;
    percentages.forEach(input => {
        total += parseFloat(input.value) || 0;
    });
    const totalEl = document.getElementById('stage-template-total');
    totalEl.textContent = total.toFixed(1);
    totalEl.style.color = Math.abs(total - 100) < 0.1 ? 'var(--success)' : 'var(--danger)';
}

document.getElementById('stage-template-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const stages = [];
    const rows = document.querySelectorAll('#stage-template-items .template-item-row');
    rows.forEach((row, idx) => {
        const name = row.querySelector('.stage-item-name').value;
        const percentage = parseFloat(row.querySelector('.stage-item-percentage').value) || 0;
        if (name) {
            stages.push({ name, percentage, position: idx });
        }
    });
    
    if (stages.length === 0) {
        showToast('Agrega al menos una etapa', 'warning');
        return;
    }
    
    try {
        await apiRequest('/api/templates/stages', {
            method: 'POST',
            body: JSON.stringify({
                name: document.getElementById('stage-template-name').value,
                description: document.getElementById('stage-template-description').value,
                stages
            })
        });
        showToast('Plantilla de etapas creada', 'success');
        document.getElementById('stage-template-modal').classList.remove('active');
        loadTemplates();
    } catch (error) {
        showToast(error.message, 'error');
    }
});

// Task Template Modal
function openTaskTemplateModal() {
    document.getElementById('task-template-name').value = '';
    document.getElementById('task-template-description').value = '';
    document.getElementById('task-template-items').innerHTML = '';
    addTaskTemplateItem();
    document.getElementById('task-template-modal').classList.add('active');
}

function addTaskTemplateItem() {
    const container = document.getElementById('task-template-items');
    const item = document.createElement('div');
    item.className = 'template-item-row';
    item.innerHTML = `
        <input type="text" placeholder="Título de la tarea" class="task-item-title" required style="flex: 2;">
        <select class="task-item-priority">
            <option value="low">Baja</option>
            <option value="medium" selected>Media</option>
            <option value="high">Alta</option>
        </select>
        <input type="number" placeholder="Días" class="task-item-days" min="1" value="7" style="width: 70px;">
        <button type="button" class="btn-icon" onclick="this.parentElement.remove();">
            <i class="fas fa-times"></i>
        </button>
    `;
    container.appendChild(item);
}

document.getElementById('task-template-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const tasks = [];
    const rows = document.querySelectorAll('#task-template-items .template-item-row');
    rows.forEach((row, idx) => {
        const title = row.querySelector('.task-item-title').value;
        const priority = row.querySelector('.task-item-priority').value;
        const days = parseInt(row.querySelector('.task-item-days').value) || 7;
        if (title) {
            tasks.push({ title, priority, duration_days: days, position: idx });
        }
    });
    
    if (tasks.length === 0) {
        showToast('Agrega al menos una tarea', 'warning');
        return;
    }
    
    try {
        await apiRequest('/api/templates/tasks', {
            method: 'POST',
            body: JSON.stringify({
                name: document.getElementById('task-template-name').value,
                description: document.getElementById('task-template-description').value,
                tasks
            })
        });
        showToast('Plantilla de tareas creada', 'success');
        document.getElementById('task-template-modal').classList.remove('active');
        loadTemplates();
    } catch (error) {
        showToast(error.message, 'error');
    }
});

// Apply Template
async function openApplyTemplateModal(templateId, type) {
    document.getElementById('apply-template-id').value = templateId;
    document.getElementById('apply-template-type').value = type;
    document.getElementById('apply-template-title').innerHTML = type === 'stage' 
        ? '<i class="fas fa-layer-group"></i> Aplicar Plantilla de Etapas'
        : '<i class="fas fa-tasks"></i> Aplicar Plantilla de Tareas';
    
    // Cargar proyectos
    const select = document.getElementById('apply-template-project');
    select.innerHTML = '<option value="">Seleccionar proyecto...</option>' + 
        projects.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
    
    // Mostrar selector de etapa solo para plantillas de tareas
    const stageGroup = document.getElementById('apply-template-stage-group');
    if (type === 'task') {
        stageGroup.classList.remove('hidden');
    } else {
        stageGroup.classList.add('hidden');
    }
    
    document.getElementById('apply-template-modal').classList.add('active');
}

// Cargar etapas cuando se selecciona un proyecto
document.getElementById('apply-template-project')?.addEventListener('change', async (e) => {
    const projectId = e.target.value;
    const stageSelect = document.getElementById('apply-template-stage');
    
    if (projectId && document.getElementById('apply-template-type').value === 'task') {
        try {
            const stages = await apiRequest(`/api/projects/${projectId}/stages`);
            stageSelect.innerHTML = '<option value="">Sin etapa específica</option>' +
                stages.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
        } catch (error) {
            console.error('Error loading stages:', error);
        }
    }
});

async function applyTemplate() {
    const templateId = document.getElementById('apply-template-id').value;
    const type = document.getElementById('apply-template-type').value;
    const projectId = document.getElementById('apply-template-project').value;
    const stageId = document.getElementById('apply-template-stage').value;
    
    if (!projectId) {
        showToast('Selecciona un proyecto', 'warning');
        return;
    }
    
    try {
        let url = type === 'stage' 
            ? `/api/projects/${projectId}/apply-stage-template/${templateId}`
            : `/api/projects/${projectId}/apply-task-template/${templateId}${stageId ? `?stage_id=${stageId}` : ''}`;
        
        const result = await apiRequest(url, { method: 'POST' });
        showToast(result.message, 'success');
        document.getElementById('apply-template-modal').classList.remove('active');
        
        // Recargar datos si es el proyecto actual
        if (currentProject && currentProject.id == projectId) {
            await loadProjectData(projectId);
        }
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function deleteStageTemplate(templateId) {
    if (!confirm('¿Estás seguro de eliminar esta plantilla?')) return;
    
    try {
        await apiRequest(`/api/templates/stages/${templateId}`, { method: 'DELETE' });
        showToast('Plantilla eliminada', 'success');
        loadTemplates();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function deleteTaskTemplate(templateId) {
    if (!confirm('¿Estás seguro de eliminar esta plantilla?')) return;
    
    try {
        await apiRequest(`/api/templates/tasks/${templateId}`, { method: 'DELETE' });
        showToast('Plantilla eliminada', 'success');
        loadTemplates();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ===================== ADMIN TEAMS =====================
let adminTeams = [];

async function loadAdminTeams() {
    try {
        adminTeams = await apiRequest('/api/admin/teams');
        renderAdminTeams();
    } catch (error) {
        console.error('Error loading admin teams:', error);
    }
}

function renderAdminTeams() {
    const container = document.getElementById('teams-grid');
    if (!adminTeams.length) {
        container.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-users"></i>
                <p>No hay administradores registrados</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = adminTeams.map(admin => `
        <div class="team-card">
            <div class="team-card-header">
                <div class="team-admin-avatar" style="background: ${admin.avatar_color || '#6366f1'}">
                    ${getInitials(admin.admin_name)}
                </div>
                <div class="team-admin-info">
                    <h4>${admin.admin_name}</h4>
                    <span>${admin.admin_email}</span>
                </div>
            </div>
            <div class="team-members-section">
                <div class="team-members-header">
                    <h5><i class="fas fa-users"></i> Equipo (${admin.team.length})</h5>
                    <button class="btn btn-sm btn-secondary" onclick="openAddTeamMemberModal(${admin.admin_id}, '${admin.admin_name}')">
                        <i class="fas fa-user-plus"></i>
                    </button>
                </div>
                <div class="team-members-list">
                    ${admin.team.length === 0 
                        ? '<div class="team-empty"><i class="fas fa-user-slash"></i> Sin miembros asignados</div>'
                        : admin.team.map(member => `
                            <div class="team-member-item">
                                <div class="team-member-avatar" style="background: ${member.avatar_color || '#6366f1'}">
                                    ${getInitials(member.name)}
                                </div>
                                <div class="team-member-info">
                                    <span>${member.name}</span>
                                    <small>${member.email}</small>
                                </div>
                                <button class="btn-icon" onclick="removeTeamMember(${admin.admin_id}, ${member.id})" title="Remover del equipo">
                                    <i class="fas fa-times"></i>
                                </button>
                            </div>
                        `).join('')}
                </div>
            </div>
        </div>
    `).join('');
}

function openAddTeamMemberModal(adminId, adminName) {
    document.getElementById('team-admin-id').value = adminId;
    document.getElementById('team-admin-name').value = adminName;
    
    // Cargar usuarios disponibles (no admins y no ya en el equipo)
    const adminTeam = adminTeams.find(t => t.admin_id === adminId);
    const teamMemberIds = adminTeam ? adminTeam.team.map(m => m.id) : [];
    
    const availableUsers = users.filter(u => !u.is_admin && !teamMemberIds.includes(u.id));
    
    const select = document.getElementById('team-member-select');
    select.innerHTML = '<option value="">Seleccionar usuario...</option>' +
        availableUsers.map(u => `<option value="${u.id}">${u.name} (${u.email})</option>`).join('');
    
    document.getElementById('add-team-member-modal').classList.add('active');
}

async function addTeamMember() {
    const adminId = document.getElementById('team-admin-id').value;
    const memberId = document.getElementById('team-member-select').value;
    
    if (!memberId) {
        showToast('Selecciona un usuario', 'warning');
        return;
    }
    
    try {
        const result = await apiRequest(`/api/admin/${adminId}/team/${memberId}`, { method: 'POST' });
        showToast(result.message, 'success');
        document.getElementById('add-team-member-modal').classList.remove('active');
        loadAdminTeams();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

async function removeTeamMember(adminId, memberId) {
    if (!confirm('¿Remover este miembro del equipo?')) return;
    
    try {
        const result = await apiRequest(`/api/admin/${adminId}/team/${memberId}`, { method: 'DELETE' });
        showToast(result.message, 'success');
        loadAdminTeams();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

// ===================== EXPONER FUNCIONES GLOBALES =====================
// Exponer funciones para onclick en HTML
window.openStageTemplateModal = openStageTemplateModal;
window.openTaskTemplateModal = openTaskTemplateModal;
window.addStageTemplateItem = addStageTemplateItem;
window.addTaskTemplateItem = addTaskTemplateItem;
window.updateStageTotal = updateStageTotal;
window.openApplyTemplateModal = openApplyTemplateModal;
window.applyTemplate = applyTemplate;
window.deleteStageTemplate = deleteStageTemplate;
window.deleteTaskTemplate = deleteTaskTemplate;
window.openAddTeamMemberModal = openAddTeamMemberModal;
window.addTeamMember = addTeamMember;
window.removeTeamMember = removeTeamMember;
window.openTaskModal = openTaskModal;
window.openProgressModal = openProgressModal;
window.openProgressHistory = openProgressHistory;
window.approveUser = approveUser;
window.rejectUser = rejectUser;
window.toggleUserAdmin = toggleUserAdmin;
window.deleteUser = deleteUser;
window.openEditUserModal = openEditUserModal;
window.editProject = editProject;
window.removeTempStage = removeTempStage;
window.removeAdmin = removeAdmin;
window.makeAdmin = makeAdmin;

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
