/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, useState, onWillStart, onMounted } from "@odoo/owl";

/**
 * Cash Register Dashboard Widget
 * Widget personalizado para mostrar estadísticas del cierre de caja
 */
export class CashRegisterDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            isLoading: true,
            todayCloses: 0,
            pendingCloses: 0,
            totalBalance: 0,
            totalDifference: 0,
            historicalData: [],
            cashAccounts: [],
        });

        onWillStart(async () => {
            await this.loadDashboardData();
        });

        onMounted(() => {
            this.animateNumbers();
        });
    }

    async loadDashboardData() {
        try {
            // Cargar datos de cierres de hoy
            const today = new Date().toISOString().split('T')[0];
            
            const todayCloses = await this.orm.searchCount("cash.register.close", [
                ["date", "=", today]
            ]);
            
            const pendingCloses = await this.orm.searchCount("cash.register.close", [
                ["state", "in", ["draft", "in_progress"]]
            ]);

            // Cargar totales
            const closedToday = await this.orm.searchRead(
                "cash.register.close",
                [["date", "=", today], ["state", "=", "closed"]],
                ["total_final_balance", "total_difference"]
            );

            let totalBalance = 0;
            let totalDifference = 0;
            closedToday.forEach(close => {
                totalBalance += close.total_final_balance || 0;
                totalDifference += close.total_difference || 0;
            });

            // Cargar datos históricos
            const historicalData = await this.orm.call(
                "cash.register.close",
                "get_historical_balances",
                [],
                { days: 7 }
            );

            // Cargar cuentas de efectivo
            const cashAccounts = await this.orm.searchRead(
                "account.account",
                [["is_cash_account", "=", true]],
                ["name", "code", "currency_id"]
            );

            this.state.todayCloses = todayCloses;
            this.state.pendingCloses = pendingCloses;
            this.state.totalBalance = totalBalance;
            this.state.totalDifference = totalDifference;
            this.state.historicalData = historicalData;
            this.state.cashAccounts = cashAccounts;
            this.state.isLoading = false;

        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.notification.add("Error al cargar datos del dashboard", {
                type: "danger",
            });
            this.state.isLoading = false;
        }
    }

    animateNumbers() {
        // Animación de conteo para los números
        const elements = document.querySelectorAll('.cash-animate-number');
        elements.forEach(el => {
            const target = parseFloat(el.dataset.target) || 0;
            const duration = 1000;
            const start = 0;
            const startTime = performance.now();

            const animate = (currentTime) => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                // Easing function
                const easeOutQuart = 1 - Math.pow(1 - progress, 4);
                const current = start + (target - start) * easeOutQuart;
                
                el.textContent = this.formatNumber(current);
                
                if (progress < 1) {
                    requestAnimationFrame(animate);
                }
            };

            requestAnimationFrame(animate);
        });
    }

    formatNumber(num) {
        return new Intl.NumberFormat('es-ES', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(num);
    }

    formatCurrency(amount, symbol = '$') {
        return `${symbol}${this.formatNumber(amount)}`;
    }

    async openNewClose() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cash.register.close",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
        });
    }

    async openMassClose() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cash.register.close.wizard",
            view_mode: "form",
            views: [[false, "form"]],
            target: "new",
        });
    }

    async openPendingCloses() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cash.register.close",
            view_mode: "tree,form",
            views: [[false, "tree"], [false, "form"]],
            domain: [["state", "in", ["draft", "in_progress"]]],
            target: "current",
            name: "Cierres Pendientes",
        });
    }

    async openTodayCloses() {
        const today = new Date().toISOString().split('T')[0];
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cash.register.close",
            view_mode: "tree,form",
            views: [[false, "tree"], [false, "form"]],
            domain: [["date", "=", today]],
            target: "current",
            name: "Cierres de Hoy",
        });
    }

    getDifferenceClass(difference) {
        if (difference < 0) return 'text-danger';
        if (difference > 0) return 'text-warning';
        return 'text-success';
    }

    getDifferenceIcon(difference) {
        if (difference < 0) return 'fa-arrow-down';
        if (difference > 0) return 'fa-arrow-up';
        return 'fa-check';
    }
}

