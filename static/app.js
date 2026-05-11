// ===================== STATE =====================
let currentUser = null;
let currentProject = null;
let projects = [];
let tasks = [];
let users = [];
let stages = [];  // Etapas del proyecto actual
let milestones = [];  // Hitos del proyecto actual
let ws = null;
let draggedTask = null;
let myTasksCache = [];
let myTasksLoadedAt = 0;
const MY_TASKS_CACHE_TTL_MS = 60000;

const API_BASE = '';

// ===================== UTILS =====================
function getToken() {
    return localStorage.getItem('token');
}

function getStoredUser() {
    try {
        const raw = localStorage.getItem('currentUser');
        return raw ? JSON.parse(raw) : null;
    } catch (e) {
        return null;
    }
}
function toggleGanttStages(event) {
    if (event) event.preventDefault();
    const stagesContainer = document.getElementById('gantt-stages-effectiveness');
    const toggleBtn = document.getElementById('stages-toggle');
    if (!stagesContainer || !toggleBtn) return;
    stagesContainer.classList.toggle('collapsed');
    const collapsedNow = stagesContainer.classList.contains('collapsed');
    localStorage.setItem('gantt-stages-collapsed', collapsedNow ? 'true' : 'false');
    const icon = toggleBtn.querySelector('i');
    if (collapsedNow) {
        icon.classList.remove('fa-chevron-up');
        icon.classList.add('fa-chevron-down');
        toggleBtn.setAttribute('aria-expanded', 'false');
    } else {
        icon.classList.remove('fa-chevron-down');
        icon.classList.add('fa-chevron-up');
        toggleBtn.setAttribute('aria-expanded', 'true');
    }
}

function toggleGanttStageGroup(stageId) {
    const group = document.querySelector(`.gantt-stage-group[data-stage-id="${stageId}"]`);
    if (!group) return;
    group.classList.toggle('collapsed');
    
    // Guardar estado en localStorage
    const collapsedStages = JSON.parse(localStorage.getItem('gantt-collapsed-stages') || '{}');
    collapsedStages[stageId] = group.classList.contains('collapsed');
    localStorage.setItem('gantt-collapsed-stages', JSON.stringify(collapsedStages));
}

function setToken(token) {
    localStorage.setItem('token', token);
}

function setStoredUser(user) {
    try {
        localStorage.setItem('currentUser', JSON.stringify(user));
    } catch (e) {}
}

function clearToken() {
    localStorage.removeItem('token');
}

function clearStoredUser() {
    localStorage.removeItem('currentUser');
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
        clearStoredUser();
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
        setStoredUser(currentUser);
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
    clearStoredUser();
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
    initSidebarToggle();
    
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

function initSidebarToggle() {
    const sidebar = document.querySelector('.sidebar');
    const toggleBtn = document.getElementById('sidebar-toggle');
    if (!sidebar || !toggleBtn) return;

    const isCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
    if (isCollapsed) {
        sidebar.classList.add('collapsed');
    }

    toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('collapsed');
        const collapsedNow = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebar-collapsed', collapsedNow ? 'true' : 'false');
        toggleBtn.setAttribute('title', collapsedNow ? 'Expandir' : 'Contraer');
    });
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
            const adminReports = document.getElementById('admin-reports');
            
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
            adminReports?.classList.toggle('hidden', tabName !== 'reports');
            
            if (tabName === 'pending') {
                loadPendingUsers();
            } else if (tabName === 'all-users') {
                loadAllUsersAdmin();
            } else if (tabName === 'templates') {
                console.log('Cargando plantillas...');
                loadTemplates();
            } else if (tabName === 'teams') {
                loadAdminTeams();
            } else if (tabName === 'reports') {
                loadReportsPanel();
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
        'projects': 'Proyectos',
        'team': 'Equipo',
        'supervision': 'Supervisión',
        'admin': 'Administración'
    };
    document.getElementById('page-title').textContent = titles[view] || view;
    
    if (view === 'my-tasks') loadMyTasks();
    if (view === 'projects') loadProjectsView();
    if (view === 'team') loadTeam();
    if (view === 'gantt') renderGantt();
    if (view === 'admin') loadPendingUsers();
    if (view === 'supervision') renderSupervisionView();
}

// ===================== PROJECTS =====================
async function loadProjects() {
    try {
        projects = await apiRequest('/api/projects');
        renderProjectList();
        updateProjectSelects();
        renderEffectivenessProjectSelect();
    } catch (error) {
        showToast('Error cargando proyectos', 'error');
    }
}

function renderProjectList() {
    const list = document.getElementById('project-list');
    const isAdmin = currentUser && currentUser.is_admin;

    const sortedProjects = [...projects].sort((a, b) => {
        if (a.is_active === b.is_active) return a.name.localeCompare(b.name);
        return a.is_active ? -1 : 1;
    });
    
    list.innerHTML = sortedProjects.map(p => `
        <div class="project-item ${currentProject?.id === p.id ? 'active' : ''} ${p.is_active ? '' : 'inactive'}" data-id="${p.id}">
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

async function deleteProject(projectId, projectName) {
    if (!confirm(`¿Estás seguro de que deseas eliminar el proyecto "${projectName}"?\n\nEsta acción eliminará todas las etapas, tareas e historial asociados y no se puede deshacer.`)) {
        return;
    }

    try {
        await apiRequest(`/api/projects/${projectId}`, { method: 'DELETE' });
        showToast('Proyecto eliminado correctamente', 'success');

        // Si el proyecto eliminado era el seleccionado, limpiar selección
        if (currentProject && currentProject.id === projectId) {
            currentProject = null;
            stages = [];
            tasks = [];
        }

        await loadProjects();
        loadDashboard();
    } catch (error) {
        showToast(error.message || 'Error al eliminar el proyecto', 'error');
    }
}

function updateProjectSelects() {
    const activeProjects = projects.filter(p => p.is_active);
    let options = activeProjects.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
    if (currentProject && !currentProject.is_active) {
        options = `<option value="${currentProject.id}">${currentProject.name} (Inactivo)</option>` + options;
    }
    
    ['kanban-project-select', 'gantt-project-select'].forEach(id => {
        const select = document.getElementById(id);
        select.innerHTML = '<option value="">Seleccionar proyecto</option>' + options;
        if (currentProject) select.value = currentProject.id;
    });
}

async function selectProject(projectId) {
    currentProject = projects.find(p => p.id === projectId);
    
    // Toggle leader class para mostrar/ocultar botones de crear tareas
    if (currentProject && currentUser && currentProject.leader_id === currentUser.id) {
        document.body.classList.add('is-project-leader');
    } else {
        document.body.classList.remove('is-project-leader');
    }
    
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
        <div class="stage-item" data-index="${index}" draggable="true">
            <span class="stage-drag-handle"><i class="fas fa-grip-vertical"></i></span>
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
    
    // Agregar eventos de drag & drop
    initStageDragAndDrop();
    updateStagesTotalDisplay();
}

// ===================== DRAG & DROP PARA ETAPAS =====================
function initStageDragAndDrop() {
    const container = document.getElementById('project-stages-container');
    if (!container) return;
    
    const items = container.querySelectorAll('.stage-item');
    let draggedItem = null;
    
    items.forEach(item => {
        item.addEventListener('dragstart', (e) => {
            draggedItem = item;
            item.classList.add('dragging');
            e.dataTransfer.effectAllowed = 'move';
            e.dataTransfer.setData('text/plain', item.dataset.index);
        });
        
        item.addEventListener('dragend', () => {
            item.classList.remove('dragging');
            items.forEach(i => i.classList.remove('drag-over'));
            draggedItem = null;
        });
        
        item.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            if (item !== draggedItem) {
                item.classList.add('drag-over');
            }
        });
        
        item.addEventListener('dragleave', () => {
            item.classList.remove('drag-over');
        });
        
        item.addEventListener('drop', (e) => {
            e.preventDefault();
            item.classList.remove('drag-over');
            
            if (draggedItem && item !== draggedItem) {
                const fromIndex = parseInt(draggedItem.dataset.index);
                const toIndex = parseInt(item.dataset.index);
                
                // Reordenar el array de etapas
                const [movedStage] = tempStages.splice(fromIndex, 1);
                tempStages.splice(toIndex, 0, movedStage);
                
                renderStagesList();
                showToast('Etapa reordenada', 'success');
            }
        });
    });
}

// ===================== PLANTILLAS DE ETAPAS EN PROYECTO =====================
async function loadStageTemplatesSelector() {
    const select = document.getElementById('stage-template-select');
    if (!select) return;
    
    // Si no hay plantillas cargadas, cargarlas primero
    if (!stageTemplates || stageTemplates.length === 0) {
        try {
            stageTemplates = await apiRequest('/api/templates/stages');
        } catch (error) {
            console.error('Error cargando plantillas de etapas:', error);
            stageTemplates = [];
        }
    }
    
    select.innerHTML = '<option value="">-- Cargar desde plantilla (opcional) --</option>';
    
    stageTemplates.forEach(template => {
        const option = document.createElement('option');
        option.value = template.id;
        option.textContent = `${template.name} (${template.items?.length || 0} etapas)`;
        select.appendChild(option);
    });
}

function applyStageTemplateToProject() {
    const select = document.getElementById('stage-template-select');
    if (!select) return;
    
    const templateId = parseInt(select.value);
    if (!templateId) {
        showToast('Selecciona una plantilla primero', 'warning');
        return;
    }
    
    const template = stageTemplates.find(t => t.id === templateId);
    if (!template || !template.items || template.items.length === 0) {
        showToast('La plantilla no tiene etapas', 'error');
        return;
    }
    
    // Preguntar si desea agregar o reemplazar
    const action = tempStages.length > 0 
        ? confirm('¿Deseas REEMPLAZAR las etapas actuales? (Cancelar para AGREGAR al final)')
        : true;
    
    if (action === true || action === null) {
        // Reemplazar
        tempStages = template.items.map(item => ({
            name: item.name,
            percentage: item.percentage,
            start_date: '',
            end_date: ''
        }));
    } else {
        // Agregar al final
        template.items.forEach(item => {
            tempStages.push({
                name: item.name,
                percentage: item.percentage,
                start_date: '',
                end_date: ''
            });
        });
    }
    
    renderStagesList();
    showToast(`Plantilla "${template.name}" aplicada`, 'success');
    select.value = '';
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

// Event listener para aplicar plantilla de etapas
document.getElementById('apply-stage-template-btn')?.addEventListener('click', applyStageTemplateToProject);

// Toggle para mostrar proyectos inactivos
document.getElementById('show-inactive-projects')?.addEventListener('change', () => {
    updateFilterCount();
    loadProjectsView();
});

// Filtro por tipología
document.getElementById('filter-typology')?.addEventListener('change', () => {
    updateFilterCount();
    loadProjectsView();
});

// Filtro por modalidad de trabajo
document.getElementById('filter-modality')?.addEventListener('change', () => {
    updateFilterCount();
    loadProjectsView();
});

// Filtros de permisología
document.getElementById('filter-perm-suelo')?.addEventListener('change', () => {
    updateFilterCount();
    loadProjectsView();
});
document.getElementById('filter-perm-topografico')?.addEventListener('change', () => {
    updateFilterCount();
    loadProjectsView();
});
document.getElementById('filter-perm-urbanas')?.addEventListener('change', () => {
    updateFilterCount();
    loadProjectsView();
});

// Toggle panel de filtros
document.getElementById('projects-filter-btn')?.addEventListener('click', () => {
    const panel = document.getElementById('projects-filter-panel');
    panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
});

// Cerrar panel al hacer clic fuera
document.addEventListener('click', (e) => {
    const wrapper = document.querySelector('.projects-filter-wrapper');
    const panel = document.getElementById('projects-filter-panel');
    if (wrapper && panel && !wrapper.contains(e.target)) {
        panel.style.display = 'none';
    }
});

// Limpiar todos los filtros
document.getElementById('clear-all-filters')?.addEventListener('click', () => {
    document.getElementById('filter-typology').value = '';
    document.getElementById('filter-modality').value = '';
    document.getElementById('show-inactive-projects').checked = false;
    document.getElementById('filter-perm-suelo').checked = false;
    document.getElementById('filter-perm-topografico').checked = false;
    document.getElementById('filter-perm-urbanas').checked = false;
    updateFilterCount();
    loadProjectsView();
});

function updateFilterCount() {
    const count = (document.getElementById('filter-typology')?.value ? 1 : 0)
        + (document.getElementById('filter-modality')?.value ? 1 : 0)
        + (document.getElementById('show-inactive-projects')?.checked ? 1 : 0)
        + (document.getElementById('filter-perm-suelo')?.checked ? 1 : 0)
        + (document.getElementById('filter-perm-topografico')?.checked ? 1 : 0)
        + (document.getElementById('filter-perm-urbanas')?.checked ? 1 : 0);
    const badge = document.getElementById('filter-active-count');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline-flex' : 'none';
    }
}

// Toggle para mostrar proyectos inactivos en vista de equipo
document.getElementById('show-inactive-team-projects')?.addEventListener('change', () => {
    loadTeam();
});

// Función para poblar selectores de coordinador y líder
function populateRoleSelectors(coordinatorId = '', leaderId = '', supervisorId = '') {
    const coordinatorSelect = document.getElementById('project-coordinator');
    const leaderSelect = document.getElementById('project-leader');
    const supervisorSelect = document.getElementById('project-supervisor');
    
    const optionsHtml = '<option value="">Sin asignar</option>' +
        users.map(u => `<option value="${u.id}">${u.name}</option>`).join('');
    
    if (coordinatorSelect) {
        coordinatorSelect.innerHTML = optionsHtml;
        if (coordinatorId) coordinatorSelect.value = coordinatorId;
    }
    if (leaderSelect) {
        leaderSelect.innerHTML = optionsHtml;
        if (leaderId) leaderSelect.value = leaderId;
    }
    if (supervisorSelect) {
        supervisorSelect.innerHTML = optionsHtml;
        if (supervisorId) supervisorSelect.value = supervisorId;
    }
}

// Función para mostrar preview de imagen
function showImagePreview(imageUrl) {
    const preview = document.getElementById('project-image-preview');
    const removeBtn = document.getElementById('project-image-remove');
    
    if (imageUrl) {
        preview.innerHTML = `<img src="${imageUrl}" alt="Preview">`;
        preview.classList.add('has-image');
        removeBtn.style.display = 'inline-flex';
    } else {
        preview.innerHTML = `<i class="fas fa-building"></i><span>Sin imagen</span>`;
        preview.classList.remove('has-image');
        removeBtn.style.display = 'none';
    }
}

// Manejar cambio de imagen
document.getElementById('project-image-input')?.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    const projectId = document.getElementById('project-id').value;
    
    // Si es un proyecto existente, subir directamente
    if (projectId) {
        const formData = new FormData();
        formData.append('file', file);
        
        try {
            const response = await fetch(`/api/projects/${projectId}/upload-image`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${getToken()}`
                },
                body: formData
            });
            
            if (response.ok) {
                const data = await response.json();
                showImagePreview(data.image_url);
                // Actualizar proyecto en memoria
                const project = projects.find(p => p.id == projectId);
                if (project) project.image_url = data.image_url;
                showToast('Imagen subida exitosamente', 'success');
            } else {
                const error = await response.json();
                showToast(error.detail || 'Error al subir imagen', 'error');
            }
        } catch (error) {
            showToast('Error al subir imagen', 'error');
        }
    } else {
        // Si es proyecto nuevo, mostrar preview local
        const reader = new FileReader();
        reader.onload = (e) => {
            showImagePreview(e.target.result);
        };
        reader.readAsDataURL(file);
    }
});

// Manejar eliminar imagen
document.getElementById('project-image-remove')?.addEventListener('click', async () => {
    const projectId = document.getElementById('project-id').value;
    
    if (projectId) {
        try {
            const response = await fetch(`/api/projects/${projectId}/image`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${getToken()}`
                }
            });
            
            if (response.ok) {
                showImagePreview(null);
                const project = projects.find(p => p.id == projectId);
                if (project) project.image_url = null;
                showToast('Imagen eliminada', 'success');
            }
        } catch (error) {
            showToast('Error al eliminar imagen', 'error');
        }
    } else {
        showImagePreview(null);
        document.getElementById('project-image-input').value = '';
    }
});

document.getElementById('add-project-btn').addEventListener('click', async () => {
    document.getElementById('project-id').value = '';
    document.getElementById('project-form').reset();
    document.getElementById('project-modal-title').textContent = 'Nuevo Proyecto';
    document.getElementById('project-color').value = '#6366f1';
    document.getElementById('project-active').checked = true;
    document.getElementById('project-active').disabled = !(currentUser && currentUser.is_admin);
    document.querySelectorAll('.color-option').forEach(c => c.classList.remove('selected'));
    document.querySelector('.color-option[data-color="#6366f1"]').classList.add('selected');
    
    // Seleccionar al usuario actual por defecto
    renderMembersSelector([currentUser.id]);
    
    // Poblar selectores de coordinador y líder
    populateRoleSelectors();
    
    // Limpiar metros cuadrados y tipología
    document.getElementById('project-square-meters').value = '';
    document.getElementById('project-typology').value = '';
    document.getElementById('project-work-modality').value = '';
    document.getElementById('perm-estudio-suelo').checked = false;
    document.getElementById('perm-levantamiento-topografico').checked = false;
    document.getElementById('perm-variables-urbanas').checked = false;

    // Limpiar imagen
    showImagePreview(null);
    document.getElementById('project-image-input').value = '';
    
    // Inicializar etapas vacías
    renderStagesEditor([]);
    
    // Cargar plantillas en el selector
    await loadStageTemplatesSelector();
    
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
    document.getElementById('project-square-meters').value = project.square_meters || '';
    document.getElementById('project-typology').value = project.typology || '';
    document.getElementById('project-work-modality').value = project.work_modality || '';
    document.getElementById('perm-estudio-suelo').checked = project.perm_estudio_suelo || false;
    document.getElementById('perm-levantamiento-topografico').checked = project.perm_levantamiento_topografico || false;
    document.getElementById('perm-variables-urbanas').checked = project.perm_variables_urbanas || false;
    document.getElementById('project-color').value = project.color;
    document.getElementById('project-active').checked = project.is_active !== false;
    document.getElementById('project-active').disabled = !(currentUser && currentUser.is_admin);
    document.getElementById('project-modal-title').textContent = 'Editar Proyecto';
    
    document.querySelectorAll('.color-option').forEach(c => c.classList.remove('selected'));
    const colorBtn = document.querySelector(`.color-option[data-color="${project.color}"]`);
    if (colorBtn) colorBtn.classList.add('selected');
    
    // Mostrar imagen existente
    showImagePreview(project.image_url);
    document.getElementById('project-image-input').value = '';
    
    // Poblar selectores de coordinador y líder
    populateRoleSelectors(project.coordinator_id || '', project.leader_id || '', project.supervisor_id || '');
    
    // Cargar miembros actuales
    const memberIds = project.members ? project.members.map(m => m.id) : [];
    renderMembersSelector(memberIds);
    
    // Cargar etapas existentes
    const existingStages = await loadProjectStages(projectId);
    renderStagesEditor(existingStages);
    
    // Cargar plantillas en el selector
    await loadStageTemplatesSelector();
    
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
    const squareMeters = document.getElementById('project-square-meters').value;
    const coordinatorId = document.getElementById('project-coordinator').value;
    const leaderId = document.getElementById('project-leader').value;
    const supervisorId = document.getElementById('project-supervisor').value;
    const typology = document.getElementById('project-typology').value;
    const workModality = document.getElementById('project-work-modality').value;
    const permEstudioSuelo = document.getElementById('perm-estudio-suelo').checked;
    const permLevantamientoTopografico = document.getElementById('perm-levantamiento-topografico').checked;
    const permVariablesUrbanas = document.getElementById('perm-variables-urbanas').checked;
    
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
        is_active: document.getElementById('project-active').checked,
        square_meters: squareMeters ? parseFloat(squareMeters) : null,
        coordinator_id: coordinatorId ? parseInt(coordinatorId) : null,
        leader_id: leaderId ? parseInt(leaderId) : null,
        supervisor_id: supervisorId ? parseInt(supervisorId) : null,
        typology: typology || null,
        work_modality: workModality || null,
        perm_estudio_suelo: permEstudioSuelo,
        perm_levantamiento_topografico: permLevantamientoTopografico,
        perm_variables_urbanas: permVariablesUrbanas,
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
            
            // Subir imagen si se seleccionó una para proyecto nuevo
            const imageInput = document.getElementById('project-image-input');
            if (imageInput && imageInput.files.length > 0) {
                const formData = new FormData();
                formData.append('file', imageInput.files[0]);
                
                try {
                    await fetch(`/api/projects/${savedProjectId}/upload-image`, {
                        method: 'POST',
                        headers: {
                            'Authorization': `Bearer ${getToken()}`
                        },
                        body: formData
                    });
                } catch (e) {
                    console.error('Error subiendo imagen:', e);
                }
            }
            
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
        milestones = [];
        renderKanban();
        renderGantt();
        return;
    }

    try {
        const [tasksData, milestonesData] = await Promise.all([
            apiRequest(`/api/projects/${currentProject.id}/tasks`),
            apiRequest(`/api/projects/${currentProject.id}/milestones`).catch(e => {
                console.warn('Error cargando hitos:', e);
                return [];
            })
        ]);
        tasks = tasksData;
        milestones = milestonesData || [];
        console.log('Tareas cargadas:', tasks.length, '- Hitos cargados:', milestones.length);
        renderKanban();
        renderGantt();
    } catch (error) {
        console.error('Error cargando tareas:', error);
        showToast('Error cargando tareas', 'error');
    }
}

function renderKanban() {
    const statuses = ['todo', 'in_progress', 'review', 'restart', 'done'];
    const isAdmin = currentUser && currentUser.is_admin;
    
    statuses.forEach(status => {
        const column = document.getElementById(`column-${status}`);
        const statusTasks = tasks.filter(t => t.status === status);
        
        document.getElementById(`count-${status}`).textContent = statusTasks.length;
        
        column.innerHTML = statusTasks.map(task => {
            // Obtener los usuarios asignados (ahora es un array de IDs)
            const assigneeIds = task.assignee_ids || [];
            const assignees = assigneeIds.map(id => users.find(u => u.id === id)).filter(u => u);
            const overdue = task.status !== 'done' && task.status !== 'restart' && isOverdue(task.due_date);
            const isMyTask = assigneeIds.includes(currentUser?.id);
            const isProjectLeader = currentProject && currentProject.leader_id === currentUser?.id;
            const canUpdateProgress = (isMyTask || isAdmin || isProjectLeader) && !(task.status === 'restart' && !isAdmin);
            const isRestart = task.status === 'restart';
            
            const canDrag = isAdmin || ((isMyTask || isProjectLeader) && !isRestart && task.status !== 'done');
            
            return `
                <div class="task-card ${isRestart ? 'restart' : ''}" data-id="${task.id}" draggable="${canDrag}">
                    <div class="task-card-header">
                        <span class="task-priority ${task.priority}">${task.priority}</span>
                        ${isRestart ? `<span class="task-status-badge restart">Reinicio</span>` : ''}
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
                            <div class="task-assignees">
                                ${assignees.slice(0, 3).map(assignee => `
                                    <div class="task-assignee" style="background: ${assignee.avatar_color}" title="${assignee.name}">
                                        ${getInitials(assignee.name)}
                                    </div>
                                `).join('')}
                                ${assignees.length > 3 ? `<div class="task-assignee-more">+${assignees.length - 3}</div>` : ''}
                            </div>
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        
        // Add drag and drop listeners
        column.querySelectorAll('.task-card').forEach(card => {
            const taskId = parseInt(card.dataset.id);
            const task = tasks.find(t => t.id === taskId);
            const taskAssigneeIds = task ? (task.assignee_ids || []) : [];
            const isMyCard = taskAssigneeIds.includes(currentUser?.id);
            const isLeaderCard = currentProject && currentProject.leader_id === currentUser?.id;
            const isRestartCard = task && task.status === 'restart';
            const canDragCard = isAdmin || ((isMyCard || isLeaderCard) && !isRestartCard);
            
            if (canDragCard) {
                card.addEventListener('dragstart', handleDragStart);
                card.addEventListener('dragend', handleDragEnd);
            }
            card.addEventListener('click', (e) => {
                // Evitar abrir modal si se hizo clic en el botón de progreso
                if (e.target.closest('.btn-progress')) return;
                
                const taskId = parseInt(card.dataset.id);
                const task = tasks.find(t => t.id === taskId);
                if (!task) {
                    console.error('Tarea no encontrada en array local:', taskId);
                    return;
                }
                const taskAssigneeIds = task.assignee_ids || [];
                
                console.log('Click en tarea:', taskId, 'isAdmin:', isAdmin, 'assigneeIds:', taskAssigneeIds, 'currentUserId:', currentUser?.id, 'isLeader:', currentProject?.leader_id === currentUser?.id);
                
                if (isAdmin) {
                    openTaskModal(taskId);
                } else if (taskAssigneeIds.includes(currentUser?.id) || (currentProject && currentProject.leader_id === currentUser?.id)) {
                    if (task.status === 'restart') {
                        showToast('Tarea en reinicio: solo administradores pueden modificarla', 'info');
                        return;
                    }
                    openProgressModal(task);
                } else {
                    console.log('Usuario no tiene permiso para esta tarea. Asignados:', taskAssigneeIds, 'User:', currentUser?.id);
                    showToast('No estás asignado a esta tarea', 'info');
                }
            });
        });
    });
    
    // Column drop listeners (para admin y usuarios con tareas asignadas)
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
    const isAdmin = currentUser && currentUser.is_admin;
    
    // Solo admin puede mover a 'done' o 'restart'
    if (!isAdmin && (newStatus === 'done' || newStatus === 'restart')) {
        showToast('Solo los administradores pueden marcar tareas como completadas o en reinicio', 'warning');
        return;
    }
    
    // Solo admin puede mover tareas que ya están en 'done'
    const task = tasks.find(t => t.id === taskId);
    if (!isAdmin && task && task.status === 'done') {
        showToast('Solo los administradores pueden modificar tareas completadas', 'warning');
        return;
    }
    
    // Verificar que el usuario puede mover esta tarea
    if (!isAdmin && task) {
        const taskAssigneeIds = task.assignee_ids || [];
        const isMyTask = taskAssigneeIds.includes(currentUser?.id);
        const isProjectLeader = currentProject && currentProject.leader_id === currentUser?.id;
        if (!isMyTask && !isProjectLeader) {
            showToast('Solo puedes mover tareas asignadas a ti', 'warning');
            return;
        }
    }
    
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
async function populateTaskSupGruposChips(selectedComprasIds = [], selectedServiciosIds = []) {
    const projectId = currentProject?.id;
    if (!projectId) return;

    const comprasContainer = document.getElementById('task-sup-compras-chips');
    const serviciosContainer = document.getElementById('task-sup-servicios-chips');
    if (!comprasContainer || !serviciosContainer) return;

    // Mostrar loading mientras se cargan
    comprasContainer.innerHTML = '<span style="color:var(--text-muted);font-size:11px">Cargando...</span>';
    serviciosContainer.innerHTML = '<span style="color:var(--text-muted);font-size:11px">Cargando...</span>';

    let comprasGrupos = [];
    let serviciosGrupos = [];

    try {
        const [c, s] = await Promise.all([
            apiRequest(`/api/supervision/${projectId}/compras`),
            apiRequest(`/api/supervision/${projectId}/servicios`),
        ]);
        comprasGrupos = c || [];
        serviciosGrupos = s || [];
    } catch (err) {
        console.warn('No se pudieron cargar grupos de supervisión:', err);
    }

    if (comprasGrupos.length) {
        comprasContainer.innerHTML = comprasGrupos.map(g => `
            <div class="assignee-chip ${selectedComprasIds.includes(g.id) ? 'selected' : ''}" data-grupo-id="${g.id}" style="cursor:pointer" onclick="this.classList.toggle('selected')">
                <i class="fas fa-box" style="font-size:9px;opacity:.7"></i>
                <span class="assignee-chip-name">${escapeHtml(g.nombre)}</span>
            </div>`).join('');
    } else {
        comprasContainer.innerHTML = '<span style="color:var(--text-muted);font-size:11px">Sin grupos de compras</span>';
    }

    if (serviciosGrupos.length) {
        serviciosContainer.innerHTML = serviciosGrupos.map(g => `
            <div class="assignee-chip ${selectedServiciosIds.includes(g.id) ? 'selected' : ''}" data-grupo-id="${g.id}" style="cursor:pointer" onclick="this.classList.toggle('selected')">
                <i class="fas fa-handshake" style="font-size:9px;opacity:.7"></i>
                <span class="assignee-chip-name">${escapeHtml(g.nombre)}</span>
            </div>`).join('');
    } else {
        serviciosContainer.innerHTML = '<span style="color:var(--text-muted);font-size:11px">Sin grupos de servicios</span>';
    }
}

document.getElementById('add-task-btn').addEventListener('click', async () => {
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
    document.getElementById('task-assignee').value = ''; // Resetear asignado
    document.getElementById('assignee-chips-container').classList.remove('disabled'); // Habilitar chips para nueva tarea
    
    // Mostrar botón guardar para admin y líderes
    const saveBtn = document.getElementById('save-task-btn');
    if (saveBtn) {
        const isAdmin = currentUser && currentUser.is_admin;
        const isLeader = currentProject && currentUser && currentProject.leader_id === currentUser.id;
        saveBtn.style.display = (isAdmin || isLeader) ? 'block' : 'none';
    }
    
    // Habilitar todos los campos para nueva tarea (admin y líder)
    document.getElementById('task-title').disabled = false;
    document.getElementById('task-priority').disabled = false;
    document.getElementById('task-start').disabled = false;
    document.getElementById('task-due').disabled = false;
    document.getElementById('task-status').disabled = false;
    document.getElementById('task-description').disabled = false;
    document.getElementById('task-progress').disabled = false;
    document.getElementById('task-stage').disabled = false;
    
    updateAssigneeSelect();
    updateStageSelect();
    await populateTaskSupGruposChips([], []);
    openModal('task-modal');
});

function updateAssigneeSelect() {
    const container = document.getElementById('assignee-chips-container');
    const hiddenInput = document.getElementById('task-assignee');
    // Ahora es una lista de IDs separados por coma
    const currentValues = hiddenInput.value ? hiddenInput.value.split(',').map(v => parseInt(v)) : [];
    
    // Crear chips para cada usuario (sin opción "Sin asignar" ya que es multi-select)
    let chipsHtml = users.map(u => `
        <div class="assignee-chip ${currentValues.includes(u.id) ? 'selected' : ''}" data-user-id="${u.id}">
            <div class="assignee-chip-avatar" style="background: ${u.avatar_color}">
                ${getInitials(u.name)}
            </div>
            <span class="assignee-chip-name">${u.name}</span>
        </div>
    `).join('');
    
    container.innerHTML = chipsHtml;
    
    // Agregar event listeners a los chips (toggle selection)
    container.querySelectorAll('.assignee-chip').forEach(chip => {
        chip.addEventListener('click', () => {
            // Si el contenedor está deshabilitado, no hacer nada
            if (container.classList.contains('disabled')) return;
            
            // Toggle selección
            chip.classList.toggle('selected');
            
            // Actualizar el valor hidden con todos los seleccionados
            const selectedIds = [];
            container.querySelectorAll('.assignee-chip.selected').forEach(c => {
                if (c.dataset.userId) {
                    selectedIds.push(c.dataset.userId);
                }
            });
            hiddenInput.value = selectedIds.join(',');
        });
    });
}

async function openTaskModal(taskId) {
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
    
    // Establecer el valor del asignado ANTES de actualizar el select visual
    // Ahora es array de IDs
    const assigneeIds = task.assignee_ids || [];
    document.getElementById('task-assignee').value = assigneeIds.join(',');
    updateAssigneeSelect();
    
    updateStageSelect();
    document.getElementById('task-stage').value = task.stage_id || '';
    
    document.getElementById('task-modal-title').textContent = 'Editar Tarea';
    
    // Configurar visibilidad según rol
    const isAdmin = currentUser && currentUser.is_admin;
    const isMyTask = assigneeIds.includes(currentUser?.id);
    const isRestart = task.status === 'restart';
    
    // Mostrar botón de historial (siempre visible para tareas existentes)
    document.getElementById('view-history-btn').style.display = 'inline-flex';
    
    // Mostrar/ocultar botón eliminar (solo admin)
    document.getElementById('delete-task-btn').style.display = isAdmin ? 'inline-flex' : 'none';
    
    // Campos que solo admin puede editar
    document.getElementById('task-title').disabled = !isAdmin;
    document.getElementById('task-priority').disabled = !isAdmin;
    document.getElementById('task-start').disabled = !isAdmin;
    document.getElementById('task-due').disabled = !isAdmin;
    // Para los chips de asignado, usamos clase disabled en el contenedor
    const assigneeContainer = document.getElementById('assignee-chips-container');
    if (isAdmin) {
        assigneeContainer.classList.remove('disabled');
    } else {
        assigneeContainer.classList.add('disabled');
    }
    
    // Campos que usuarios normales pueden editar (si es su tarea)
    const canEdit = isAdmin || (isMyTask && !isRestart);
    document.getElementById('task-status').disabled = !canEdit;
    document.getElementById('task-description').disabled = !canEdit;
    document.getElementById('task-progress').disabled = !canEdit;
    document.getElementById('task-stage').disabled = !canEdit;
    
    // Mostrar botón guardar para admin, líder del proyecto, o usuario asignado
    const isLeader = currentProject && currentUser && currentProject.leader_id === currentUser.id;
    const submitBtn = document.getElementById('save-task-btn');
    if (submitBtn) {
        submitBtn.style.display = (isAdmin || isLeader || canEdit) ? 'block' : 'none';
    }

    // Cargar chips de supervisión con los grupos ya vinculados
    await populateTaskSupGruposChips(
        task.sup_compras_grupo_ids || [],
        task.sup_servicios_grupo_ids || []
    );
    
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
    const isLeader = currentProject && currentUser && currentProject.leader_id === currentUser.id;
    
    if (isAdmin || (isLeader && !taskId)) {
        // Admin puede enviar todos los campos, y líder al crear tarea nueva
        const assigneeValue = document.getElementById('task-assignee').value;
        const stageValue = document.getElementById('task-stage').value;
        const startDateValue = document.getElementById('task-start').value;
        const dueDateValue = document.getElementById('task-due').value;
        
        // Convertir string de IDs separados por coma a array de integers
        const assigneeIds = assigneeValue ? assigneeValue.split(',').map(v => parseInt(v)).filter(v => !isNaN(v)) : [];
        
        taskData = {
            title: document.getElementById('task-title').value,
            description: document.getElementById('task-description').value || null,
            status: document.getElementById('task-status').value,
            priority: document.getElementById('task-priority').value,
            assignee_ids: assigneeIds,
            stage_id: stageValue ? parseInt(stageValue) : null,
            start_date: startDateValue ? new Date(startDateValue).toISOString() : null,
            due_date: dueDateValue ? new Date(dueDateValue).toISOString() : null,
            progress: parseInt(document.getElementById('task-progress').value) || 0,
            sup_compras_grupo_ids: _getSelectedExtraGrupoIds('task-sup-compras-chips'),
            sup_servicios_grupo_ids: _getSelectedExtraGrupoIds('task-sup-servicios-chips'),
        };
    } else {
        // Usuario normal solo puede enviar: estado, descripción, progreso, etapa
        const stageValue = document.getElementById('task-stage').value;
        
        taskData = {
            status: document.getElementById('task-status').value,
            description: document.getElementById('task-description').value || null,
            progress: parseInt(document.getElementById('task-progress').value) || 0,
            stage_id: stageValue ? parseInt(stageValue) : null,
            sup_compras_grupo_ids: _getSelectedExtraGrupoIds('task-sup-compras-chips'),
            sup_servicios_grupo_ids: _getSelectedExtraGrupoIds('task-sup-servicios-chips'),
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
            // Admin o líder del proyecto pueden crear tareas
            if (!isAdmin && !isLeader) {
                showToast('Solo administradores o líderes pueden crear tareas', 'error');
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
    
    // Cerrar task-modal antes de abrir historial
    closeModal('task-modal');
    
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

// Botón "Volver a Tarea" del historial de cambios
document.getElementById('history-back-btn')?.addEventListener('click', () => {
    closeModal('history-modal');
    if (currentTaskForHistory) {
        openTaskModal(currentTaskForHistory.id);
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
    document.getElementById('stat-projects-total').textContent = stats.total_projects;
    document.getElementById('stat-projects-active').textContent = stats.active_projects;
    document.getElementById('stat-projects-inactive').textContent = stats.inactive_projects;

    document.getElementById('stat-tasks-total').textContent = stats.total_tasks;
    document.getElementById('stat-tasks-todo').textContent = stats.todo_tasks;
    document.getElementById('stat-tasks-progress').textContent = stats.in_progress_tasks;
    document.getElementById('stat-tasks-review').textContent = stats.review_tasks;
    document.getElementById('stat-tasks-done').textContent = stats.completed_tasks;
    document.getElementById('stat-tasks-restart').textContent = stats.restart_tasks;
    document.getElementById('stat-tasks-overdue').textContent = stats.overdue_tasks;
    
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
                    <div class="stages-title-left">
                        <i class="fas fa-layer-group"></i> Efectividad por Etapa
                    </div>
                    <button class="btn-icon stages-toggle" id="stages-toggle" title="Contraer/Expandir" onclick="toggleGanttStages(event)">
                        <i class="fas fa-chevron-up"></i>
                    </button>
                </div>
                <div class="stages-effectiveness-grid">
                    ${data.stages.map(stage => {
                        const stageEffectiveness = stage.scheduled_progress > 0 
                            ? Math.round((stage.actual_progress / stage.scheduled_progress) * 100) 
                            : 0;
                        
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
    
    const timeline = document.getElementById('gantt-timeline');
    const taskRows = document.getElementById('gantt-tasks');
    const ganttContainer = document.querySelector('.gantt-container');
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    // USAR EL MES SELECCIONADO (ganttCurrentDate) como base
    // Mostrar solo el mes seleccionado + 7 días del mes siguiente para contexto
    const selectedYear = ganttCurrentDate.getFullYear();
    const selectedMonth = ganttCurrentDate.getMonth();
    
    // Primer día del mes seleccionado
    const minDate = new Date(selectedYear, selectedMonth, 1);
    // Último día del mes + 7 días extra
    const lastDayOfMonth = new Date(selectedYear, selectedMonth + 1, 0);
    const maxDate = new Date(selectedYear, selectedMonth + 1, 7);
    
    // Actualizar el display del mes
    updateGanttDateDisplay();
    
    // Obtener tareas con fechas
    let tasksWithDates = [];
    if (currentProject && tasks.length > 0) {
        tasksWithDates = tasks.filter(t => t.start_date || t.due_date);
    }
    
    // Calcular días totales primero para determinar el scale
    const totalDaysTemp = Math.ceil((maxDate - minDate) / (1000 * 60 * 60 * 24)) + 1;
    
    // CALCULAR ESCALA AUTOMÁTICAMENTE basado en el ancho disponible
    const taskInfoWidth = 180; // Ancho de la columna de info
    const containerWidth = ganttContainer ? ganttContainer.clientWidth - 50 : 800; // -50 para padding
    const availableWidth = containerWidth - taskInfoWidth;
    ganttScale = Math.max(18, Math.floor(availableWidth / totalDaysTemp)); // Mínimo 18px por día
    
    // Render timeline - mostrar solo el mes seleccionado
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
                <span class="gantt-day-date">${d.getDate()}</span>
                <span class="gantt-day-name">${dayNames[d.getDay()]}</span>
            </div>
        `);
        dayIndex++;
    }
    timeline.innerHTML = days.join('');
    
    const totalDays = dayIndex;
    // Calcular el ancho total del timeline
    const timelineWidth = totalDays * ganttScale;
    
    // Mostrar mensaje si no hay proyecto o tareas
    if (!currentProject) {
        taskRows.innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text-muted);"><i class="fas fa-hand-pointer" style="font-size: 2rem; margin-bottom: 10px; display: block;"></i>Selecciona un proyecto para ver las tareas</div>';
        return;
    }

    const hasMilestones = milestones && milestones.length > 0;

    if (tasks.length === 0 && !hasMilestones) {
        taskRows.innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text-muted);"><i class="fas fa-tasks" style="font-size: 2rem; margin-bottom: 10px; display: block;"></i>Este proyecto no tiene tareas</div>';
        return;
    }

    if (tasksWithDates.length === 0 && !hasMilestones) {
        taskRows.innerHTML = '<div style="padding: 40px; text-align: center; color: var(--text-muted);"><i class="fas fa-calendar-plus" style="font-size: 2rem; margin-bottom: 10px; display: block;"></i>Las tareas necesitan fechas para mostrar el Gantt</div>';
        return;
    }
    
    // Filtrar tareas que están visibles en este rango de fechas
    const visibleTasks = tasksWithDates.filter(t => {
        const taskStart = t.start_date ? new Date(t.start_date) : new Date(t.due_date);
        const taskEnd = t.due_date ? new Date(t.due_date) : new Date(t.start_date);
        // La tarea es visible si se superpone con el rango del mes
        return taskEnd >= minDate && taskStart <= maxDate;
    });
    
    const hasVisibleMilestones = hasMilestones && milestones.some(m => {
        const mDate = new Date(m.date);
        return mDate >= minDate && mDate <= maxDate;
    });

    if (visibleTasks.length === 0 && !hasVisibleMilestones) {
        taskRows.innerHTML = `<div style="padding: 40px; text-align: center; color: var(--text-muted);"><i class="fas fa-calendar-alt" style="font-size: 2rem; margin-bottom: 10px; display: block;"></i>No hay tareas en ${monthNames[selectedMonth]} ${selectedYear}</div>`;
        return;
    }
    
    // ORDENAR tareas por fecha de inicio
    visibleTasks.sort((a, b) => {
        const dateA = a.start_date ? new Date(a.start_date) : new Date(a.due_date);
        const dateB = b.start_date ? new Date(b.start_date) : new Date(b.due_date);
        return dateA - dateB;
    });
    
    // AGRUPAR tareas por etapa
    const tasksByStage = {};
    const noStageKey = '__no_stage__';
    
    visibleTasks.forEach(task => {
        const stageId = task.stage_id || noStageKey;
        if (!tasksByStage[stageId]) {
            tasksByStage[stageId] = [];
        }
        tasksByStage[stageId].push(task);
    });
    
    // Ordenar las etapas por posición
    const sortedStageIds = Object.keys(tasksByStage).sort((a, b) => {
        if (a === noStageKey) return 1; // Sin etapa al final
        if (b === noStageKey) return -1;
        const stageA = stages.find(s => s.id == a);
        const stageB = stages.find(s => s.id == b);
        return (stageA?.position || 0) - (stageB?.position || 0);
    });
    
    // Render task bars
    const colors = {
        todo: '#64748b',
        in_progress: '#06b6d4',
        review: '#f59e0b',
        done: '#10b981',
        restart: '#8b5cf6'
    };
    
    console.log('Total días:', totalDays, 'Scale:', ganttScale, 'Timeline width:', timelineWidth, 'Tareas visibles:', visibleTasks.length);
    
    // Función helper para renderizar una tarea
    function renderTaskRow(task) {
        const start = task.start_date ? new Date(task.start_date) : new Date(task.due_date);
        const end = task.due_date ? new Date(task.due_date) : new Date(task.start_date);
        
        // Calcular posición y duración ORIGINALES
        const startDayOffset = Math.floor((start - minDate) / (1000 * 60 * 60 * 24));
        const endDayOffset = Math.floor((end - minDate) / (1000 * 60 * 60 * 24));
        
        // RECORTAR al rango visible (0 a totalDays)
        const clippedStartDay = Math.max(0, Math.min(totalDays - 1, startDayOffset));
        const clippedEndDay = Math.max(0, Math.min(totalDays - 1, endDayOffset));
        const clippedDurationDays = Math.max(1, clippedEndDay - clippedStartDay + 1);
        
        // Verificar si la tarea está completamente fuera del rango visible
        const isOutOfRange = endDayOffset < 0 || startDayOffset >= totalDays;
        
        const startOffset = clippedStartDay * ganttScale;
        const duration = clippedDurationDays * ganttScale;
        
        // CALCULAR AVANCE PROGRAMADO DE ESTA TAREA
        let scheduledProgress = 0;
        const startDate = new Date(start);
        const endDate = new Date(end);
        startDate.setHours(0, 0, 0, 0);
        endDate.setHours(23, 59, 59, 999);
        
        if (today >= endDate) {
            scheduledProgress = 100;
        } else if (today >= startDate) {
            const totalDaysTask = Math.floor((endDate - startDate) / (1000 * 60 * 60 * 24)) + 1;
            const elapsedDays = Math.floor((today - startDate) / (1000 * 60 * 60 * 24)) + 1;
            scheduledProgress = Math.min(100, Math.round((elapsedDays / totalDaysTask) * 100));
        }
        
        // CALCULAR EFECTIVIDAD DE LA TAREA
        let taskEffectiveness = 100;
        if (scheduledProgress > 0) {
            taskEffectiveness = Math.round((task.progress / scheduledProgress) * 100);
        } else if (task.progress > 0) {
            taskEffectiveness = 100;
        }
        
        // Determinar color de efectividad
        let effectivenessIcon = '🚀';
        if (taskEffectiveness < 100) {
            effectivenessIcon = '⚠️';
        } else if (taskEffectiveness === 100) {
            effectivenessIcon = '✅';
        }
        
        // Indicadores de recorte
        const isClippedStart = startDayOffset < 0;
        const isClippedEnd = endDayOffset >= totalDays;
        const clipStartIndicator = isClippedStart ? '◀' : '';
        const clipEndIndicator = isClippedEnd ? '▶' : '';
        
        // Bordes redondeados según recorte
        const borderRadiusLeft = isClippedStart ? '0' : '6px';
        const borderRadiusRight = isClippedEnd ? '0' : '6px';
        const borderRadius = `${borderRadiusLeft} ${borderRadiusRight} ${borderRadiusRight} ${borderRadiusLeft}`;
        
        // Get assignee names (ahora puede haber múltiples)
        const assigneeIds = task.assignee_ids || [];
        const assignees = assigneeIds.map(id => users.find(u => u.id === id)).filter(u => u);
        const assigneeName = assignees.length > 0 ? assignees.map(u => u.name).join(', ') : 'Sin asignar';
        
        // Formatear fechas para mostrar
        const startDateStr = task.start_date ? new Date(task.start_date).toLocaleDateString('es-ES', {day: '2-digit', month: 'short'}) : '';
        const endDateStr = task.due_date ? new Date(task.due_date).toLocaleDateString('es-ES', {day: '2-digit', month: 'short'}) : '';
        
        // Color según estado
        const barColor = colors[task.status] || '#64748b';
        
        // Si la tarea está completamente fuera del rango visible
        if (isOutOfRange) {
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
                    <div class="gantt-task-bar-container" style="width: ${timelineWidth}px;">
                        ${todayIndex >= 0 ? `<div class="gantt-today-line" style="left: ${(todayIndex * ganttScale) + (ganttScale / 2)}px;"></div>` : ''}
                        <div style="position: absolute; left: ${startDayOffset < 0 ? 0 : timelineWidth - 100}px; padding: 8px 12px; color: #94a3b8; font-size: 0.75rem; font-style: italic;">
                            ${startDayOffset < 0 ? '◀ Antes de este período' : 'Después de este período ▶'}
                        </div>
                    </div>
                </div>
            `;
        }
        
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
                <div class="gantt-task-bar-container" style="width: ${timelineWidth}px; max-width: ${timelineWidth}px; overflow: hidden;">
                    ${todayIndex >= 0 ? `<div class="gantt-today-line" style="left: ${(todayIndex * ganttScale) + (ganttScale / 2)}px;"></div>` : ''}
                    <div style="position: absolute; left: ${startOffset}px; width: ${duration}px; height: 36px; top: 2px; background: ${barColor}; border-radius: ${borderRadius}; display: flex; flex-direction: column; cursor: pointer; box-shadow: 0 2px 8px rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.2); overflow: hidden;" 
                         class="gantt-task-bar"
                         data-id="${task.id}" 
                         title="📅 Prog: ${scheduledProgress}% | ✅ Real: ${task.progress}% | ${effectivenessIcon} Efect: ${taskEffectiveness}%">
                        <div style="position: absolute; left: 0; top: 0; height: 100%; width: ${scheduledProgress}%; background: rgba(0,0,0,0.3);"></div>
                        <div style="position: absolute; left: 0; top: 0; height: 100%; width: ${task.progress}%; background: rgba(255,255,255,0.35);"></div>
                        <div style="display: flex; justify-content: space-between; align-items: center; padding: 2px 8px; position: relative; z-index: 1; height: 100%;">
                            <span style="color: rgba(255,255,255,0.9); font-size: 0.65rem; text-shadow: 0 1px 2px rgba(0,0,0,0.5);">${clipStartIndicator} 📅${scheduledProgress}%</span>
                            <span style="color: white; font-size: 0.8rem; font-weight: bold; text-shadow: 0 1px 2px rgba(0,0,0,0.5);">${task.progress}% ${clipEndIndicator}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Generar HTML agrupado por etapas
    let ganttHtml = '';

    // ===== RENDERIZAR GRUPO DE HITOS =====
    const MILESTONE_TYPE_ICONS = { meeting: '🤝', change: '🔄', blueprint: '📐', team: '👥', other: '📌' };
    const MILESTONE_TYPE_LABELS = { meeting: 'Reunión', change: 'Cambio', blueprint: 'Plano', team: 'Equipo', other: 'Otro' };

    console.log('Milestones para renderizar:', milestones, 'minDate:', minDate, 'maxDate:', maxDate);

    const visibleMilestones = (milestones || []).filter(m => {
        const mDate = new Date(m.date);
        mDate.setHours(0, 0, 0, 0);
        console.log('Milestone:', m.title, 'date:', m.date, 'parsed:', mDate, 'visible:', mDate >= minDate && mDate <= maxDate);
        return mDate >= minDate && mDate <= maxDate;
    });

    if (visibleMilestones.length > 0) {
        ganttHtml += `
            <div class="gantt-stage-group gantt-milestone-group" data-stage-id="__milestones__">
                <div class="gantt-stage-header gantt-milestone-header" onclick="toggleGanttStageGroup('__milestones__')">
                    <i class="fas fa-diamond"></i>
                    <span>Hitos</span>
                    <span class="stage-task-count">${visibleMilestones.length} hito${visibleMilestones.length !== 1 ? 's' : ''}</span>
                    <i class="fas fa-chevron-down stage-toggle"></i>
                </div>
                <div class="gantt-stage-tasks">
                    ${visibleMilestones.map(m => {
                        const mDate = new Date(m.date);
                        const dayOffset = Math.floor((mDate - minDate) / (1000 * 60 * 60 * 24));
                        const leftPos = dayOffset * ganttScale + (ganttScale / 2) - 10; // center diamond
                        const icon = MILESTONE_TYPE_ICONS[m.milestone_type] || '📌';
                        const typeLabel = MILESTONE_TYPE_LABELS[m.milestone_type] || 'Otro';
                        const dateStr = mDate.toLocaleDateString('es-ES', {day: '2-digit', month: 'short'});
                        return `
                            <div class="gantt-task-row gantt-milestone-row">
                                <div class="gantt-task-info">
                                    <span class="milestone-type-icon">${icon}</span>
                                    <div class="gantt-task-details">
                                        <span class="gantt-task-name">${m.title}</span>
                                        <span class="gantt-task-assignee">${typeLabel} · ${dateStr}</span>
                                    </div>
                                </div>
                                <div class="gantt-task-bar-container" style="width: ${timelineWidth}px; max-width: ${timelineWidth}px; overflow: hidden;">
                                    ${todayIndex >= 0 ? `<div class="gantt-today-line" style="left: ${(todayIndex * ganttScale) + (ganttScale / 2)}px;"></div>` : ''}
                                    <div class="gantt-milestone-diamond" style="left: ${leftPos}px;" data-milestone-id="${m.id}" title="${icon} ${m.title}\n${dateStr}"></div>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }

    sortedStageIds.forEach(stageId => {
        const stageTasks = tasksByStage[stageId];
        const stage = stageId === noStageKey ? null : stages.find(s => s.id == stageId);
        const stageName = stage ? stage.name : 'Sin Etapa';
        const stageIcon = stage ? 'fa-layer-group' : 'fa-inbox';
        const headerClass = stage ? '' : 'gantt-no-stage-header';
        
        ganttHtml += `
            <div class="gantt-stage-group" data-stage-id="${stageId}">
                <div class="gantt-stage-header ${headerClass}" onclick="toggleGanttStageGroup('${stageId}')">
                    <i class="fas ${stageIcon}"></i>
                    <span>${stageName}</span>
                    <span class="stage-task-count">${stageTasks.length} tarea${stageTasks.length !== 1 ? 's' : ''}</span>
                    <i class="fas fa-chevron-down stage-toggle"></i>
                </div>
                <div class="gantt-stage-tasks">
                    ${stageTasks.map(task => renderTaskRow(task)).join('')}
                </div>
            </div>
        `;
    });
    
    taskRows.innerHTML = ganttHtml;
    
    // Restaurar estados colapsados desde localStorage
    const collapsedStages = JSON.parse(localStorage.getItem('gantt-collapsed-stages') || '{}');
    Object.keys(collapsedStages).forEach(stageId => {
        if (collapsedStages[stageId]) {
            const group = document.querySelector(`.gantt-stage-group[data-stage-id="${stageId}"]`);
            if (group) group.classList.add('collapsed');
        }
    });
    
    // Add click listeners
    taskRows.querySelectorAll('.gantt-task-bar').forEach(bar => {
        bar.addEventListener('click', () => openTaskModal(parseInt(bar.dataset.id)));
    });

    // Add click listeners for milestone diamonds
    taskRows.querySelectorAll('.gantt-milestone-diamond').forEach(diamond => {
        diamond.addEventListener('click', () => openMilestoneModal(parseInt(diamond.dataset.milestoneId)));
    });
}

// ===================== MY TASKS =====================
async function loadMyTasks(force = false) {
    if (!currentUser) return;
    
    if (!force && myTasksLoadedAt && (Date.now() - myTasksLoadedAt) < MY_TASKS_CACHE_TTL_MS) {
        renderMyTasks(myTasksCache);
        return;
    }
    
    try {
        // Load all tasks from all projects in parallel (including stage info)
        const stagePromises = projects.map(project => loadProjectStages(project.id));
        const tasksPromises = projects.map(project => apiRequest(`/api/projects/${project.id}/tasks`));
        const stagesResults = await Promise.all(stagePromises);
        const tasksResults = await Promise.all(tasksPromises);
        
        let allTasks = [];
        projects.forEach((project, index) => {
            const projectStages = stagesResults[index] || [];
            const stageById = new Map(projectStages.map(s => [s.id, s]));
            const projectTasks = tasksResults[index] || [];
            allTasks = allTasks.concat(projectTasks.map(t => ({
                ...t,
                project,
                stage: t.stage_id ? (stageById.get(t.stage_id) || null) : null
            })));
        });
        
        // Filter by current user (ahora buscar si el usuario está en el array de assignee_ids)
        const myTasks = allTasks.filter(t => (t.assignee_ids || []).includes(currentUser.id));
        myTasksCache = myTasks;
        myTasksLoadedAt = Date.now();
        renderMyTasks(myTasksCache);
    } catch (error) {
        showToast('Error cargando tareas', 'error');
    }
}

function refreshMyTasksView() {
    if (myTasksCache.length > 0) {
        renderMyTasks(myTasksCache);
    } else {
        loadMyTasks();
    }
}

function renderMyTasks(taskList) {
    const list = document.getElementById('my-tasks-list');
    const prioritySelect = document.getElementById('my-tasks-priority-filter');
    const statusSelect = document.getElementById('my-tasks-status-filter');
    const activeTab = document.querySelector('.filter-tab.active');
    const priorityFilter = (prioritySelect?.value && prioritySelect.value !== 'all')
        ? prioritySelect.value
        : 'all';
    const statusFilter = (statusSelect?.value && statusSelect.value !== 'all')
        ? statusSelect.value
        : (activeTab?.dataset.filter || 'all');
    
    let filtered = taskList;
    if (priorityFilter !== 'all') {
        filtered = taskList.filter(t => t.priority === priorityFilter);
    }
    if (statusFilter !== 'all') {
        filtered = filtered.filter(t => t.status === statusFilter);
    }
    
    if (filtered.length === 0) {
        list.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-clipboard-check"></i>
                <p>No hay tareas para este filtro</p>
            </div>
        `;
        return;
    }
    
    // Agrupar por proyecto y etapa
    const projectGroups = new Map();
    filtered.forEach(task => {
        const projectId = task.project.id;
        if (!projectGroups.has(projectId)) {
            projectGroups.set(projectId, {
                project: task.project,
                stages: new Map()
            });
        }
        const stageKey = task.stage ? String(task.stage.id) : 'no-stage';
        const stageName = task.stage ? task.stage.name : 'Sin etapa';
        const group = projectGroups.get(projectId);
        if (!group.stages.has(stageKey)) {
            group.stages.set(stageKey, {
                name: stageName,
                tasks: []
            });
        }
        group.stages.get(stageKey).tasks.push(task);
    });
    
    const isAdmin = currentUser && currentUser.is_admin;
    
    const statusOptions = isAdmin ? [
        { value: 'todo', label: 'Por Hacer' },
        { value: 'in_progress', label: 'En Progreso' },
        { value: 'review', label: 'En Revisión' },
        { value: 'done', label: 'Completada' }
    ] : [
        { value: 'todo', label: 'Por Hacer' },
        { value: 'in_progress', label: 'En Progreso' },
        { value: 'review', label: 'En Revisión' }
    ];
    
    const projectsSorted = Array.from(projectGroups.values()).sort((a, b) =>
        a.project.name.localeCompare(b.project.name)
    );
    
    list.innerHTML = projectsSorted.map(projectGroup => {
        const stagesSorted = Array.from(projectGroup.stages.values()).sort((a, b) =>
            a.name.localeCompare(b.name)
        );
        
        return `
            <div class="my-tasks-project">
                <div class="my-tasks-project-header">
                    <span class="dot" style="background: ${projectGroup.project.color}"></span>
                    <span>${projectGroup.project.name}</span>
                </div>
                ${stagesSorted.map(stageGroup => `
                    <div class="my-tasks-stage">
                        <div class="my-tasks-stage-header">
                            <span class="stage-name">${stageGroup.name}</span>
                            <span class="stage-count">${stageGroup.tasks.length}</span>
                        </div>
                        ${stageGroup.tasks.map(task => {
                            const progressValue = task.progress || 0;
                            const isRestart = task.status === 'restart';
                            const isDone = task.status === 'done';
                            let statusOptionsForTask = isRestart
                                ? [...statusOptions, { value: 'restart', label: 'Reinicio' }]
                                : statusOptions;
                            // Si la tarea está en 'done' y no es admin, agregar opción done como solo lectura
                            if (isDone && !isAdmin && !statusOptionsForTask.find(o => o.value === 'done')) {
                                statusOptionsForTask = [...statusOptionsForTask, { value: 'done', label: 'Completada' }];
                            }
                            return `
                                <div class="task-list-item" data-id="${task.id}">
                                    <div class="task-list-left">
                                        <div class="task-checkbox ${task.status === 'done' ? 'checked' : ''} ${isRestart ? 'disabled' : ''}" data-task-id="${task.id}">
                                            <i class="fas fa-check"></i>
                                        </div>
                                        <div class="task-list-content">
                                            <div class="task-list-title ${task.status === 'done' ? 'completed' : ''}">${task.title}</div>
                                            <div class="task-list-meta">
                                                ${task.due_date ? `
                                                    <span class="${isOverdue(task.due_date) && task.status !== 'done' && !isRestart ? 'overdue' : ''}">
                                                        <i class="fas fa-calendar"></i> ${formatDate(task.due_date)}
                                                    </span>
                                                ` : ''}
                                                <span class="task-priority ${task.priority}">${task.priority}</span>
                                                ${isRestart ? '<span class="task-status-badge restart">Reinicio</span>' : ''}
                                            </div>
                                        </div>
                                    </div>
                                    <div class="task-list-actions ${isRestart ? 'disabled' : ''}">
                                        <div class="task-action-row">
                                            <label>Estado</label>
                                            <select class="task-status-select" data-task-id="${task.id}" ${isRestart ? 'disabled' : ''}>
                                                ${statusOptionsForTask.map(opt => `
                                                    <option value="${opt.value}" ${task.status === opt.value ? 'selected' : ''}>${opt.label}</option>
                                                `).join('')}
                                            </select>
                                        </div>
                                        <div class="task-action-row">
                                            <label>Avance <span class="progress-value" data-task-id="${task.id}">${progressValue}%</span></label>
                                            <input type="range" class="task-progress-input" min="0" max="${isAdmin ? 100 : 99}" value="${progressValue}" data-task-id="${task.id}" ${isRestart ? 'disabled' : ''}>
                                        </div>
                                    </div>
                                </div>
                            `;
                        }).join('')}
                    </div>
                `).join('')}
            </div>
        `;
    }).join('');
    
    list.querySelectorAll('.task-checkbox').forEach(checkbox => {
        checkbox.addEventListener('click', async (e) => {
            e.stopPropagation();
            if (checkbox.classList.contains('disabled')) {
                showToast('Tarea en reinicio: solo administradores pueden modificarla', 'info');
                return;
            }
            const isAdmin = currentUser && currentUser.is_admin;
            const isChecked = checkbox.classList.contains('checked');
            // Solo admin puede marcar como completada o desmarcar completada
            if (!isAdmin) {
                if (isChecked) {
                    showToast('Solo los administradores pueden modificar tareas completadas', 'warning');
                } else {
                    showToast('Solo los administradores pueden marcar tareas como completadas', 'warning');
                }
                return;
            }
            const taskId = parseInt(checkbox.dataset.taskId);
            const newStatus = isChecked ? 'todo' : 'done';
            await updateMyTaskInline(taskId, { status: newStatus });
        });
    });
    
    list.querySelectorAll('.task-status-select').forEach(select => {
        select.addEventListener('change', async (e) => {
            const taskId = parseInt(e.target.dataset.taskId);
            const newStatus = e.target.value;
            const isAdmin = currentUser && currentUser.is_admin;
            if (!isAdmin && (newStatus === 'done' || newStatus === 'restart')) {
                showToast('Solo los administradores pueden marcar tareas como completadas o en reinicio', 'warning');
                await loadMyTasks(true);
                return;
            }
            // Si la tarea estaba en 'done', solo admin puede cambiarla
            const taskObj = myTasksCache.find(t => t.id === taskId);
            if (!isAdmin && taskObj && taskObj.status === 'done') {
                showToast('Solo los administradores pueden modificar tareas completadas', 'warning');
                await loadMyTasks(true);
                return;
            }
            await updateMyTaskInline(taskId, { status: newStatus });
        });
    });
    
    list.querySelectorAll('.task-progress-input').forEach(range => {
        range.addEventListener('input', (e) => {
            const taskId = e.target.dataset.taskId;
            const value = e.target.value;
            const label = list.querySelector(`.progress-value[data-task-id="${taskId}"]`);
            if (label) label.textContent = `${value}%`;
        });
        range.addEventListener('change', async (e) => {
            const taskId = parseInt(e.target.dataset.taskId);
            const value = parseInt(e.target.value) || 0;
            try {
                await apiRequest(`/api/tasks/${taskId}/progress`, {
                    method: 'POST',
                    body: JSON.stringify({ progress: value, comment: 'Actualizado desde Mis Tareas' })
                });
                showToast(`Avance actualizado a ${value}%`, 'success');
                await loadMyTasks(true);
                loadDashboard();
            } catch (error) {
                showToast(error.message || 'Error al actualizar avance', 'error');
                await loadMyTasks(true);
            }
        });
    });
}

async function updateMyTaskInline(taskId, payload) {
    try {
        await apiRequest(`/api/tasks/${taskId}`, {
            method: 'PUT',
            body: JSON.stringify(payload)
        });
        await loadMyTasks(true);
        loadDashboard();
    } catch (error) {
        showToast(error.message, 'error');
    }
}

document.querySelectorAll('.filter-tab').forEach(tab => {
    tab.addEventListener('click', () => {
        document.querySelectorAll('.filter-tab').forEach(t => t.classList.remove('active'));
        tab.classList.add('active');
        const statusSelect = document.getElementById('my-tasks-status-filter');
        if (statusSelect) {
            statusSelect.value = tab.dataset.filter;
        }
        refreshMyTasksView();
    });
});

document.getElementById('my-tasks-priority-filter')?.addEventListener('change', (e) => {
    refreshMyTasksView();
});

document.getElementById('my-tasks-status-filter')?.addEventListener('change', (e) => {
    const value = e.target.value;
    const tabs = document.querySelectorAll('.filter-tab');
    tabs.forEach(t => t.classList.remove('active'));
    const tabToActivate = document.querySelector(`.filter-tab[data-filter="${value}"]`);
    if (tabToActivate) {
        tabToActivate.classList.add('active');
    } else if (tabs[0]) {
        tabs[0].classList.add('active');
    }
    refreshMyTasksView();
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
    const showInactiveTeam = document.getElementById('show-inactive-team-projects')?.checked || false;
    
    // Una sola petición al backend con todo el resumen
    let teamData;
    try {
        teamData = await apiRequest(`/api/team-summary?include_inactive=${showInactiveTeam}`);
    } catch (e) {
        console.error('Error loading team summary:', e);
        grid.innerHTML = '<p style="color:var(--text-muted);text-align:center">Error al cargar equipo</p>';
        return;
    }
    
    grid.innerHTML = teamData.map(member => {
        const projectCount = (member.projects || []).length;
        const projectsHtml = projectCount
            ? member.projects.map(p => `
                <span class="team-project-chip" style="--chip-color: ${p.color}">
                    <span class="dot"></span>${p.name}
                </span>
            `).join('')
            : '<span class="team-project-empty">Sin proyectos</span>';
        
        return `
            <div class="team-card">
                <div class="team-avatar" style="background: ${member.avatar_color}">
                    ${getInitials(member.name)}
                </div>
                <div class="team-name">${member.name}</div>
                <div class="team-email">${member.email}</div>
                <div class="team-projects">
                    <div class="team-projects-title">Proyectos asignados</div>
                    <div class="team-projects-list">
                        ${projectsHtml}
                    </div>
                </div>
                <div class="team-stats">
                    <div class="team-stat">
                        <div class="team-stat-value">${projectCount}</div>
                        <div class="team-stat-label">Obras</div>
                    </div>
                    <div class="team-stat">
                        <div class="team-stat-value">${member.task_count}</div>
                        <div class="team-stat-label">Tareas</div>
                    </div>
                    <div class="team-stat">
                        <div class="team-stat-value">${member.completed_count}</div>
                        <div class="team-stat-label">Completadas</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// ===================== PROJECTS VIEW =====================
const TYPOLOGY_LABELS = {
    residencial: 'Residencial',
    comercial_corporativo: 'Comercial Corporativo',
    comercial_residencial: 'Comercial Residencial',
    deportivo: 'Deportivo',
    hospitalario: 'Hospitalario',
    otros: 'Otros'
};

function getTypologyLabel(typology) {
    return TYPOLOGY_LABELS[typology] || typology || 'Sin especificar';
}

const MODALITY_LABELS = {
    anteproyecto: 'Ante-proyecto',
    proyecto: 'Proyecto',
    probono: 'Favores/Probono',
    personal: 'Personal',
    solo_obra: 'Solo Obra',
    outsourcing: 'Outsourcing'
};

function getModalityLabel(modality) {
    return MODALITY_LABELS[modality] || modality || 'Sin especificar';
}

async function loadProjectsView() {
    const grid = document.getElementById('projects-grid');
    if (!grid) return;
    
    // Filtrar por activos/inactivos
    const showInactive = document.getElementById('show-inactive-projects')?.checked || false;
    const typologyFilter = document.getElementById('filter-typology')?.value || '';
    const modalityFilter = document.getElementById('filter-modality')?.value || '';
    let filteredProjects = projects.filter(p => showInactive ? !p.is_active : p.is_active !== false);

    // Filtrar por tipología
    if (typologyFilter) {
        filteredProjects = filteredProjects.filter(p => p.typology === typologyFilter);
    }

    // Filtrar por modalidad
    if (modalityFilter) {
        filteredProjects = filteredProjects.filter(p => p.work_modality === modalityFilter);
    }

    // Filtrar por permisología
    const filterPermSuelo = document.getElementById('filter-perm-suelo')?.checked || false;
    const filterPermTopografico = document.getElementById('filter-perm-topografico')?.checked || false;
    const filterPermUrbanas = document.getElementById('filter-perm-urbanas')?.checked || false;
    if (filterPermSuelo) {
        filteredProjects = filteredProjects.filter(p => p.perm_estudio_suelo);
    }
    if (filterPermTopografico) {
        filteredProjects = filteredProjects.filter(p => p.perm_levantamiento_topografico);
    }
    if (filterPermUrbanas) {
        filteredProjects = filteredProjects.filter(p => p.perm_variables_urbanas);
    }
    
    // Ordenar por código/nombre
    filteredProjects.sort((a, b) => a.name.localeCompare(b.name, 'es', { numeric: true }));
    
    // Obtener tareas de todos los proyectos en paralelo
    const taskResults = await Promise.all(
        filteredProjects.map(project =>
            apiRequest(`/api/projects/${project.id}/tasks`)
                .then(tasks => tasks.map(t => ({ ...t, project_id: project.id })))
                .catch(() => [])
        )
    );
    const allTasks = taskResults.flat();
    
    if (filteredProjects.length === 0) {
        grid.innerHTML = `
            <div class="empty-state" style="grid-column: 1 / -1;">
                <i class="fas fa-folder-open"></i>
                <p>${showInactive ? 'No hay proyectos inactivos' : 'No hay proyectos activos'}</p>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = filteredProjects.map(project => {
        const projectTasks = allTasks.filter(t => t.project_id === project.id);
        const completedTasks = projectTasks.filter(t => t.status === 'done').length;
        const totalTasks = projectTasks.length;
        const progressPercent = totalTasks > 0 ? Math.round((completedTasks / totalTasks) * 100) : 0;
        
        const startDate = project.start_date ? formatDate(project.start_date) : 'Sin definir';
        const endDate = project.end_date ? formatDate(project.end_date) : 'Sin definir';
        
        const membersHtml = project.members && project.members.length > 0
            ? project.members.slice(0, 5).map(m => `
                <div class="project-card-member" style="background: ${m.avatar_color}" title="${m.name}">
                    ${getInitials(m.name)}
                </div>
            `).join('') + (project.members.length > 5 ? `<div class="project-card-member more">+${project.members.length - 5}</div>` : '')
            : '<span class="no-members">Sin asignar</span>';
        
        const coordinatorHtml = project.coordinator
            ? `<div class="project-role-person">
                <div class="project-role-avatar" style="background: ${project.coordinator.avatar_color}">${getInitials(project.coordinator.name)}</div>
                <span>${project.coordinator.name}</span>
               </div>`
            : '<span class="no-assigned">Sin asignar</span>';
        
        const leaderHtml = project.leader
            ? `<div class="project-role-person">
                <div class="project-role-avatar" style="background: ${project.leader.avatar_color}">${getInitials(project.leader.name)}</div>
                <span>${project.leader.name}</span>
               </div>`
            : '<span class="no-assigned">Sin asignar</span>';
        
        const supervisorHtml = project.supervisor
            ? `<div class="project-role-person">
                <div class="project-role-avatar" style="background: ${project.supervisor.avatar_color}">${getInitials(project.supervisor.name)}</div>
                <span>${project.supervisor.name}</span>
               </div>`
            : '<span class="no-assigned">Sin asignar</span>';
        
        const imageHtml = project.image_url
            ? `<div class="project-card-image">
                <img src="${project.image_url}" alt="${project.name}">
               </div>`
            : '';
        
        return `
            <div class="project-card glass-card" data-project-id="${project.id}">
                ${imageHtml}
                <div class="project-card-header" style="border-left-color: ${project.color}">
                    <div class="project-card-title">
                        <h3>${project.name}</h3>
                        <div style="display: flex; align-items: center; gap: 6px;">
                            <span class="project-status-badge ${project.is_active ? 'active' : 'inactive'}">
                                ${project.is_active ? 'Activo' : 'Inactivo'}
                            </span>
                            ${currentUser && (currentUser.is_admin || (project.coordinator && project.coordinator.id === currentUser.id)) ? `
                                <button class="btn-delete-project-card" onclick="deleteProject(${project.id}, '${project.name.replace(/'/g, "\\'")}')" title="Eliminar proyecto">
                                    <i class="fas fa-trash"></i>
                                </button>
                            ` : ''}
                        </div>
                    </div>
                    ${project.description ? `<p class="project-card-desc">${project.description}</p>` : ''}
                </div>
                
                <div class="project-card-info">
                    <div class="project-info-item">
                        <i class="fas fa-ruler-combined"></i>
                        <span>${project.square_meters ? project.square_meters.toLocaleString() + ' m²' : 'No especificado'}</span>
                    </div>
                    <div class="project-info-item">
                        <i class="fas fa-calendar-alt"></i>
                        <span>${startDate} - ${endDate}</span>
                    </div>
                </div>
                <div class="project-card-typology">
                    <span class="typology-badge typology-${project.typology || 'none'}"><i class="fas fa-building"></i> ${getTypologyLabel(project.typology)}</span>
                    <span class="modality-badge modality-${project.work_modality || 'none'}"><i class="fas fa-briefcase"></i> ${getModalityLabel(project.work_modality)}</span>
                </div>

                <div class="project-card-permisologia">
                    <span class="perm-badge ${project.perm_estudio_suelo ? 'perm-active' : 'perm-inactive'}"><i class="fas ${project.perm_estudio_suelo ? 'fa-check-circle' : 'fa-times-circle'}"></i> Estudio de suelo</span>
                    <span class="perm-badge ${project.perm_levantamiento_topografico ? 'perm-active' : 'perm-inactive'}"><i class="fas ${project.perm_levantamiento_topografico ? 'fa-check-circle' : 'fa-times-circle'}"></i> Lev. topográfico</span>
                    <span class="perm-badge ${project.perm_variables_urbanas ? 'perm-active' : 'perm-inactive'}"><i class="fas ${project.perm_variables_urbanas ? 'fa-check-circle' : 'fa-times-circle'}"></i> Permisología</span>
                </div>

                <div class="project-card-roles">
                    <div class="project-role">
                        <div class="project-role-label"><i class="fas fa-user-tie"></i> Coordinador</div>
                        ${coordinatorHtml}
                    </div>
                    <div class="project-role">
                        <div class="project-role-label"><i class="fas fa-user-cog"></i> Líder</div>
                        ${leaderHtml}
                    </div>
                    <div class="project-role">
                        <div class="project-role-label"><i class="fas fa-hard-hat"></i> Supervisor</div>
                        ${supervisorHtml}
                    </div>
                </div>
                
                <div class="project-card-team">
                    <div class="project-team-label">Equipo asignado</div>
                    <div class="project-team-avatars">
                        ${membersHtml}
                    </div>
                </div>
                
                <div class="project-card-stats">
                    <div class="project-stat">
                        <div class="project-stat-value">${totalTasks}</div>
                        <div class="project-stat-label">Tareas</div>
                    </div>
                    <div class="project-stat">
                        <div class="project-stat-value">${completedTasks}</div>
                        <div class="project-stat-label">Completadas</div>
                    </div>
                    <div class="project-stat">
                        <div class="project-stat-value">${progressPercent}%</div>
                        <div class="project-stat-label">Progreso</div>
                    </div>
                </div>
                
                <div class="project-card-progress">
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${progressPercent}%; background: ${project.color}"></div>
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

let progressFormInitialized = false;

function setupProgressForm() {
    if (progressFormInitialized) return;
    progressFormInitialized = true;
    
    const progressSlider = document.getElementById('new-progress');
    const progressNumber = document.getElementById('new-progress-number');
    
    if (progressSlider && progressNumber) {
        // Sincronizar slider → número
        progressSlider.addEventListener('input', (e) => {
            progressNumber.value = e.target.value;
        });
        
        // Sincronizar número → slider
        progressNumber.addEventListener('input', (e) => {
            let val = parseInt(e.target.value) || 0;
            if (val < 0) val = 0;
            if (val > 100) val = 100;
            progressSlider.value = val;
            e.target.value = val;
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
    console.log('Abriendo modal de progreso para tarea:', task.id, task.title);
    currentProgressTaskId = task.id;
    document.getElementById('progress-task-id').value = task.id;
    document.getElementById('progress-task-title').textContent = task.title;
    document.getElementById('progress-current').querySelector('span').textContent = `${task.progress || 0}%`;
    
    const progressValue = task.progress || 0;
    const slider = document.getElementById('new-progress');
    const numberInput = document.getElementById('new-progress-number');
    const isAdmin = currentUser && currentUser.is_admin;
    const maxProgress = isAdmin ? 100 : 99;
    
    slider.value = progressValue;
    slider.min = 0;
    slider.max = maxProgress;
    
    if (numberInput) {
        numberInput.value = progressValue;
        numberInput.max = maxProgress;
    }
    
    document.getElementById('progress-comment').value = '';
    
    openModal('progress-modal');
}

async function submitProgress() {
    const taskId = document.getElementById('progress-task-id').value;
    const progress = parseInt(document.getElementById('new-progress').value) || 0;
    const comment = document.getElementById('progress-comment').value;
    
    if (progress < 0 || progress > 100) {
        showToast('El progreso debe estar entre 0 y 100', 'warning');
        return;
    }
    
    // Non-admin no puede poner 100%
    const isAdmin = currentUser && currentUser.is_admin;
    const cappedProgress = (!isAdmin && progress >= 100) ? 99 : progress;
    
    const submitBtn = document.querySelector('#progress-form button[type="submit"]');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Guardando...';
    }
    
    try {
        console.log('Enviando progreso:', { taskId, progress: cappedProgress, comment });
        await apiRequest(`/api/tasks/${taskId}/progress`, {
            method: 'POST',
            body: JSON.stringify({ progress: cappedProgress, comment })
        });
        
        showToast(`Avance actualizado a ${cappedProgress}%`, 'success');
        closeModal('progress-modal');
        loadTasks();
        loadDashboard();
    } catch (error) {
        console.error('Error al registrar avance:', error);
        showToast(error.message || 'Error al registrar el avance', 'error');
    } finally {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = '<i class="fas fa-save"></i> Guardar Avance';
        }
    }
}

async function openProgressHistory() {
    if (!currentProgressTaskId) {
        showToast('No se pudo identificar la tarea', 'warning');
        return;
    }
    
    try {
        console.log('Cargando historial de progreso para tarea:', currentProgressTaskId);
        const history = await apiRequest(`/api/tasks/${currentProgressTaskId}/progress`);
        console.log('Historial recibido:', history.length, 'registros');
        renderProgressHistory(history);
        closeModal('progress-modal');
        openModal('progress-history-modal');
    } catch (error) {
        console.error('Error cargando historial de progreso:', error);
        showToast('Error cargando historial: ' + (error.message || 'Error desconocido'), 'error');
    }
}

function renderProgressHistory(history) {
    const container = document.getElementById('progress-history-content');
    
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

// Solo cerrar modal si mousedown Y mouseup ocurren en el overlay
// Esto evita cerrar cuando el usuario selecciona texto y suelta el mouse fuera
document.querySelectorAll('.modal-overlay').forEach(overlay => {
    let mouseDownOnOverlay = false;
    
    overlay.addEventListener('mousedown', (e) => {
        mouseDownOnOverlay = (e.target === overlay);
    });
    
    overlay.addEventListener('mouseup', (e) => {
        if (mouseDownOnOverlay && e.target === overlay) {
            overlay.classList.remove('active');
        }
        mouseDownOnOverlay = false;
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
    ganttCurrentDate.setMonth(ganttCurrentDate.getMonth() - 1);
    renderGantt();
});

document.getElementById('gantt-next-month').addEventListener('click', () => {
    ganttCurrentDate.setMonth(ganttCurrentDate.getMonth() + 1);
    renderGantt();
});

document.getElementById('gantt-today').addEventListener('click', () => {
    // Ir al mes actual
    ganttCurrentDate = new Date();
    renderGantt();
    // Scroll al día de hoy
    setTimeout(() => {
        const todayEl = document.querySelector('.gantt-day.today');
        if (todayEl) {
            todayEl.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        }
    }, 100);
});

// Botón para agregar nueva actividad desde Gantt
document.getElementById('gantt-add-task')?.addEventListener('click', async () => {
    // Verificar si hay un proyecto seleccionado en el Gantt
    const ganttProjectSelect = document.getElementById('gantt-project-select');
    const selectedProjectId = ganttProjectSelect?.value;
    
    if (!selectedProjectId) {
        showToast('Selecciona un proyecto primero', 'warning');
        return;
    }
    
    // Verificar si el usuario es admin
    if (!currentUser?.is_admin) {
        showToast('Solo administradores pueden crear tareas', 'error');
        return;
    }
    
    // Cambiar al proyecto seleccionado si es diferente
    const projectId = parseInt(selectedProjectId);
    if (currentProject?.id !== projectId) {
        const project = projects.find(p => p.id === projectId);
        if (project) {
            currentProject = project;
        }
    }
    
    // Precargar fechas del mes visible en el Gantt
    const startDate = new Date(ganttCurrentDate.getFullYear(), ganttCurrentDate.getMonth(), 1);
    const endDate = new Date(ganttCurrentDate.getFullYear(), ganttCurrentDate.getMonth() + 1, 0);
    
    // Abrir modal de nueva tarea
    document.getElementById('task-id').value = '';
    document.getElementById('task-title').value = '';
    document.getElementById('task-description').value = '';
    document.getElementById('task-status').value = 'todo';
    document.getElementById('task-priority').value = 'medium';
    document.getElementById('task-start').value = startDate.toISOString().split('T')[0];
    document.getElementById('task-due').value = endDate.toISOString().split('T')[0];
    document.getElementById('task-progress').value = 0;
    document.getElementById('progress-value').textContent = '0';
    document.getElementById('task-assignee').value = '';
    document.getElementById('assignee-chips-container').classList.remove('disabled');
    document.getElementById('task-modal-title').textContent = 'Nueva Actividad';
    document.getElementById('delete-task-btn').style.display = 'none';
    document.getElementById('view-history-btn').style.display = 'none';
    
    updateAssigneeSelect();
    updateStageSelect();
    // Mostrar botón guardar (admin ya verificado arriba)
    const saveBtn = document.getElementById('save-task-btn');
    if (saveBtn) saveBtn.style.display = 'block';
    await populateTaskSupGruposChips([], []);
    openModal('task-modal');
});
document.querySelector('.gantt-container')?.addEventListener('wheel', (e) => {
    const container = e.currentTarget;
    // Permitir scroll horizontal siempre (con o sin Shift)
    if (e.deltaX !== 0 || e.shiftKey) {
        e.preventDefault();
        container.scrollLeft += e.shiftKey ? e.deltaY : e.deltaX;
    }
});

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
        // Plantillas de supervisión
        await loadSupTemplates();
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

// ===================== QUICK TASK TEMPLATE (desde Kanban) =====================
async function openQuickTaskTemplateModal() {
    if (!currentProject) {
        showToast('Primero selecciona un proyecto', 'warning');
        return;
    }
    
    // Cargar plantillas si aún no se han cargado
    if (taskTemplates.length === 0) {
        try {
            taskTemplates = await apiRequest('/api/templates/tasks');
        } catch (error) {
            console.error('Error cargando plantillas:', error);
        }
    }
    
    if (taskTemplates.length === 0) {
        showToast('No hay plantillas de tareas disponibles. Crea una desde Administración.', 'info');
        return;
    }
    
    // Cargar plantillas en el selector
    const select = document.getElementById('quick-task-template-select');
    select.innerHTML = '<option value="">Seleccionar plantilla...</option>' +
        taskTemplates.map(t => `<option value="${t.id}">${t.name} (${t.tasks?.length || 0} tareas)</option>`).join('');
    
    // Cargar etapas del proyecto actual
    loadQuickTemplateStages();
    
    // Limpiar preview
    document.getElementById('quick-template-preview').innerHTML = '<p class="text-muted">Selecciona una plantilla para ver las tareas que se crearán</p>';
    
    openModal('quick-task-template-modal');
}

async function loadQuickTemplateStages() {
    const stageSelect = document.getElementById('quick-task-template-stage');
    if (!currentProject) return;
    
    try {
        const stages = await apiRequest(`/api/projects/${currentProject.id}/stages`);
        stageSelect.innerHTML = '<option value="">Sin etapa específica</option>' +
            stages.map(s => `<option value="${s.id}">${s.name}</option>`).join('');
    } catch (error) {
        console.error('Error loading stages:', error);
    }
}

document.getElementById('quick-task-template-select')?.addEventListener('change', (e) => {
    const templateId = parseInt(e.target.value);
    const preview = document.getElementById('quick-template-preview');
    
    if (!templateId) {
        preview.innerHTML = '<p class="text-muted">Selecciona una plantilla para ver las tareas que se crearán</p>';
        return;
    }
    
    const template = taskTemplates.find(t => t.id === templateId);
    if (!template || !template.tasks || template.tasks.length === 0) {
        preview.innerHTML = '<p class="text-muted">Esta plantilla no tiene tareas</p>';
        return;
    }
    
    preview.innerHTML = `
        <div class="template-preview-title">${template.name} - ${template.tasks.length} tareas:</div>
        <div class="template-preview-items">
            ${template.tasks.map(task => `
                <div class="template-preview-item">
                    <i class="fas fa-check-circle"></i>
                    <span>${task.title}</span>
                </div>
            `).join('')}
        </div>
    `;
});

document.getElementById('apply-quick-template-btn')?.addEventListener('click', async () => {
    const templateId = document.getElementById('quick-task-template-select').value;
    const stageId = document.getElementById('quick-task-template-stage').value;
    
    if (!templateId) {
        showToast('Selecciona una plantilla', 'warning');
        return;
    }
    
    if (!currentProject) {
        showToast('No hay proyecto seleccionado', 'error');
        return;
    }
    
    try {
        const url = `/api/projects/${currentProject.id}/apply-task-template/${templateId}${stageId ? `?stage_id=${stageId}` : ''}`;
        const result = await apiRequest(url, { method: 'POST' });
        showToast(result.message, 'success');
        closeModal('quick-task-template-modal');
        
        // Recargar tareas y dashboard
        await loadTasks();
        loadDashboard();
    } catch (error) {
        showToast(error.message, 'error');
    }
});

// Event listener para el botón de plantilla en kanban
document.getElementById('apply-task-template-btn')?.addEventListener('click', openQuickTaskTemplateModal);

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
                                    <div class="team-member-projects">
                                        ${(member.projects && member.projects.length)
                                            ? member.projects.map(p => `
                                                <span class="team-member-project-chip ${p.is_active ? '' : 'inactive'}" style="--chip-color: ${p.color}">
                                                    <span class="dot"></span>${p.name}
                                                </span>
                                            `).join('')
                                            : '<span class="team-member-project-empty">Sin proyectos</span>'}
                                    </div>
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

// ===================== PLANTILLAS DE SUPERVISIÓN =====================
let supTemplates = [];
let supTemplateFilterActive = 'all';
let applySupTemplateFilterActive = 'all';

async function loadSupTemplates() {
    try {
        supTemplates = await apiRequest('/api/templates/supervision');
    } catch (e) {
        supTemplates = [];
    }
    renderSupTemplates();
}

function renderSupTemplates() {
    const container = document.getElementById('sup-templates-list');
    if (!container) return;

    const filtered = supTemplateFilterActive === 'all'
        ? supTemplates
        : supTemplates.filter(t => t.tipo === supTemplateFilterActive);

    if (!filtered.length) {
        container.innerHTML = `<div class="empty-state"><i class="fas fa-folder-open"></i><p>No hay plantillas de supervisión</p></div>`;
        return;
    }

    container.innerHTML = filtered.map(t => {
        const isCompras = t.tipo === 'COMPRAS';
        const badgeColor = isCompras ? 'linear-gradient(135deg,#6366f1,#8b5cf6)' : 'linear-gradient(135deg,#10b981,#34d399)';
        const icon = isCompras ? 'fa-box' : 'fa-handshake';
        return `
        <div class="template-card">
            <div class="template-card-header">
                <div style="display:flex;align-items:center;gap:8px">
                    <span style="background:${badgeColor};color:#fff;border-radius:6px;padding:3px 8px;font-size:11px;font-weight:700">
                        <i class="fas ${icon}"></i> ${t.tipo}
                    </span>
                    <h5 style="margin:0">${escapeHtml(t.nombre)}</h5>
                </div>
                <div class="template-card-actions">
                    <button class="btn-icon" onclick="openSupTemplateModal('${t.tipo}', ${t.id})" title="Editar"><i class="fas fa-edit"></i></button>
                    <button class="btn-icon" onclick="deleteSupTemplate(${t.id})" title="Eliminar"><i class="fas fa-trash"></i></button>
                </div>
            </div>
            ${t.descripcion ? `<p class="template-card-description">${escapeHtml(t.descripcion)}</p>` : ''}
            <div class="template-card-items">
                ${(t.items || []).slice(0, 4).map(i => `<span class="template-item-badge">${escapeHtml(i.actividad)}</span>`).join('')}
                ${(t.items || []).length > 4 ? `<span class="template-item-badge">+${t.items.length - 4} más</span>` : ''}
            </div>
            <div class="template-card-footer">
                <span class="template-card-meta">${(t.items || []).length} actividades</span>
                <button class="btn btn-sm btn-primary" onclick="openApplySupTemplateModal(${t.id})">
                    <i class="fas fa-copy"></i> Aplicar a obra
                </button>
            </div>
        </div>`;
    }).join('');
}

function filterSupTemplates(tipo, btn) {
    supTemplateFilterActive = tipo;
    document.querySelectorAll('[data-stfilter]').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderSupTemplates();
}

function filterApplySupTemplates(tipo, btn) {
    applySupTemplateFilterActive = tipo;
    const parent = btn.closest('.modal-body') || btn.closest('.modal-overlay');
    parent.querySelectorAll('.sup-pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    renderApplySupTemplateList();
}

function renderApplySupTemplateList() {
    const container = document.getElementById('apply-sup-template-list');
    if (!container) return;
    const filtered = applySupTemplateFilterActive === 'all'
        ? supTemplates
        : supTemplates.filter(t => t.tipo === applySupTemplateFilterActive);

    if (!filtered.length) {
        container.innerHTML = `<div class="empty-state" style="padding:20px"><i class="fas fa-folder-open"></i><p>No hay plantillas</p></div>`;
        return;
    }
    container.innerHTML = filtered.map(t => {
        const isC = t.tipo === 'COMPRAS';
        const col = isC ? '#6366f1' : '#10b981';
        return `
        <label class="sup-template-check-row" style="display:flex;align-items:flex-start;gap:10px;background:var(--card-bg);border:1px solid var(--border-color);border-radius:8px;padding:10px 12px;cursor:pointer">
            <input type="checkbox" class="apply-sup-chk" data-id="${t.id}" style="margin-top:3px;accent-color:${col}">
            <div style="flex:1">
                <div style="display:flex;align-items:center;gap:6px;margin-bottom:3px">
                    <span style="background:${col}22;color:${col};border-radius:4px;padding:1px 7px;font-size:11px;font-weight:700">${t.tipo}</span>
                    <span style="font-weight:600;font-size:13px">${escapeHtml(t.nombre)}</span>
                </div>
                <div style="font-size:11px;color:var(--text-muted)">${(t.items||[]).length} actividades${t.descripcion ? ' · ' + escapeHtml(t.descripcion.substring(0,60)) : ''}</div>
            </div>
        </label>`;
    }).join('');
}

async function openSupTemplateModal(tipo, editId = null) {
    // Reset
    document.getElementById('sup-template-id').value = editId || '';
    document.getElementById('sup-template-tipo').value = tipo;
    document.getElementById('sup-template-items').innerHTML = '';

    const isCompras = tipo === 'COMPRAS';
    const color = isCompras ? '#6366f1' : '#10b981';
    const icon  = isCompras ? 'fa-box' : 'fa-handshake';
    document.getElementById('sup-template-modal-title').innerHTML =
        `<i class="fas fa-clipboard-check"></i> Plantilla de ${isCompras ? 'Compras' : 'Servicios'}`;
    document.getElementById('sup-template-tipo-badge').innerHTML =
        `<span style="background:${color};color:#fff;padding:4px 12px;border-radius:6px;font-size:12px;font-weight:700"><i class="fas ${icon}"></i> ${tipo}</span>`;

    if (editId) {
        const t = supTemplates.find(x => x.id === editId);
        if (t) {
            document.getElementById('sup-template-nombre').value = t.nombre;
            document.getElementById('sup-template-desc').value = t.descripcion || '';
            (t.items || []).forEach(item => addSupTemplateItem(item.actividad, item.prioridad));
        }
    } else {
        document.getElementById('sup-template-nombre').value = '';
        document.getElementById('sup-template-desc').value = '';
        addSupTemplateItem();
    }
    document.getElementById('sup-template-modal').classList.add('active');
}

function addSupTemplateItem(actividad = '', prioridad = 3) {
    const container = document.getElementById('sup-template-items');
    const row = document.createElement('div');
    row.className = 'template-item-row';
    row.style.cssText = 'display:flex;gap:8px;align-items:center;margin-bottom:6px';
    row.innerHTML = `
        <input type="text" placeholder="Nombre de la actividad" class="sup-item-actividad"
               value="${escapeHtml(actividad)}" required style="flex:1">
        <select class="sup-item-prioridad" style="width:90px;font-size:12px">
            ${[1,2,3,4,5].map(n => `<option value="${n}"${n==prioridad?' selected':''}>${n===1?'Urgente':n===5?'Baja':n}</option>`).join('')}
        </select>
        <button type="button" class="btn-icon" onclick="this.parentElement.remove()"><i class="fas fa-times"></i></button>
    `;
    container.appendChild(row);
}

document.getElementById('sup-template-form')?.addEventListener('submit', async (e) => {
    e.preventDefault();
    const id   = document.getElementById('sup-template-id').value;
    const tipo = document.getElementById('sup-template-tipo').value;
    const nombre = document.getElementById('sup-template-nombre').value.trim();
    const descripcion = document.getElementById('sup-template-desc').value.trim();
    const items = [];
    document.querySelectorAll('#sup-template-items .template-item-row').forEach((row, idx) => {
        const actividad = row.querySelector('.sup-item-actividad').value.trim();
        const prioridad = parseInt(row.querySelector('.sup-item-prioridad').value);
        if (actividad) items.push({ actividad, prioridad, position: idx });
    });
    if (!nombre) { showToast('El nombre es obligatorio', 'warning'); return; }
    if (!items.length) { showToast('Agrega al menos una actividad', 'warning'); return; }

    try {
        const payload = { nombre, tipo, descripcion, items };
        if (id) {
            await apiRequest(`/api/templates/supervision/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
        } else {
            await apiRequest('/api/templates/supervision', { method: 'POST', body: JSON.stringify(payload) });
        }
        showToast(id ? 'Plantilla actualizada' : 'Plantilla creada', 'success');
        document.getElementById('sup-template-modal').classList.remove('active');
        await loadSupTemplates();
    } catch (err) {
        showToast(err.message, 'error');
    }
});

async function deleteSupTemplate(id) {
    if (!confirm('¿Eliminar esta plantilla de supervisión?')) return;
    try {
        await apiRequest(`/api/templates/supervision/${id}`, { method: 'DELETE' });
        showToast('Plantilla eliminada', 'success');
        await loadSupTemplates();
    } catch (err) {
        showToast(err.message, 'error');
    }
}

// -- Aplicar plantillas a proyecto --
async function openApplySupTemplateModal(preSelectId = null) {
    // Cargar plantillas si no están
    if (!supTemplates.length) await loadSupTemplates();

    // Poblar selector de proyectos
    const sel = document.getElementById('apply-sup-project');
    try {
        const projs = await apiRequest('/api/projects');
        sel.innerHTML = '<option value="">Seleccionar proyecto…</option>' +
            projs.map(p => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join('');
        // Pre-seleccionar proyecto actual de supervisión
        if (supCurrentProject) sel.value = supCurrentProject;
    } catch (e) { /* ignore */ }

    applySupTemplateFilterActive = 'all';
    // Reset filter pills UI
    document.querySelectorAll('#apply-sup-template-modal .sup-pill').forEach((b, i) => {
        b.classList.toggle('active', i === 0);
    });
    renderApplySupTemplateList();

    // Pre-seleccionar si viene de un template específico
    if (preSelectId) {
        setTimeout(() => {
            const chk = document.querySelector(`#apply-sup-template-list .apply-sup-chk[data-id="${preSelectId}"]`);
            if (chk) chk.checked = true;
        }, 50);
    }

    document.getElementById('apply-sup-template-modal').classList.add('active');
}

async function applySelectedSupTemplates() {
    const projectId = document.getElementById('apply-sup-project').value;
    if (!projectId) { showToast('Selecciona un proyecto', 'warning'); return; }

    const checked = [...document.querySelectorAll('#apply-sup-template-list .apply-sup-chk:checked')];
    if (!checked.length) { showToast('Selecciona al menos una plantilla', 'warning'); return; }

    let ok = 0, fail = 0;
    for (const chk of checked) {
        try {
            await apiRequest(`/api/projects/${projectId}/apply-sup-template/${chk.dataset.id}`, { method: 'POST' });
            ok++;
        } catch (e) { fail++; }
    }

    if (ok) showToast(`${ok} categoría(s) aplicada(s) al proyecto`, 'success');
    if (fail) showToast(`${fail} no pudieron aplicarse`, 'error');

    document.getElementById('apply-sup-template-modal').classList.remove('active');

    // Recargar supervisión si el proyecto activo es el mismo
    if (supCurrentProject && parseInt(projectId) === supCurrentProject) {
        await supLoadProject(supCurrentProject);
    }
}

// ===================== REPORTES PDF =====================
async function downloadPendingTasksReport() {
    const projectId = document.getElementById('report-project-filter')?.value || '';
    const userId = document.getElementById('report-user-filter')?.value || '';
    let url = `/api/reports/pending-tasks-pdf`;
    const params = [];
    if (projectId) params.push('project_id=' + projectId);
    if (userId) params.push('user_id=' + userId);
    if (params.length) url += '?' + params.join('&');
    try {
        showToast('Generando PDF…', 'info');
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (!response.ok) throw new Error('Error generando reporte');
        const blob = await response.blob();
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `tareas_pendientes_${new Date().toISOString().slice(0,10)}.pdf`;
        link.click();
        URL.revokeObjectURL(link.href);
        showToast('PDF descargado', 'success');
    } catch (err) {
        showToast('Error al generar el reporte', 'error');
    }
}

async function downloadMyTasksReport() {
    if (!currentUser) return;
    const url = `/api/reports/pending-tasks-pdf?user_id=${currentUser.id}`;
    try {
        showToast('Generando PDF…', 'info');
        const response = await fetch(url, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('token')}` }
        });
        if (!response.ok) throw new Error('Error generando reporte');
        const blob = await response.blob();
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = `mis_tareas_pendientes_${new Date().toISOString().slice(0,10)}.pdf`;
        link.click();
        URL.revokeObjectURL(link.href);
        showToast('PDF descargado', 'success');
    } catch (err) {
        showToast('Error al generar el reporte', 'error');
    }
}

async function loadReportsPanel() {
    // Poblar selector de proyectos en reportes
    const sel = document.getElementById('report-project-filter');
    const selUser = document.getElementById('report-user-filter');
    try {
        if (sel) {
            const projs = await apiRequest('/api/projects');
            sel.innerHTML = '<option value="">Todas las obras</option>' +
                projs.map(p => `<option value="${p.id}">${escapeHtml(p.name)}</option>`).join('');
        }
        if (selUser) {
            const users = await apiRequest('/api/users');
            selUser.innerHTML = '<option value="">Todos los usuarios</option>' +
                users.map(u => `<option value="${u.id}">${escapeHtml(u.name)}</option>`).join('');
        }
    } catch (e) { /* ignore */ }
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
window.deleteUser = deleteUser;
window.openEditUserModal = openEditUserModal;
window.editProject = editProject;
window.removeTempStage = removeTempStage;
window.removeAdmin = removeAdmin;
window.makeAdmin = makeAdmin;
window.updateTempStage = updateTempStage;
window.applyStageTemplateToProject = applyStageTemplateToProject;
window.openQuickTaskTemplateModal = openQuickTaskTemplateModal;
window.toggleGanttStages = toggleGanttStages;
// Plantillas de supervisión
window.openSupTemplateModal = openSupTemplateModal;
window.addSupTemplateItem = addSupTemplateItem;
window.deleteSupTemplate = deleteSupTemplate;
window.filterSupTemplates = filterSupTemplates;
window.filterApplySupTemplates = filterApplySupTemplates;
window.openApplySupTemplateModal = openApplySupTemplateModal;
window.applySelectedSupTemplates = applySelectedSupTemplates;
// Reportes
window.downloadPendingTasksReport = downloadPendingTasksReport;
window.downloadMyTasksReport = downloadMyTasksReport;

// ===================== INIT ON LOAD =====================
document.addEventListener('DOMContentLoaded', async () => {
    const token = getToken();
    
    if (token) {
        const storedUser = getStoredUser();
        if (storedUser) {
            currentUser = storedUser;
            showMainApp();
            updateUserInfo();
            setupAdminUI();
        }
        try {
            currentUser = await apiRequest('/api/auth/me');
            setStoredUser(currentUser);
            initApp();
        } catch (error) {
            if (error.message === 'No autorizado') {
                showAuthScreen();
            } else {
                showToast('No se pudo validar la sesión. Intenta de nuevo.', 'warning');
            }
        }
    } else {
        showAuthScreen();
    }
});

// ===================== HITOS (MILESTONES) =====================

function openMilestoneModal(milestoneId = null) {
    if (!currentProject) {
        showToast('Selecciona un proyecto primero', 'warning');
        return;
    }

    const modal = document.getElementById('milestone-modal');
    const titleEl = document.getElementById('milestone-modal-title');
    const deleteBtn = document.getElementById('milestone-delete-btn');
    const attachmentsSection = document.getElementById('milestone-attachments-section');

    // Reset form
    document.getElementById('milestone-id').value = '';
    document.getElementById('milestone-title').value = '';
    document.getElementById('milestone-date').value = '';
    document.getElementById('milestone-type').value = 'meeting';
    document.getElementById('milestone-description').value = '';

    // Reset pending files for create mode
    window._pendingMilestoneFiles = [];

    // Always show attachments section
    attachmentsSection.style.display = 'block';

    if (milestoneId) {
        // Edit mode
        const milestone = milestones.find(m => m.id === milestoneId);
        if (!milestone) {
            showToast('Hito no encontrado', 'error');
            return;
        }
        titleEl.innerHTML = '<i class="fas fa-diamond"></i> Editar Hito';
        document.getElementById('milestone-id').value = milestone.id;
        document.getElementById('milestone-title').value = milestone.title;
        document.getElementById('milestone-date').value = milestone.date ? milestone.date.split('T')[0] : '';
        document.getElementById('milestone-type').value = milestone.milestone_type;
        document.getElementById('milestone-description').value = milestone.description || '';

        // Show delete button for admin
        if (currentUser && currentUser.is_admin) {
            deleteBtn.style.display = 'inline-flex';
        } else {
            deleteBtn.style.display = 'none';
        }
        renderMilestoneAttachments(milestone.attachments || []);
    } else {
        // Create mode
        titleEl.innerHTML = '<i class="fas fa-diamond"></i> Nuevo Hito';
        deleteBtn.style.display = 'none';
        // Default date to today
        const today = new Date().toISOString().split('T')[0];
        document.getElementById('milestone-date').value = today;
        // Show empty pending files list
        renderPendingMilestoneFiles();
    }

    modal.classList.add('active');
}

async function saveMilestone() {
    const id = document.getElementById('milestone-id').value;
    const title = document.getElementById('milestone-title').value.trim();
    const date = document.getElementById('milestone-date').value;
    const milestoneType = document.getElementById('milestone-type').value;
    const description = document.getElementById('milestone-description').value.trim();

    if (!title || !date) {
        showToast('Título y fecha son requeridos', 'warning');
        return;
    }

    const data = {
        title,
        date: new Date(date + 'T12:00:00').toISOString(),
        milestone_type: milestoneType,
        description: description || null
    };

    try {
        if (id) {
            await apiRequest(`/api/milestones/${id}`, {
                method: 'PUT',
                body: JSON.stringify(data)
            });
            showToast('Hito actualizado', 'success');
        } else {
            const created = await apiRequest(`/api/projects/${currentProject.id}/milestones`, {
                method: 'POST',
                body: JSON.stringify(data)
            });
            // Upload pending files after creation
            const pendingFiles = window._pendingMilestoneFiles || [];
            if (pendingFiles.length > 0 && created && created.id) {
                for (const file of pendingFiles) {
                    await uploadMilestoneAttachment(created.id, file);
                }
                window._pendingMilestoneFiles = [];
            }
            showToast('Hito creado', 'success');
        }
        document.getElementById('milestone-modal').classList.remove('active');
        await loadTasks();
    } catch (error) {
        showToast('Error guardando hito: ' + error.message, 'error');
    }
}

async function deleteMilestone() {
    const id = document.getElementById('milestone-id').value;
    if (!id) return;

    if (!confirm('¿Estás seguro de eliminar este hito?')) return;

    try {
        await apiRequest(`/api/milestones/${id}`, { method: 'DELETE' });
        showToast('Hito eliminado', 'success');
        document.getElementById('milestone-modal').classList.remove('active');
        await loadTasks();
    } catch (error) {
        showToast('Error eliminando hito: ' + error.message, 'error');
    }
}

function renderMilestoneAttachments(attachments) {
    const list = document.getElementById('milestone-attachments-list');
    if (!attachments || attachments.length === 0) {
        list.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem; padding: 8px 0;">Sin archivos adjuntos</div>';
        return;
    }

    list.innerHTML = attachments.map(att => {
        const isImage = att.file_type && att.file_type.startsWith('image/');
        const icon = isImage ? 'fa-image' : att.file_type && att.file_type.includes('pdf') ? 'fa-file-pdf' : 'fa-file';
        const isAdmin = currentUser && currentUser.is_admin;
        return `
            <div class="milestone-attachment-item">
                <i class="fas ${icon} attachment-icon"></i>
                <a href="${att.file_url}" target="_blank" class="attachment-name" title="${att.file_name}">${att.file_name}</a>
                ${isAdmin ? `<button class="btn-icon btn-delete-attachment" onclick="deleteMilestoneAttachment(${att.milestone_id}, ${att.id})" title="Eliminar">
                    <i class="fas fa-times"></i>
                </button>` : ''}
            </div>
        `;
    }).join('');
}

async function uploadMilestoneAttachment(milestoneId, file) {
    const formData = new FormData();
    formData.append('file', file);

    try {
        const token = localStorage.getItem('token');
        const response = await fetch(`/api/milestones/${milestoneId}/attachments`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });

        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || 'Error subiendo archivo');
        }

        showToast('Archivo adjuntado', 'success');
        // Reload milestones to get updated attachments
        const updatedMilestones = await apiRequest(`/api/projects/${currentProject.id}/milestones`);
        milestones = updatedMilestones;
        const milestone = milestones.find(m => m.id === milestoneId);
        if (milestone) {
            renderMilestoneAttachments(milestone.attachments || []);
        }
    } catch (error) {
        showToast('Error subiendo archivo: ' + error.message, 'error');
    }
}

async function deleteMilestoneAttachment(milestoneId, attachmentId) {
    if (!confirm('¿Eliminar este archivo adjunto?')) return;

    try {
        await apiRequest(`/api/milestones/${milestoneId}/attachments/${attachmentId}`, { method: 'DELETE' });
        showToast('Adjunto eliminado', 'success');
        // Reload milestones to get updated attachments
        const updatedMilestones = await apiRequest(`/api/projects/${currentProject.id}/milestones`);
        milestones = updatedMilestones;
        const milestone = milestones.find(m => m.id === milestoneId);
        if (milestone) {
            renderMilestoneAttachments(milestone.attachments || []);
        }
    } catch (error) {
        showToast('Error eliminando adjunto: ' + error.message, 'error');
    }
}

// File input change listener for milestone attachments
document.addEventListener('DOMContentLoaded', () => {
    const fileInput = document.getElementById('milestone-file-input');
    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;
            const milestoneId = document.getElementById('milestone-id').value;
            if (!milestoneId) {
                // Create mode: store file in pending list
                if (!window._pendingMilestoneFiles) window._pendingMilestoneFiles = [];
                window._pendingMilestoneFiles.push(file);
                renderPendingMilestoneFiles();
                showToast('Archivo agregado, se subirá al guardar el hito', 'info');
            } else {
                // Edit mode: upload immediately
                uploadMilestoneAttachment(parseInt(milestoneId), file);
            }
            fileInput.value = ''; // Reset input
        });
    }
});

function renderPendingMilestoneFiles() {
    const list = document.getElementById('milestone-attachments-list');
    const pendingFiles = window._pendingMilestoneFiles || [];
    if (pendingFiles.length === 0) {
        list.innerHTML = '<div style="color: var(--text-muted); font-size: 0.85rem; padding: 8px 0;">Sin archivos adjuntos</div>';
        return;
    }
    list.innerHTML = pendingFiles.map((file, index) => {
        const isImage = file.type && file.type.startsWith('image/');
        const icon = isImage ? 'fa-image' : file.type && file.type.includes('pdf') ? 'fa-file-pdf' : 'fa-file';
        return `
            <div class="milestone-attachment-item">
                <i class="fas ${icon} attachment-icon"></i>
                <span class="attachment-name" title="${file.name}">${file.name}</span>
                <span style="color: var(--text-muted); font-size: 0.75rem; margin-left: 4px;">(pendiente)</span>
                <button class="btn-icon btn-delete-attachment" onclick="removePendingMilestoneFile(${index})" title="Quitar">
                    <i class="fas fa-times"></i>
                </button>
            </div>
        `;
    }).join('');
}

function removePendingMilestoneFile(index) {
    if (window._pendingMilestoneFiles) {
        window._pendingMilestoneFiles.splice(index, 1);
        renderPendingMilestoneFiles();
    }
}

// Recalcular Gantt cuando cambie el tamaño de la ventana
let resizeTimeout;
window.addEventListener('resize', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        const ganttView = document.getElementById('gantt-view');
        if (ganttView && ganttView.classList.contains('active')) {
            renderGantt();
        }
    }, 250);
});

// ===================== SUPERVISIÓN =====================
let supActiveTab = 'resumen';
let supResumenFilter = 'all';
let supComprasFilter = 'all';
let supServiciosFilter = 'all';
let supCurrentProject = null;

// Loaded data
let SUP_RESUMEN = [];
let SUP_COMPRAS = [];
let SUP_SERVICIOS = [];

function supStatusClass(status) {
  if (!status) return 'sin-estado';
  const s = status.toUpperCase();
  if (s === 'CONTRATADO') return 'contratado';
  if (s === 'EN PROCESO') return 'en-proceso';
  if (s === 'PENDIENTE') return 'pendiente';
  if (s === 'ENTREGADO') return 'entregado';
  if (s === 'APROBADO') return 'aprobado';
  if (s === 'POR COTIZAR') return 'por-cotizar';
  return 'sin-estado';
}

function supStatusDot(status) {
  const map = { 'CONTRATADO': '●', 'EN PROCESO': '◐', 'PENDIENTE': '○', 'ENTREGADO': '✓', 'APROBADO': '✓', 'POR COTIZAR': '◌' };
  return map[(status || '').toUpperCase()] || '–';
}

function supProgressClass(pct) {
  if (pct === 0) return 'zero';
  if (pct >= 50) return 'high';
  if (pct >= 20) return 'medium';
  return 'low';
}

function supPriorityClass(p) {
  if (p === 1) return 'prio-1';
  if (p === 2) return 'prio-2';
  if (p === 3) return 'prio-3';
  return 'prio-other';
}

async function supLoadGlobal() {
  supCurrentProject = null;
  // Mostrar dashboard global, ocultar resumen por proyecto
  const globalDash = document.getElementById('sup-global-dashboard');
  const projectResumen = document.getElementById('sup-project-resumen');
  if (globalDash) globalDash.style.display = '';
  if (projectResumen) projectResumen.style.display = 'none';
  // Ocultar tabs de compras/servicios (no aplica para vista global)
  document.querySelectorAll('#sup-tabs .sup-tab[data-tab="compras"], #sup-tabs .sup-tab[data-tab="servicios"]')
    .forEach(b => b.style.display = 'none');
  // Activar tab resumen
  document.querySelectorAll('#sup-tabs .sup-tab').forEach(b => b.classList.remove('active'));
  const resumenTab = document.querySelector('#sup-tabs .sup-tab[data-tab="resumen"]');
  if (resumenTab) resumenTab.classList.add('active');
  document.querySelectorAll('.sup-content').forEach(c => c.classList.remove('active'));
  const resumenContent = document.getElementById('sup-resumen');
  if (resumenContent) resumenContent.classList.add('active');

  try {
    const data = await apiRequest('/api/supervision/global/resumen');
    renderSupGlobalDashboard(data || []);
  } catch (e) {
    renderSupGlobalDashboard([]);
  }
}

function renderSupGlobalDashboard(data) {
  // KPIs globales
  const totalObras = data.length;
  const totalGrupos = data.reduce((a, p) => a + p.total_grupos, 0);
  const totalItems = data.reduce((a, p) => a + p.total_items, 0);
  const totalAprobados = data.reduce((a, p) => a + p.aprobados, 0);
  const totalPendientes = data.reduce((a, p) => a + p.pendientes, 0);
  const avgAvance = totalObras ? Math.round(data.reduce((a, p) => a + p.avg_avance, 0) / totalObras) : 0;

  const kpisEl = document.getElementById('sup-global-kpis');
  if (kpisEl) {
    const kpis = [
      { value: totalObras,    label: 'Obras activas',    icon: 'fa-hard-hat',    color: 'linear-gradient(135deg,#6366f1,#8b5cf6)' },
      { value: totalGrupos,   label: 'Grupos totales',   icon: 'fa-layer-group', color: 'linear-gradient(135deg,#06b6d4,#0ea5e9)' },
      { value: totalItems,    label: 'Actividades',      icon: 'fa-list',        color: 'linear-gradient(135deg,#3b82f6,#6366f1)' },
      { value: totalAprobados,label: 'Aprobados',        icon: 'fa-check-circle',color: 'linear-gradient(135deg,#10b981,#34d399)' },
      { value: totalPendientes,label:'Pendientes',       icon: 'fa-clock',       color: 'linear-gradient(135deg,#ef4444,#f87171)' },
      { value: avgAvance + '%',label:'Avance promedio',  icon: 'fa-chart-line',  color: 'linear-gradient(135deg,#f59e0b,#fbbf24)' },
    ];
    kpisEl.innerHTML = kpis.map(k => `
      <div class="sup-kpi">
        <div class="sup-kpi-icon" style="background:${k.color}"><i class="fas ${k.icon}"></i></div>
        <div class="sup-kpi-body">
          <span class="sup-kpi-value">${k.value}</span>
          <span class="sup-kpi-label">${k.label}</span>
        </div>
      </div>
    `).join('');
  }

  // Tabla por obra
  const tbody = document.getElementById('sup-global-tbody');
  if (!tbody) return;

  if (!data.length) {
    tbody.innerHTML = `<tr><td colspan="7"><div class="sup-empty"><i class="fas fa-inbox"></i><p>No hay datos de supervisión en ninguna obra</p></div></td></tr>`;
    return;
  }

  tbody.innerHTML = data.map(p => {
    const pctClass = p.avg_avance >= 80 ? 'sup-prog-high' : p.avg_avance >= 40 ? 'sup-prog-mid' : 'sup-prog-low';
    const avColor = p.avg_avance >= 80 ? '#34d399' : p.avg_avance >= 40 ? '#fbbf24' : '#f87171';
    return `
      <tr style="cursor:pointer" onclick="document.getElementById('sup-project-select').value='${p.project_id}'; supLoadProject(${p.project_id})">
        <td>
          <div style="display:flex;align-items:center;gap:8px">
            <div style="width:10px;height:10px;border-radius:50%;background:${p.project_color};flex-shrink:0"></div>
            <span style="font-weight:600">${escapeHtml(p.project_name)}</span>
          </div>
        </td>
        <td style="text-align:center">
          <span title="Compras">${p.compras_grupos}<i class="fas fa-box" style="font-size:9px;opacity:.6;margin-left:3px;color:#6366f1"></i></span>
          <span style="color:var(--text-muted);margin:0 4px">+</span>
          <span title="Servicios">${p.servicios_grupos}<i class="fas fa-handshake" style="font-size:9px;opacity:.6;margin-left:3px;color:#34d399"></i></span>
        </td>
        <td style="text-align:center;font-weight:600">${p.total_items}</td>
        <td style="text-align:center">${p.aprobados > 0 ? `<span style="color:#34d399;font-weight:600">${p.aprobados}</span>` : '–'}</td>
        <td style="text-align:center">${p.pendientes > 0 ? `<span style="color:#f87171;font-weight:600">${p.pendientes}</span>` : '–'}</td>
        <td class="date-cell">${p.fecha_proxima || '–'}</td>
        <td>
          <div style="display:flex;align-items:center;gap:8px">
            <div class="sup-avance-bar" style="flex:1;min-width:80px">
              <div class="sup-avance-fill ${pctClass}" style="width:${p.avg_avance}%"></div>
            </div>
            <span class="sup-avance-text" style="color:${avColor}">${p.avg_avance}%</span>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function supLoadProject(projectId) {
  supCurrentProject = projectId;
  // Restaurar tabs de compras/servicios
  document.querySelectorAll('#sup-tabs .sup-tab[data-tab="compras"], #sup-tabs .sup-tab[data-tab="servicios"]')
    .forEach(b => b.style.display = '');
  // Mostrar resumen por proyecto, ocultar dashboard global
  const globalDash = document.getElementById('sup-global-dashboard');
  const projectResumen = document.getElementById('sup-project-resumen');
  if (globalDash) globalDash.style.display = 'none';
  if (projectResumen) projectResumen.style.display = '';
  try {
    const [resumen, compras, servicios] = await Promise.all([
      apiRequest(`/api/supervision/${projectId}/resumen`),
      apiRequest(`/api/supervision/${projectId}/compras`),
      apiRequest(`/api/supervision/${projectId}/servicios`),
    ]);
    SUP_RESUMEN = resumen || [];
    SUP_COMPRAS = compras || [];
    SUP_SERVICIOS = servicios || [];
  } catch (e) {
    SUP_RESUMEN = [];
    SUP_COMPRAS = [];
    SUP_SERVICIOS = [];
  }
  renderSupKPIs();
  renderSupResumen(supResumenFilter, document.getElementById('sup-search')?.value || '');
  renderSupCompras(supComprasFilter, document.getElementById('sup-compras-search')?.value || '');
  renderSupServicios(supServiciosFilter, document.getElementById('sup-servicios-search')?.value || '');
}

async function renderSupervisionView() {
  // Populate project selector
  try {
    const projectsList = await apiRequest('/api/projects');
    const select = document.getElementById('sup-project-select');
    select.innerHTML = '<option value="">Todas las obras</option>' +
      projectsList.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
    select.onchange = () => {
      if (select.value) {
        supLoadProject(parseInt(select.value));
      } else {
        supLoadGlobal();
      }
    };
    if (supCurrentProject) {
      select.value = supCurrentProject;
      await supLoadProject(supCurrentProject);
    } else {
      // Sin proyecto seleccionado: mostrar resumen global
      await supLoadGlobal();
    }
  } catch (e) {}

  // Tabs
  document.querySelectorAll('#sup-tabs .sup-tab').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('#sup-tabs .sup-tab').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      supActiveTab = btn.dataset.tab;
      document.querySelectorAll('.sup-content').forEach(c => c.classList.remove('active'));
      document.getElementById('sup-' + supActiveTab).classList.add('active');
    };
  });

  // Resumen filters
  document.querySelectorAll('#sup-status-filters .sup-pill').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('#sup-status-filters .sup-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      supResumenFilter = btn.dataset.filter;
      renderSupResumen(supResumenFilter, document.getElementById('sup-search').value);
    };
  });
  document.getElementById('sup-search').oninput = (e) => {
    renderSupResumen(supResumenFilter, e.target.value);
  };

  // Compras filters
  document.querySelectorAll('#sup-compras-filters .sup-pill').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('#sup-compras-filters .sup-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      supComprasFilter = btn.dataset.filter;
      renderSupCompras(supComprasFilter, document.getElementById('sup-compras-search').value);
    };
  });
  document.getElementById('sup-compras-search').oninput = (e) => {
    renderSupCompras(supComprasFilter, e.target.value);
  };

  // Servicios filters
  document.querySelectorAll('#sup-servicios-filters .sup-pill').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('#sup-servicios-filters .sup-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      supServiciosFilter = btn.dataset.filter;
      renderSupServicios(supServiciosFilter, document.getElementById('sup-servicios-search').value);
    };
  });
  document.getElementById('sup-servicios-search').oninput = (e) => {
    renderSupServicios(supServiciosFilter, e.target.value);
  };

  // "Nuevo grupo" buttons
  const newComprasGrupoBtn = document.getElementById('sup-compras-new-grupo');
  if (newComprasGrupoBtn) newComprasGrupoBtn.onclick = () => openSupComprasGrupoModal();
  const newServiciosGrupoBtn = document.getElementById('sup-servicios-new-grupo');
  if (newServiciosGrupoBtn) newServiciosGrupoBtn.onclick = () => openSupServiciosGrupoModal();

  // Wire the modal forms (idempotent)
  initSupModals();
}

function _allItems() {
  const c = SUP_COMPRAS.flatMap(g => (g.items || []).map(i => ({ ...i, _tipo: 'compra' })));
  const s = SUP_SERVICIOS.flatMap(g => (g.items || []).map(i => ({ ...i, _tipo: 'servicio' })));
  return [...c, ...s];
}

function renderSupKPIs() {
  const allItems = _allItems();
  const totalItems = allItems.length;
  const totalGrupos = SUP_COMPRAS.length + SUP_SERVICIOS.length;
  const aprobados = allItems.filter(i => (i.status_compra || '').toUpperCase() === 'APROBADO').length;
  const pendientes = allItems.filter(i => (i.status_compra || '').toUpperCase() === 'PENDIENTE').length;
  const avgAvance = totalItems ? Math.round(allItems.reduce((a, i) => a + (i.avance || 0), 0) / totalItems) : 0;

  const kpis = [
    { value: totalGrupos, label: 'Grupos', icon: 'fa-layer-group', color: 'linear-gradient(135deg,#6366f1,#8b5cf6)' },
    { value: totalItems,  label: 'Total Actividades', icon: 'fa-list', color: 'linear-gradient(135deg,#06b6d4,#0ea5e9)' },
    { value: aprobados,   label: 'Aprobados', icon: 'fa-check-circle', color: 'linear-gradient(135deg,#10b981,#34d399)' },
    { value: pendientes,  label: 'Pendientes', icon: 'fa-clock', color: 'linear-gradient(135deg,#ef4444,#f87171)' },
    { value: avgAvance + '%', label: 'Avance Promedio', icon: 'fa-chart-line', color: 'linear-gradient(135deg,#f59e0b,#fbbf24)' },
  ];

  document.getElementById('sup-kpis').innerHTML = kpis.map(k => `
    <div class="sup-kpi">
      <div class="sup-kpi-icon" style="background:${k.color}"><i class="fas ${k.icon}"></i></div>
      <div class="sup-kpi-body">
        <span class="sup-kpi-value">${k.value}</span>
        <span class="sup-kpi-label">${k.label}</span>
      </div>
    </div>
  `).join('');
}

function renderSupResumen(filter, search) {
  // Build rows from actual compras + servicios groups
  const rows = [
    ...SUP_COMPRAS.map(g => ({ ...g, _tipo: 'Compra' })),
    ...SUP_SERVICIOS.map(g => ({ ...g, _tipo: 'Servicio' })),
  ];

  let data = rows;
  if (filter !== 'all') data = data.filter(r => r._tipo.toUpperCase() === filter);
  if (search) {
    const q = search.toLowerCase();
    data = data.filter(r => (r.nombre || '').toLowerCase().includes(q));
  }

  const tbody = document.getElementById('sup-resumen-tbody');
  if (!data.length) {
    tbody.innerHTML = `<tr><td colspan="7"><div class="sup-empty"><i class="fas fa-inbox"></i><p>Sin grupos creados aún</p></div></td></tr>`;
    return;
  }

  tbody.innerHTML = data.map(g => {
    const items = g.items || [];
    const total = items.length;
    const aprobados = items.filter(i => (i.status_compra || '').toUpperCase() === 'APROBADO').length;
    const pendientes = items.filter(i => (i.status_compra || '').toUpperCase() === 'PENDIENTE').length;
    const avgAvance = total ? Math.round(items.reduce((a, i) => a + (i.avance || 0), 0) / total) : 0;
    const pctClass = avgAvance >= 80 ? 'sup-prog-high' : avgAvance >= 40 ? 'sup-prog-mid' : 'sup-prog-low';
    const tipoClass = g._tipo === 'Compra' ? 'sup-tipo-compra' : 'sup-tipo-servicio';
    // find nearest fecha_limite among items
    const fechas = items.map(i => i.fecha_limite).filter(Boolean).sort();
    const fechaProxima = fechas[0] || '–';
    return `
      <tr>
        <td><span class="sup-badge ${tipoClass}">${g._tipo}</span></td>
        <td class="rubro-cell" style="font-weight:600">${escapeHtml(g.nombre)}</td>
        <td style="text-align:center">${total}</td>
        <td style="text-align:center">${aprobados > 0 ? `<span style="color:#34d399;font-weight:600">${aprobados}</span>` : '–'}</td>
        <td style="text-align:center">${pendientes > 0 ? `<span style="color:#f87171;font-weight:600">${pendientes}</span>` : '–'}</td>
        <td class="date-cell">${fechaProxima}</td>
        <td>
          <div style="display:flex;align-items:center;gap:8px">
            <div class="sup-avance-bar" style="flex:1;min-width:80px"><div class="sup-avance-fill ${pctClass}" style="width:${avgAvance}%"></div></div>
            <span class="sup-avance-text">${avgAvance}%</span>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

function renderSupCompras(filter, search) {
  const container = document.getElementById('sup-compras-list');
  let html = '';

  SUP_COMPRAS.forEach(group => {
    let items = group.items || [];
    if (filter !== 'all') items = items.filter(i => (i.status_compra || '').toUpperCase() === filter);
    if (search) {
      const q = search.toLowerCase();
      items = items.filter(i =>
        (i.actividad || '').toLowerCase().includes(q) ||
        (i.proveedor || '').toLowerCase().includes(q) ||
        (i.observaciones || '').toLowerCase().includes(q)
      );
    }

    const allGroupItems = group.items || [];
    const groupAvg = allGroupItems.length ? Math.round(allGroupItems.reduce((a, i) => a + (i.avance || 0), 0) / allGroupItems.length) : 0;
    const groupAprobados = allGroupItems.filter(i => (i.status_compra || '').toUpperCase() === 'APROBADO').length;
    const groupPendientes = allGroupItems.filter(i => (i.status_compra || '').toUpperCase() === 'PENDIENTE').length;
    const gAvColor = groupAvg >= 80 ? '#34d399' : groupAvg >= 40 ? '#fbbf24' : '#f87171';

    html += `
      <div class="sup-group">
        <div class="sup-group-header">
          <span class="sup-group-toggle-area" onclick="supToggleGroup(this.parentElement)" style="display:flex;align-items:center;gap:10px;flex:1;cursor:pointer;">
            <i class="fas fa-chevron-down sup-group-toggle"></i>
            <span class="sup-group-title">${escapeHtml(group.nombre)}</span>
            <span class="sup-group-count">${allGroupItems.length} items</span>
            <div style="display:flex;align-items:center;gap:6px;margin-left:8px">
              <div style="width:90px;height:6px;border-radius:4px;background:rgba(255,255,255,0.1);overflow:hidden">
                <div style="height:100%;width:${groupAvg}%;background:${gAvColor};border-radius:4px;transition:width .4s"></div>
              </div>
              <span style="font-size:11px;font-weight:700;color:${gAvColor}">${groupAvg}%</span>
            </div>
            ${groupAprobados > 0 ? `<span style="font-size:10.5px;color:#34d399"><i class="fas fa-check-circle"></i> ${groupAprobados} aprobados</span>` : ''}
            ${groupPendientes > 0 ? `<span style="font-size:10.5px;color:#f87171"><i class="fas fa-clock"></i> ${groupPendientes} pendientes</span>` : ''}
          </span>
          <div class="sup-group-actions">
            <button class="btn-icon btn-icon-sm" title="Agregar item" onclick="event.stopPropagation();openSupComprasItemModal(${group.id})"><i class="fas fa-plus"></i></button>
            <button class="btn-icon btn-icon-sm" title="Editar grupo" onclick="event.stopPropagation();openSupComprasGrupoModal(${group.id}, ${JSON.stringify(group.nombre)})"><i class="fas fa-pen"></i></button>
            <button class="btn-icon btn-icon-sm btn-icon-danger" title="Eliminar grupo" onclick="event.stopPropagation();deleteSupComprasGrupo(${group.id})"><i class="fas fa-trash"></i></button>
          </div>
        </div>
        <div class="sup-group-body">
          ${items.length ? `
          <table class="sup-detail-table sup-compras-table">
            <thead>
              <tr>
                <th>Prior.</th>
                <th>Actividad</th>
                <th>Categoría</th>
                <th>Proveedor</th>
                <th title="Procura" class="sup-check-th">PR</th>
                <th title="Contratado" class="sup-check-th">CT</th>
                <th title="Fabricado" class="sup-check-th">FB</th>
                <th title="Despacho" class="sup-check-th">DS</th>
                <th title="Recepción" class="sup-check-th">RC</th>
                <th>Status</th>
                <th>F. Llegada</th>
                <th>F. Límite</th>
                <th>Prod./Envío</th>
                <th title="Días instalación">Días inst.</th>
                <th>Programación</th>
                <th>Observaciones</th>
                <th>Avance</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              ${items.map(i => {
                const avance = i.avance ?? 0;
                const catClass = (i.categoria || '').toUpperCase() === 'IMPORTADO' ? 'sup-cat-importado' : (i.categoria || '').toUpperCase() === 'NACIONAL' ? 'sup-cat-nacional' : '';
                return `
                <tr>
                  <td><span class="priority-dot-cell ${supPriorityClass(i.prioridad)}">${i.prioridad ?? '–'}</span></td>
                  <td class="act-cell">${escapeHtml(i.actividad || '')}${(i.extra_grupo_ids && i.extra_grupo_ids.length > 0) ? ` <span class="sup-badge" style="background:rgba(99,102,241,.25);color:#a5b4fc;font-size:9px" title="Vinculado a ${i.extra_grupo_ids.length} grupo(s) adicional(es)"><i class="fas fa-link"></i> +${i.extra_grupo_ids.length}</span>` : ''}${i.avance_proyecto > 0 ? ` <span class="sup-badge" style="background:rgba(251,191,36,.15);color:#fbbf24;font-size:9px" title="Avance proyecto: ${i.avance_proyecto}%"><i class="fas fa-tasks"></i> ${i.avance_proyecto}%</span>` : ''}</td>
                  <td>${i.categoria ? `<span class="sup-badge ${catClass}">${escapeHtml(i.categoria)}</span>` : '–'}</td>
                  <td class="sup-prov-cell">${escapeHtml(i.proveedor || '–')}</td>
                  <td class="sup-check-cell">${supCheckCell(i.procura, i.id, 'procura')}</td>
                  <td class="sup-check-cell">${supCheckCell(i.contratado, i.id, 'contratado')}</td>
                  <td class="sup-check-cell">${supCheckCell(i.fabricado, i.id, 'fabricado')}</td>
                  <td class="sup-check-cell">${supCheckCell(i.despacho, i.id, 'despacho')}</td>
                  <td class="sup-check-cell">${supCheckCell(i.recepcion, i.id, 'recepcion')}</td>
                  <td>${i.status_compra ? `<span class="sup-badge ${supStatusCompraClass(i.status_compra)}">${escapeHtml(i.status_compra)}</span>` : '–'}</td>
                  <td class="date-cell">${i.fecha_llegada || '–'}</td>
                  <td class="date-cell">${i.fecha_limite || '–'}</td>
                  <td class="sup-prov-cell">${escapeHtml(i.tiempo_prod || '–')}</td>
                  <td style="text-align:center">${supDiasHtml(i.inicio_project)}</td>
                  <td>${i.programacion ? `<span class="sup-badge ${supProgramacionClass(i.programacion)}">${escapeHtml(i.programacion)}</span>` : '–'}</td>
                  <td class="sup-obs-cell" title="${escapeHtml(i.observaciones || '')}">${escapeHtml((i.observaciones || '').slice(0, 55))}${(i.observaciones || '').length > 55 ? '…' : ''}</td>
                  <td class="sup-avance-cell">
                    <div class="sup-avance-bar"><div class="sup-avance-fill" style="width:${avance}%"></div></div>
                    <span class="sup-avance-text">${avance}%</span>
                  </td>
                  <td class="sup-row-actions">
                    <button class="btn-icon btn-icon-sm" title="Editar" onclick="openSupComprasItemModal(${group.id}, ${i.id})"><i class="fas fa-pen"></i></button>
                    <button class="btn-icon btn-icon-sm btn-icon-danger" title="Eliminar" onclick="deleteSupComprasItem(${i.id})"><i class="fas fa-trash"></i></button>
                  </td>
                </tr>
              `;}).join('')}
            </tbody>
          </table>` : `<div class="sup-empty" style="padding:24px;text-align:center;color:var(--text-muted)"><i class="fas fa-inbox"></i> Sin items en este grupo</div>`}
        </div>
      </div>
    `;
  });

  if (!html) {
    html = `<div class="sup-empty glass-card" style="padding:60px"><i class="fas fa-box-open"></i><p>Aún no hay grupos. Crea uno con el botón <strong>Nuevo grupo</strong>.</p></div>`;
  }
  container.innerHTML = html;
}

function supCheckCell(checked, itemId, field) {
  return `<button type="button" class="sup-check-toggle ${checked ? 'is-on' : ''}" onclick="toggleSupComprasCheck(${itemId}, '${field}', ${!checked})" title="${field}">${checked ? '<i class="fas fa-check"></i>' : ''}</button>`;
}

function supDiasParaInstalacion(fechaStr) {
  if (!fechaStr) return null;
  const hoy = new Date(); hoy.setHours(0, 0, 0, 0);
  const inicio = new Date(fechaStr);
  if (isNaN(inicio)) return null;
  return Math.ceil((inicio - hoy) / (1000 * 60 * 60 * 24));
}

function supDiasHtml(fechaStr) {
  const d = supDiasParaInstalacion(fechaStr);
  if (d === null) return '–';
  if (d > 0) return `<span class="dias-inst-badge dias-inst-ok">${d} d</span>`;
  if (d === 0) return `<span class="dias-inst-badge dias-inst-hoy">Hoy</span>`;
  return `<span class="dias-inst-badge dias-inst-vencido">${d} d</span>`;
}

function supStatusCompraClass(s) {
  const v = (s || '').toUpperCase();
  if (v === 'APROBADO') return 'sup-status-aprobado';
  if (v === 'PENDIENTE') return 'sup-status-pendiente';
  if (v.startsWith('EN REVIS')) return 'sup-status-revision';
  if (v === 'RECHAZADO') return 'sup-status-rechazado';
  return 'sup-status-default';
}

function supProgramacionClass(p) {
  const v = (p || '').toUpperCase();
  if (v.startsWith('PROCURA')) return 'sup-prog-procura';
  if (v.startsWith('CONTRAT')) return 'sup-prog-contratacion';
  if (v.startsWith('FABRIC')) return 'sup-prog-fabricacion';
  if (v.startsWith('TRANS')) return 'sup-prog-transito';
  if (v.startsWith('RECEP')) return 'sup-prog-recepcion';
  if (v.startsWith('INSTAL')) return 'sup-prog-instalacion';
  if (v === 'FINALIZADO') return 'sup-prog-finalizado';
  return 'sup-prog-default';
}

async function toggleSupComprasCheck(itemId, field, newValue) {
  try {
    await apiRequest(`/api/supervision/compras/item/${itemId}`, {
      method: 'PUT',
      body: JSON.stringify({ [field]: newValue })
    });
    await supLoadProject(supCurrentProject);
  } catch (err) {
    showToast(err.message || 'Error al actualizar', 'error');
  }
}

function supServiciosStatusClass(s) {
  const v = (s || '').toUpperCase();
  if (v === 'APROBADO') return 'sup-status-aprobado';
  if (v === 'CONTRATADO') return 'sup-status-aprobado';
  if (v === 'POR COTIZAR') return 'sup-status-pendiente';
  return 'sup-status-default';
}

function supServCheckCell(checked, itemId, field) {
  return `<button type="button" class="sup-check-toggle ${checked ? 'is-on' : ''}" onclick="toggleSupServiciosCheck(${itemId}, '${field}', ${!checked})" title="${field}">${checked ? '<i class="fas fa-check"></i>' : ''}</button>`;
}

async function toggleSupServiciosCheck(itemId, field, newValue) {
  try {
    await apiRequest(`/api/supervision/servicios/item/${itemId}`, { method: 'PUT', body: JSON.stringify({ [field]: newValue }) });
    await supLoadProject(supCurrentProject);
  } catch (err) {
    showToast('Error al actualizar', 'error');
  }
}

function renderSupServicios(filter, search) {
  const container = document.getElementById('sup-servicios-list');
  let html = '';

  SUP_SERVICIOS.forEach(group => {
    let items = group.items || [];
    if (filter !== 'all') items = items.filter(i => (i.status || '').toUpperCase() === filter);
    if (search) {
      const q = search.toLowerCase();
      items = items.filter(i =>
        (i.actividad || '').toLowerCase().includes(q) ||
        (i.proveedor || '').toLowerCase().includes(q) ||
        (i.observaciones || '').toLowerCase().includes(q)
      );
    }

    const allGroupItems = group.items || [];
    const groupAvg = allGroupItems.length ? Math.round(allGroupItems.reduce((a, i) => a + (i.avance || 0), 0) / allGroupItems.length) : 0;
    const groupAprobados = allGroupItems.filter(i => ['APROBADO','CONTRATADO'].includes((i.status || '').toUpperCase())).length;
    const groupPendientes = allGroupItems.filter(i => (i.status || '').toUpperCase() === 'POR COTIZAR').length;
    const gAvColor = groupAvg >= 80 ? '#34d399' : groupAvg >= 40 ? '#fbbf24' : '#f87171';

    html += `
      <div class="sup-group">
        <div class="sup-group-header">
          <span class="sup-group-toggle-area" onclick="supToggleGroup(this.parentElement)" style="display:flex;align-items:center;gap:10px;flex:1;cursor:pointer;">
            <i class="fas fa-chevron-down sup-group-toggle"></i>
            <span class="sup-group-title">${escapeHtml(group.nombre)}</span>
            <span class="sup-group-count">${allGroupItems.length} items</span>
            <div style="display:flex;align-items:center;gap:6px;margin-left:8px">
              <div style="width:90px;height:6px;border-radius:4px;background:rgba(255,255,255,0.1);overflow:hidden">
                <div style="height:100%;width:${groupAvg}%;background:${gAvColor};border-radius:4px;transition:width .4s"></div>
              </div>
              <span style="font-size:11px;font-weight:700;color:${gAvColor}">${groupAvg}%</span>
            </div>
            ${groupAprobados > 0 ? `<span style="font-size:10.5px;color:#34d399"><i class="fas fa-check-circle"></i> ${groupAprobados} contratados</span>` : ''}
            ${groupPendientes > 0 ? `<span style="font-size:10.5px;color:#f87171"><i class="fas fa-clock"></i> ${groupPendientes} por cotizar</span>` : ''}
          </span>
          <div class="sup-group-actions">
            <button class="btn-icon btn-icon-sm" title="Agregar item" onclick="event.stopPropagation();openSupServiciosItemModal(${group.id})"><i class="fas fa-plus"></i></button>
            <button class="btn-icon btn-icon-sm" title="Editar grupo" onclick="event.stopPropagation();openSupServiciosGrupoModal(${group.id}, ${JSON.stringify(group.nombre)})"><i class="fas fa-pen"></i></button>
            <button class="btn-icon btn-icon-sm btn-icon-danger" title="Eliminar grupo" onclick="event.stopPropagation();deleteSupServiciosGrupo(${group.id})"><i class="fas fa-trash"></i></button>
          </div>
        </div>
        <div class="sup-group-body">
          ${items.length ? `
          <table class="sup-detail-table sup-compras-table">
            <thead>
              <tr>
                <th>Prior.</th>
                <th>Actividad</th>
                <th>Proveedor</th>
                <th title="Solicitud" class="sup-check-th">SL</th>
                <th title="Contratado" class="sup-check-th">CT</th>
                <th title="Fabricado" class="sup-check-th">FB</th>
                <th title="Instalado" class="sup-check-th">IN</th>
                <th>Status</th>
                <th>F. Límite</th>
                <th>Prod./Servicio</th>
                <th title="Días para instalación">Días inst.</th>
                <th>Presup. ODC</th>
                <th>Por contratar</th>
                <th>Observaciones</th>
                <th>Avance</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              ${items.map(i => {
                const avance = i.avance ?? 0;
                return `
                <tr>
                  <td><span class="priority-dot-cell ${supPriorityClass(i.prioridad)}">${i.prioridad ?? '–'}</span></td>
                  <td class="act-cell">${escapeHtml(i.actividad || '')}${(i.extra_grupo_ids && i.extra_grupo_ids.length > 0) ? ` <span class="sup-badge" style="background:rgba(99,102,241,.25);color:#a5b4fc;font-size:9px" title="Vinculado a ${i.extra_grupo_ids.length} grupo(s) adicional(es)"><i class="fas fa-link"></i> +${i.extra_grupo_ids.length}</span>` : ''}${i.avance_proyecto > 0 ? ` <span class="sup-badge" style="background:rgba(251,191,36,.15);color:#fbbf24;font-size:9px" title="Avance proyecto: ${i.avance_proyecto}%"><i class="fas fa-tasks"></i> ${i.avance_proyecto}%</span>` : ''}</td>
                  <td class="sup-prov-cell">${escapeHtml(i.proveedor || '–')}</td>
                  <td class="sup-check-cell">${supServCheckCell(i.solicitud, i.id, 'solicitud')}</td>
                  <td class="sup-check-cell">${supServCheckCell(i.contratado, i.id, 'contratado')}</td>
                  <td class="sup-check-cell">${supServCheckCell(i.fabricado, i.id, 'fabricado')}</td>
                  <td class="sup-check-cell">${supServCheckCell(i.instalado, i.id, 'instalado')}</td>
                  <td>${i.status ? `<span class="sup-badge ${supServiciosStatusClass(i.status)}">${escapeHtml(i.status)}</span>` : '–'}</td>
                  <td class="date-cell">${i.fecha_limite || '–'}</td>
                  <td class="sup-prov-cell">${escapeHtml(i.tiempo_prod || '–')}</td>
                  <td style="text-align:center">${supDiasHtml(i.inicio_project)}</td>
                  <td style="text-align:right">${i.presupuesto_odc != null ? '$' + Number(i.presupuesto_odc).toLocaleString('es', {minimumFractionDigits:2}) : '–'}</td>
                  <td style="text-align:right">${i.por_contratar != null ? '$' + Number(i.por_contratar).toLocaleString('es', {minimumFractionDigits:2}) : '–'}</td>
                  <td class="sup-obs-cell" title="${escapeHtml(i.observaciones || '')}">${escapeHtml((i.observaciones || '').slice(0, 55))}${(i.observaciones || '').length > 55 ? '…' : ''}</td>
                  <td class="sup-avance-cell">
                    <div class="sup-avance-bar"><div class="sup-avance-fill" style="width:${avance}%"></div></div>
                    <span class="sup-avance-text">${avance}%</span>
                  </td>
                  <td class="sup-row-actions">
                    <button class="btn-icon btn-icon-sm" title="Editar" onclick="openSupServiciosItemModal(${group.id}, ${i.id})"><i class="fas fa-pen"></i></button>
                    <button class="btn-icon btn-icon-sm btn-icon-danger" title="Eliminar" onclick="deleteSupServiciosItem(${i.id})"><i class="fas fa-trash"></i></button>
                  </td>
                </tr>
              `}).join('')}
            </tbody>
          </table>` : `<div class="sup-empty" style="padding:24px;text-align:center;color:var(--text-muted)"><i class="fas fa-inbox"></i> Sin items en este grupo</div>`}
        </div>
      </div>
    `;
  });

  if (!html) {
    html = `<div class="sup-empty glass-card" style="padding:60px"><i class="fas fa-handshake"></i><p>Aún no hay grupos. Crea uno con el botón <strong>Nuevo grupo</strong>.</p></div>`;
  }
  container.innerHTML = html;
}

function supToggleGroup(header) {
  header.classList.toggle('collapsed');
  const body = header.nextElementSibling;
  body.classList.toggle('collapsed');
}

// ===================== SUPERVISIÓN - CRUD COMPRAS / SERVICIOS =====================
function escapeHtml(str) {
  if (str === null || str === undefined) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

let _supModalsInited = false;
function initSupModals() {
  if (_supModalsInited) return;
  _supModalsInited = true;

  document.getElementById('sup-compras-grupo-form').addEventListener('submit', submitSupComprasGrupo);
  document.getElementById('sup-compras-item-form').addEventListener('submit', submitSupComprasItem);
  document.getElementById('sup-servicios-grupo-form').addEventListener('submit', submitSupServiciosGrupo);
  document.getElementById('sup-servicios-item-form').addEventListener('submit', submitSupServiciosItem);
}

function _ensureSupProject() {
  if (!supCurrentProject) {
    showToast('Selecciona un proyecto primero', 'warning');
    return false;
  }
  return true;
}

// ---------- COMPRAS: GRUPO ----------
function openSupComprasGrupoModal(grupoId = null, nombre = '') {
  if (!_ensureSupProject()) return;
  document.getElementById('sup-compras-grupo-id').value = grupoId || '';
  document.getElementById('sup-compras-grupo-nombre').value = nombre || '';
  document.getElementById('sup-compras-grupo-title').innerHTML = grupoId
    ? '<i class="fas fa-pen"></i> Editar grupo de compras'
    : '<i class="fas fa-folder-plus"></i> Nuevo grupo de compras';
  openModal('sup-compras-grupo-modal');
}

async function submitSupComprasGrupo(e) {
  e.preventDefault();
  const id = document.getElementById('sup-compras-grupo-id').value;
  const nombre = document.getElementById('sup-compras-grupo-nombre').value.trim();
  if (!nombre) return;
  try {
    if (id) {
      await apiRequest(`/api/supervision/compras/grupo/${id}`, { method: 'PUT', body: JSON.stringify({ nombre }) });
      showToast('Grupo actualizado', 'success');
    } else {
      await apiRequest(`/api/supervision/${supCurrentProject}/compras/grupo`, { method: 'POST', body: JSON.stringify({ nombre }) });
      showToast('Grupo creado', 'success');
    }
    closeModal('sup-compras-grupo-modal');
    await supLoadProject(supCurrentProject);
  } catch (err) {
    showToast(err.message || 'Error al guardar', 'error');
  }
}

async function deleteSupComprasGrupo(grupoId) {
  if (!confirm('¿Eliminar este grupo y todos sus items?')) return;
  try {
    await apiRequest(`/api/supervision/compras/grupo/${grupoId}`, { method: 'DELETE' });
    showToast('Grupo eliminado', 'success');
    await supLoadProject(supCurrentProject);
  } catch (err) {
    showToast(err.message || 'Error al eliminar', 'error');
  }
}

// ---------- COMPRAS: ITEM ----------
function _buildExtraGruposChips(containerId, allGroups, currentGroupId, selectedIds) {
  const container = document.getElementById(containerId);
  if (!container) return;
  // Excluir el grupo primario de la lista de extra grupos
  const otherGroups = allGroups.filter(g => g.id !== parseInt(currentGroupId));
  if (!otherGroups.length) {
    container.innerHTML = '<span style="color:var(--text-muted);font-size:12px">No hay otros grupos disponibles</span>';
    return;
  }
  container.innerHTML = otherGroups.map(g => `
    <div class="assignee-chip ${selectedIds.includes(g.id) ? 'selected' : ''}" data-grupo-id="${g.id}" style="cursor:pointer" onclick="this.classList.toggle('selected')">
      <i class="fas fa-layer-group" style="font-size:10px;opacity:.7"></i>
      <span class="assignee-chip-name">${escapeHtml(g.nombre)}</span>
    </div>
  `).join('');
}

function _getSelectedExtraGrupoIds(containerId) {
  const container = document.getElementById(containerId);
  if (!container) return [];
  return Array.from(container.querySelectorAll('.assignee-chip.selected'))
    .map(c => parseInt(c.dataset.grupoId));
}

function openSupComprasItemModal(grupoId, itemId = null) {
  if (!_ensureSupProject()) return;
  const form = document.getElementById('sup-compras-item-form');
  form.reset();
  document.getElementById('sup-compras-item-id').value = itemId || '';
  document.getElementById('sup-compras-item-grupo-id').value = grupoId;
  document.getElementById('sup-compras-item-avance-proyecto').value = 0;
  document.getElementById('sup-compras-item-avance-proyecto-val').textContent = '0';

  // Poblar selector de tareas del proyecto actual
  const taskSel = document.getElementById('sup-compras-item-task-id');
  taskSel.innerHTML = '<option value="">Sin tarea vinculada</option>';
  (tasks || []).forEach(t => {
    const opt = document.createElement('option');
    opt.value = t.id;
    opt.textContent = `${t.title}${t.progress ? ' (' + t.progress + '%)' : ''}`;
    taskSel.appendChild(opt);
  });
  const apSliderC = document.getElementById('sup-compras-item-avance-proyecto');
  apSliderC.oninput = function() {
    document.getElementById('sup-compras-item-avance-proyecto-val').textContent = this.value;
  };

  function _setComprasSliderEnabled(enabled) {
    apSliderC.disabled = !enabled;
    apSliderC.style.opacity = enabled ? '' : '0.5';
    apSliderC.style.cursor = enabled ? '' : 'not-allowed';
  }

  taskSel.onchange = function() {
    const tid = parseInt(this.value) || 0;
    const t = tid ? tasks.find(x => x.id === tid) : null;
    if (t) {
      const ap = t.progress || 0;
      apSliderC.value = ap;
      document.getElementById('sup-compras-item-avance-proyecto-val').textContent = ap;
      _setComprasSliderEnabled(false);
      document.getElementById('sup-compras-item-avance-hint').textContent = `Avance tomado de la tarea "${t.title}" — solo cambia actualizando la tarea`;
    } else {
      _setComprasSliderEnabled(true);
      document.getElementById('sup-compras-item-avance-hint').textContent = 'Vincula una tarea de proyecto para que el avance se actualice automáticamente';
    }
  };

  let selectedExtraIds = [];
  if (itemId) {
    // Buscar el item en cualquier grupo (puede ser primario o extra)
    let item = null;
    for (const g of SUP_COMPRAS) {
      item = g.items?.find(i => i.id === itemId);
      if (item) break;
    }
    if (item) {
      document.getElementById('sup-compras-item-actividad').value = item.actividad || '';
      document.getElementById('sup-compras-item-prioridad').value = item.prioridad ?? '';
      document.getElementById('sup-compras-item-categoria').value = item.categoria || '';
      document.getElementById('sup-compras-item-proveedor').value = item.proveedor || '';
      document.getElementById('sup-compras-item-status-compra').value = item.status_compra || '';
      document.getElementById('sup-compras-item-fecha-limite').value = item.fecha_limite || '';
      document.getElementById('sup-compras-item-fecha-llegada').value = item.fecha_llegada || '';
      document.getElementById('sup-compras-item-tiempo-prod').value = item.tiempo_prod || '';
      document.getElementById('sup-compras-item-inicio-project').value = item.inicio_project || '';
      document.getElementById('sup-compras-item-programacion').value = item.programacion || '';
      document.getElementById('sup-compras-item-procura').checked = !!item.procura;
      document.getElementById('sup-compras-item-contratado').checked = !!item.contratado;
      document.getElementById('sup-compras-item-fabricado').checked = !!item.fabricado;
      document.getElementById('sup-compras-item-despacho').checked = !!item.despacho;
      document.getElementById('sup-compras-item-recepcion').checked = !!item.recepcion;
      document.getElementById('sup-compras-item-observaciones').value = item.observaciones || '';
      const ap = item.avance_proyecto ?? 0;
      apSliderC.value = ap;
      document.getElementById('sup-compras-item-avance-proyecto-val').textContent = ap;
      // Task vinculada
      if (item.task_id) {
        taskSel.value = item.task_id;
        const linkedTask = tasks.find(t => t.id === item.task_id);
        document.getElementById('sup-compras-item-avance-hint').textContent = linkedTask
          ? `Avance tomado de la tarea "${linkedTask.title}" — solo cambia actualizando la tarea`
          : 'Avance controlado por la tarea vinculada';
        _setComprasSliderEnabled(false);
      } else {
        _setComprasSliderEnabled(true);
      }
      selectedExtraIds = item.extra_grupo_ids || [];
    }
    document.getElementById('sup-compras-item-title').innerHTML = '<i class="fas fa-pen"></i> Editar compra / importación';
  } else {
    // Nuevo item: habilitar slider de avance (sin tarea vinculada)
    _setComprasSliderEnabled(true);
    document.getElementById('sup-compras-item-title').innerHTML = '<i class="fas fa-box"></i> Nueva compra / importación';
  }
  _buildExtraGruposChips('sup-compras-item-extra-grupos', SUP_COMPRAS, grupoId, selectedExtraIds);
  openModal('sup-compras-item-modal');
}

async function submitSupComprasItem(e) {
  e.preventDefault();
  const id = document.getElementById('sup-compras-item-id').value;
  const grupoId = document.getElementById('sup-compras-item-grupo-id').value;
  const extraGrupoIds = _getSelectedExtraGrupoIds('sup-compras-item-extra-grupos');
  const taskIdRaw = document.getElementById('sup-compras-item-task-id').value;
  const taskId = taskIdRaw ? parseInt(taskIdRaw) : (id ? 0 : null); // 0 = desvincular al editar
  const payload = {
    actividad: document.getElementById('sup-compras-item-actividad').value.trim(),
    prioridad: parseInt(document.getElementById('sup-compras-item-prioridad').value) || null,
    categoria: document.getElementById('sup-compras-item-categoria').value || null,
    proveedor: document.getElementById('sup-compras-item-proveedor').value.trim() || null,
    status_compra: document.getElementById('sup-compras-item-status-compra').value || null,
    fecha_limite: document.getElementById('sup-compras-item-fecha-limite').value || null,
    fecha_llegada: document.getElementById('sup-compras-item-fecha-llegada').value || null,
    tiempo_prod: document.getElementById('sup-compras-item-tiempo-prod').value.trim() || null,
    inicio_project: document.getElementById('sup-compras-item-inicio-project').value || null,
    programacion: document.getElementById('sup-compras-item-programacion').value || null,
    procura: document.getElementById('sup-compras-item-procura').checked,
    contratado: document.getElementById('sup-compras-item-contratado').checked,
    fabricado: document.getElementById('sup-compras-item-fabricado').checked,
    despacho: document.getElementById('sup-compras-item-despacho').checked,
    recepcion: document.getElementById('sup-compras-item-recepcion').checked,
    observaciones: document.getElementById('sup-compras-item-observaciones').value.trim() || null,
    extra_grupo_ids: extraGrupoIds,
    task_id: taskId,
  };
  // avance_proyecto solo se envía si NO hay tarea vinculada (de lo contrario el backend lo sincroniza)
  if (!taskIdRaw) {
    payload.avance_proyecto = parseFloat(document.getElementById('sup-compras-item-avance-proyecto').value) || 0;
  }
  if (!payload.actividad) return;
  try {
    if (id) {
      await apiRequest(`/api/supervision/compras/item/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
      showToast('Item actualizado', 'success');
    } else {
      await apiRequest(`/api/supervision/compras/grupo/${grupoId}/item`, { method: 'POST', body: JSON.stringify(payload) });
      showToast('Item creado', 'success');
    }
    closeModal('sup-compras-item-modal');
    await supLoadProject(supCurrentProject);
  } catch (err) {
    showToast(err.message || 'Error al guardar', 'error');
  }
}

async function deleteSupComprasItem(itemId) {
  if (!confirm('¿Eliminar este item?')) return;
  try {
    await apiRequest(`/api/supervision/compras/item/${itemId}`, { method: 'DELETE' });
    showToast('Item eliminado', 'success');
    await supLoadProject(supCurrentProject);
  } catch (err) {
    showToast(err.message || 'Error al eliminar', 'error');
  }
}

// ---------- SERVICIOS: GRUPO ----------
function openSupServiciosGrupoModal(grupoId = null, nombre = '') {
  if (!_ensureSupProject()) return;
  document.getElementById('sup-servicios-grupo-id').value = grupoId || '';
  document.getElementById('sup-servicios-grupo-nombre').value = nombre || '';
  document.getElementById('sup-servicios-grupo-title').innerHTML = grupoId
    ? '<i class="fas fa-pen"></i> Editar grupo de servicios'
    : '<i class="fas fa-folder-plus"></i> Nuevo grupo de servicios';
  openModal('sup-servicios-grupo-modal');
}

async function submitSupServiciosGrupo(e) {
  e.preventDefault();
  const id = document.getElementById('sup-servicios-grupo-id').value;
  const nombre = document.getElementById('sup-servicios-grupo-nombre').value.trim();
  if (!nombre) return;
  try {
    if (id) {
      await apiRequest(`/api/supervision/servicios/grupo/${id}`, { method: 'PUT', body: JSON.stringify({ nombre }) });
      showToast('Grupo actualizado', 'success');
    } else {
      await apiRequest(`/api/supervision/${supCurrentProject}/servicios/grupo`, { method: 'POST', body: JSON.stringify({ nombre }) });
      showToast('Grupo creado', 'success');
    }
    closeModal('sup-servicios-grupo-modal');
    await supLoadProject(supCurrentProject);
  } catch (err) {
    showToast(err.message || 'Error al guardar', 'error');
  }
}

async function deleteSupServiciosGrupo(grupoId) {
  if (!confirm('¿Eliminar este grupo y todos sus items?')) return;
  try {
    await apiRequest(`/api/supervision/servicios/grupo/${grupoId}`, { method: 'DELETE' });
    showToast('Grupo eliminado', 'success');
    await supLoadProject(supCurrentProject);
  } catch (err) {
    showToast(err.message || 'Error al eliminar', 'error');
  }
}

// ---------- SERVICIOS: ITEM ----------
function openSupServiciosItemModal(grupoId, itemId = null) {
  if (!_ensureSupProject()) return;
  const form = document.getElementById('sup-servicios-item-form');
  form.reset();
  document.getElementById('sup-servicios-item-id').value = itemId || '';
  document.getElementById('sup-servicios-item-grupo-id').value = grupoId;
  document.getElementById('sup-servicios-item-avance-proyecto').value = 0;
  document.getElementById('sup-servicios-item-avance-proyecto-val').textContent = '0';

  // Poblar selector de tareas del proyecto actual
  const taskSel = document.getElementById('sup-servicios-item-task-id');
  taskSel.innerHTML = '<option value="">Sin tarea vinculada</option>';
  (tasks || []).forEach(t => {
    const opt = document.createElement('option');
    opt.value = t.id;
    opt.textContent = `${t.title}${t.progress ? ' (' + t.progress + '%)' : ''}`;
    taskSel.appendChild(opt);
  });
  const apSliderS = document.getElementById('sup-servicios-item-avance-proyecto');
  apSliderS.oninput = function() {
    document.getElementById('sup-servicios-item-avance-proyecto-val').textContent = this.value;
  };

  function _setServiciosSliderEnabled(enabled) {
    apSliderS.disabled = !enabled;
    apSliderS.style.opacity = enabled ? '' : '0.5';
    apSliderS.style.cursor = enabled ? '' : 'not-allowed';
  }

  taskSel.onchange = function() {
    const tid = parseInt(this.value) || 0;
    const t = tid ? tasks.find(x => x.id === tid) : null;
    if (t) {
      const ap = t.progress || 0;
      apSliderS.value = ap;
      document.getElementById('sup-servicios-item-avance-proyecto-val').textContent = ap;
      _setServiciosSliderEnabled(false);
      document.getElementById('sup-servicios-item-avance-hint').textContent = `Avance tomado de la tarea "${t.title}" — solo cambia actualizando la tarea`;
    } else {
      _setServiciosSliderEnabled(true);
      document.getElementById('sup-servicios-item-avance-hint').textContent = 'Vincula una tarea de proyecto para que el avance se actualice automáticamente';
    }
  };

  let selectedExtraIds = [];
  if (itemId) {
    let item = null;
    for (const g of SUP_SERVICIOS) {
      item = g.items?.find(i => i.id === itemId);
      if (item) break;
    }
    if (item) {
      document.getElementById('sup-servicios-item-actividad').value = item.actividad || '';
      document.getElementById('sup-servicios-item-prioridad').value = item.prioridad ?? '';
      document.getElementById('sup-servicios-item-status').value = item.status || '';
      document.getElementById('sup-servicios-item-proveedor').value = item.proveedor || '';
      document.getElementById('sup-servicios-item-tiempo-prod').value = item.tiempo_prod || '';
      document.getElementById('sup-servicios-item-fecha-limite').value = item.fecha_limite || '';
      document.getElementById('sup-servicios-item-inicio-project').value = item.inicio_project || '';
      document.getElementById('sup-servicios-item-presupuesto-odc').value = item.presupuesto_odc ?? '';
      document.getElementById('sup-servicios-item-por-contratar').value = item.por_contratar ?? '';
      document.getElementById('sup-servicios-item-solicitud').checked = !!item.solicitud;
      document.getElementById('sup-servicios-item-contratado').checked = !!item.contratado;
      document.getElementById('sup-servicios-item-fabricado').checked = !!item.fabricado;
      document.getElementById('sup-servicios-item-instalado').checked = !!item.instalado;
      document.getElementById('sup-servicios-item-observaciones').value = item.observaciones || '';
      const ap = item.avance_proyecto ?? 0;
      apSliderS.value = ap;
      document.getElementById('sup-servicios-item-avance-proyecto-val').textContent = ap;
      // Task vinculada
      if (item.task_id) {
        taskSel.value = item.task_id;
        const linkedTask = tasks.find(t => t.id === item.task_id);
        document.getElementById('sup-servicios-item-avance-hint').textContent = linkedTask
          ? `Avance tomado de la tarea "${linkedTask.title}" — solo cambia actualizando la tarea`
          : 'Avance controlado por la tarea vinculada';
        _setServiciosSliderEnabled(false);
      } else {
        _setServiciosSliderEnabled(true);
      }
      selectedExtraIds = item.extra_grupo_ids || [];
    }
    document.getElementById('sup-servicios-item-title').innerHTML = '<i class="fas fa-pen"></i> Editar contratación de servicio';
  } else {
    // Nuevo item: habilitar slider de avance (sin tarea vinculada)
    _setServiciosSliderEnabled(true);
    document.getElementById('sup-servicios-item-title').innerHTML = '<i class="fas fa-handshake"></i> Nueva contratación de servicio';
  }
  _buildExtraGruposChips('sup-servicios-item-extra-grupos', SUP_SERVICIOS, grupoId, selectedExtraIds);
  openModal('sup-servicios-item-modal');
}

async function submitSupServiciosItem(e) {
  e.preventDefault();
  const id = document.getElementById('sup-servicios-item-id').value;
  const grupoId = document.getElementById('sup-servicios-item-grupo-id').value;
  const extraGrupoIds = _getSelectedExtraGrupoIds('sup-servicios-item-extra-grupos');
  const taskIdRaw = document.getElementById('sup-servicios-item-task-id').value;
  const taskId = taskIdRaw ? parseInt(taskIdRaw) : (id ? 0 : null); // 0 = desvincular al editar
  const payload = {
    actividad: document.getElementById('sup-servicios-item-actividad').value.trim(),
    prioridad: parseInt(document.getElementById('sup-servicios-item-prioridad').value) || null,
    status: document.getElementById('sup-servicios-item-status').value || null,
    proveedor: document.getElementById('sup-servicios-item-proveedor').value.trim() || null,
    tiempo_prod: document.getElementById('sup-servicios-item-tiempo-prod').value.trim() || null,
    fecha_limite: document.getElementById('sup-servicios-item-fecha-limite').value || null,
    inicio_project: document.getElementById('sup-servicios-item-inicio-project').value || null,
    presupuesto_odc: parseFloat(document.getElementById('sup-servicios-item-presupuesto-odc').value) || null,
    por_contratar: parseFloat(document.getElementById('sup-servicios-item-por-contratar').value) || null,
    solicitud: document.getElementById('sup-servicios-item-solicitud').checked,
    contratado: document.getElementById('sup-servicios-item-contratado').checked,
    fabricado: document.getElementById('sup-servicios-item-fabricado').checked,
    instalado: document.getElementById('sup-servicios-item-instalado').checked,
    observaciones: document.getElementById('sup-servicios-item-observaciones').value.trim() || null,
    extra_grupo_ids: extraGrupoIds,
    task_id: taskId,
  };
  // avance_proyecto solo se envía si NO hay tarea vinculada
  if (!taskIdRaw) {
    payload.avance_proyecto = parseFloat(document.getElementById('sup-servicios-item-avance-proyecto').value) || 0;
  }
  if (!payload.actividad) return;
  try {
    if (id) {
      await apiRequest(`/api/supervision/servicios/item/${id}`, { method: 'PUT', body: JSON.stringify(payload) });
      showToast('Item actualizado', 'success');
    } else {
      await apiRequest(`/api/supervision/servicios/grupo/${grupoId}/item`, { method: 'POST', body: JSON.stringify(payload) });
      showToast('Item creado', 'success');
    }
    closeModal('sup-servicios-item-modal');
    await supLoadProject(supCurrentProject);
  } catch (err) {
    showToast(err.message || 'Error al guardar', 'error');
  }
}

async function deleteSupServiciosItem(itemId) {
  if (!confirm('¿Eliminar este item?')) return;
  try {
    await apiRequest(`/api/supervision/servicios/item/${itemId}`, { method: 'DELETE' });
    showToast('Item eliminado', 'success');
    await supLoadProject(supCurrentProject);
  } catch (err) {
    showToast(err.message || 'Error al eliminar', 'error');
  }
}