CashRegisterDashboard.template = "cash_register_close.CashRegisterDashboard";

// Registrar el componente
registry.category("actions").add("cash_register_dashboard", CashRegisterDashboard);


/**
 * Cash Denomination Counter Widget
 * Widget para el conteo rápido de denominaciones
 */
export class CashDenominationCounter extends Component {
    setup() {
        this.state = useState({
            denominations: [],
            total: 0,
        });
    }

    updateQuantity(index, delta) {
        const current = this.state.denominations[index].quantity || 0;
        const newValue = Math.max(0, current + delta);
        this.state.denominations[index].quantity = newValue;
        this.calculateTotal();
    }

    setQuantity(index, value) {
        this.state.denominations[index].quantity = Math.max(0, parseInt(value) || 0);
        this.calculateTotal();
    }

    calculateTotal() {
        this.state.total = this.state.denominations.reduce((sum, d) => {
            return sum + (d.value * (d.quantity || 0));
        }, 0);
        
        // Emitir evento para actualizar el campo
        this.trigger('total-changed', { total: this.state.total });
    }

    formatCurrency(amount) {
        return new Intl.NumberFormat('es-ES', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    }
}

CashDenominationCounter.template = "cash_register_close.CashDenominationCounter";


/**
 * Quick Actions para el Cierre de Caja
 * Acciones rápidas en el dashboard
 */
export class CashRegisterQuickActions extends Component {
    setup() {
        this.action = useService("action");
        this.notification = useService("notification");
    }

    async quickClose() {
        try {
            await this.action.doAction("cash_register_close.action_cash_register_close_wizard");
            this.notification.add("Wizard de cierre masivo abierto", {
                type: "info",
            });
        } catch (error) {
            this.notification.add("Error al abrir el wizard", {
                type: "danger",
            });
        }
    }

    async viewReports() {
        await this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "cash.register.close",
            view_mode: "pivot,graph",
            views: [[false, "pivot"], [false, "graph"]],
            target: "current",
            name: "Análisis de Cierres",
        });
    }

    async configDenominations() {
        await this.action.doAction("cash_register_close.action_cash_denomination");
    }
}

CashRegisterQuickActions.template = "cash_register_close.CashRegisterQuickActions";


/**
 * Utilidades para formateo y cálculos
 */
export const CashRegisterUtils = {
    /**
     * Formatea un número como moneda
     */
    formatCurrency(amount, currency = 'USD', locale = 'es-ES') {
        return new Intl.NumberFormat(locale, {
            style: 'currency',
            currency: currency,
        }).format(amount);
    },

    /**
     * Calcula el total de denominaciones
     */
    calculateDenominationsTotal(denominations) {
        return denominations.reduce((total, denom) => {
            return total + (denom.value * (denom.quantity || 0));
        }, 0);
    },

    /**
     * Obtiene la clase CSS para un valor de diferencia
     */
    getDifferenceClass(difference) {
        if (difference < 0) return 'cash-difference-negative';
        if (difference > 0) return 'cash-difference-positive';
        return 'cash-difference-zero';
    },

    /**
     * Formatea una fecha
     */
    formatDate(date, format = 'long') {
        const options = format === 'long' 
            ? { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }
            : { year: 'numeric', month: '2-digit', day: '2-digit' };
        return new Date(date).toLocaleDateString('es-ES', options);
    },

    /**
     * Genera un color basado en el estado
     */
    getStateColor(state) {
        const colors = {
            'draft': '#6c757d',
            'in_progress': '#ffc107',
            'closed': '#28a745',
            'cancelled': '#dc3545',
        };
        return colors[state] || '#6c757d';
    },

    /**
     * Anima un valor numérico
     */
    animateValue(element, start, end, duration = 1000) {
        const startTime = performance.now();
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            // Easing
            const easeOutQuart = 1 - Math.pow(1 - progress, 4);
            const current = start + (end - start) * easeOutQuart;
            
            element.textContent = this.formatCurrency(current);
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };

        requestAnimationFrame(animate);
    }
};

// Exportar utilidades al objeto window para uso global
window.CashRegisterUtils = CashRegisterUtils;

