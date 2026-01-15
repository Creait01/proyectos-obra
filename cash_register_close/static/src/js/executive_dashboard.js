/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const { Component, useState, onMounted, onWillUnmount, useRef } = owl;

/**
 * Executive Dashboard Component for Cash Register
 * Uses Chart.js for independent visualizations
 */
export class CashRegisterExecutiveDashboard extends Component {
    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        
        this.state = useState({
            loading: true,
            period: 'month', // month, quarter, year
            selectedMonth: new Date().getMonth(),
            selectedYear: new Date().getFullYear(),
            // Período para el gráfico de flujo
            flowPeriod: 'year', // day, month, year
            flowCurrency: 'USD', // USD o EUR
            flowData: [],
            // KPIs del período
            totalIncomeBs: 0,
            totalExpenseBs: 0,
            totalBalanceBs: 0,
            totalIncomeUsd: 0,
            totalExpenseUsd: 0,
            totalBalanceUsd: 0,
            totalIncomeEur: 0,
            totalExpenseEur: 0,
            totalBalanceEur: 0,
            totalCloses: 0,
            closedCount: 0,
            confirmedCount: 0,
            pendingCount: 0,
            companiesCount: 0,
            // Chart data
            monthlyData: [],
            companyData: [],
            // TIEMPO REAL - Saldos actuales de las cuentas
            realtimeBalanceUsd: 0,
            realtimeBalanceEur: 0,
            realtimeBalanceBs: 0,
            realtimeAccountsUsd: [],
            realtimeAccountsEur: [],
            realtimeAccountsBs: [],
            // HOY - Movimientos del día
            todayIncomeUsd: 0,
            todayExpenseUsd: 0,
            todayIncomeEur: 0,
            todayExpenseEur: 0,
            todayIncomeBs: 0,
            todayExpenseBs: 0,
            todayMovementsCount: 0,
            // Billetes en mal estado
            badBillsData: {
                total_count: 0,
                total_value_usd: 0,
                total_value_eur: 0,
                by_condition: [],
                by_denomination: [],
            },
            // Denominaciones actuales
            denominationsData: {
                usd: [],
                eur: [],
                bs: [],
                total_usd: 0,
                total_eur: 0,
                total_bs: 0,
            },
        });

        // Chart references
        this.cashFlowChartRef = useRef("cashFlowChart");
        
        this.charts = {};

        onMounted(() => {
            this.loadChartJS().then(() => {
                this.loadDashboardData();
            });
        });

        onWillUnmount(() => {
            this.destroyCharts();
        });
    }

    async loadChartJS() {
        // Load Chart.js from CDN if not already loaded
        if (typeof Chart === 'undefined') {
            return new Promise((resolve, reject) => {
                const script = document.createElement('script');
                script.src = 'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js';
                script.onload = resolve;
                script.onerror = reject;
                document.head.appendChild(script);
            });
        }
        return Promise.resolve();
    }

    async loadDashboardData() {
        this.state.loading = true;
        try {
            const data = await this.orm.call(
                "cash.register.executive.dashboard",
                "get_dashboard_data",
                [],
                {
                    period: this.state.period,
                    month: this.state.selectedMonth,
                    year: this.state.selectedYear,
                }
            );
            
            // Update state with received data
            Object.assign(this.state, data);
            
            // Cargar datos del flujo según el período seleccionado
            const flowData = await this.orm.call(
                "cash.register.executive.dashboard",
                "get_flow_data",
                [],
                { period: this.state.flowPeriod }
            );
            this.state.flowData = flowData;
            
            this.state.loading = false;
            
            // Render charts after data is loaded - use setTimeout to ensure DOM is ready
            setTimeout(() => {
                this.renderCharts();
            }, 100);
        } catch (error) {
            console.error("Error loading dashboard data:", error);
            this.state.loading = false;
        }
    }

    destroyCharts() {
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
    }

    renderCharts() {
        this.destroyCharts();
        this.renderCashFlowChart();
    }

    renderCashFlowChart() {
        const canvas = this.cashFlowChartRef.el;
        if (!canvas || typeof Chart === 'undefined') return;

        const ctx = canvas.getContext('2d');
        // Usar flowData si existe, sino monthlyData para compatibilidad
        const data = this.state.flowData && this.state.flowData.length > 0 
            ? this.state.flowData 
            : (this.state.monthlyData || []);
        
        const labels = data.map(d => d.label || d.month);
        const incomeData = data.map(d => d.income || 0);
        const expenseData = data.map(d => d.expense || 0);
        const netFlow = data.map((d, i) => (incomeData[i] || 0) - (expenseData[i] || 0));

        // Guardar referencia para usar en callbacks
        const self = this;

        this.charts.cashFlow = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Ingresos',
                        data: incomeData,
                        backgroundColor: 'rgba(16, 185, 129, 0.8)',
                        borderColor: 'rgba(16, 185, 129, 1)',
                        borderWidth: 1,
                        borderRadius: 6,
                    },
                    {
                        label: 'Egresos',
                        data: expenseData,
                        backgroundColor: 'rgba(239, 68, 68, 0.8)',
                        borderColor: 'rgba(239, 68, 68, 1)',
                        borderWidth: 1,
                        borderRadius: 6,
                    },
                    {
                        label: 'Flujo Neto',
                        data: netFlow,
                        type: 'line',
                        borderColor: 'rgba(59, 130, 246, 1)',
                        backgroundColor: 'transparent',
                        borderWidth: 3,
                        pointBackgroundColor: 'rgba(59, 130, 246, 1)',
                        pointBorderColor: '#fff',
                        pointRadius: 4,
                        pointHoverRadius: 6,
                        tension: 0.4,
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    intersect: false,
                    mode: 'index',
                },
                plugins: {
                    // Desactivar datalabels para que no muestre números en las barras
                    datalabels: {
                        display: false
                    },
                    legend: {
                        position: 'bottom',
                        labels: {
                            usePointStyle: true,
                            padding: 20,
                            color: '#94a3b8',
                            font: { size: 12, family: "'Inter', sans-serif" }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.95)',
                        titleColor: '#f1f5f9',
                        bodyColor: '#cbd5e1',
                        borderColor: 'rgba(148, 163, 184, 0.2)',
                        borderWidth: 1,
                        titleFont: { size: 13, family: "'Inter', sans-serif" },
                        bodyFont: { size: 12, family: "'Inter', sans-serif" },
                        padding: 12,
                        cornerRadius: 8,
                        callbacks: {
                            label: (context) => {
                                return `${context.dataset.label}: ${self.formatCurrencyUSD(context.raw)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: 'rgba(148, 163, 184, 0.1)' },
                        ticks: { 
                            color: '#94a3b8',
                            font: { size: 10, family: "'Inter', sans-serif" },
                            maxRotation: 45,
                            minRotation: 0,
                        }
                    },
                    y: {
                        grid: { color: 'rgba(148, 163, 184, 0.1)' },
                        ticks: {
                            color: '#94a3b8',
                            font: { size: 11, family: "'Inter', sans-serif" },
                            callback: (value) => self.formatCurrencyUSD(value)
                        }
                    }
                }
            }
        });
    }

    formatCurrency(value, currency = 'Bs') {
        if (value === null || value === undefined) return '-';
        const formatted = new Intl.NumberFormat('es-VE', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(value);
        return `${formatted} ${currency}`;
    }

    formatCompact(value) {
        if (Math.abs(value) >= 1000000) {
            return (value / 1000000).toFixed(1) + 'M';
        } else if (Math.abs(value) >= 1000) {
            return (value / 1000).toFixed(1) + 'K';
        }
        return value.toFixed(0);
    }

    formatNumber(value) {
        if (value === null || value === undefined) return '0,00';
        // Redondear a 2 decimales para evitar errores de punto flotante
        const rounded = Math.round(value * 100) / 100;
        // Formato: 1.222.548,41 (punto para miles, coma para decimales)
        return new Intl.NumberFormat('de-DE', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(rounded);
    }

    formatCurrencyUSD(value) {
        if (value === null || value === undefined) return '$ 0,00';
        const rounded = Math.round(value * 100) / 100;
        // Formato: $ 1.222.548,41
        const formatted = new Intl.NumberFormat('de-DE', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2
        }).format(rounded);
        return `$ ${formatted}`;
    }

    onRefresh() {
        this.loadDashboardData();
    }

    async onFlowPeriodChange(period) {
        this.state.flowPeriod = period;
        await this.loadFlowData();
    }

    async onFlowCurrencyChange(currency) {
        this.state.flowCurrency = currency;
        await this.loadFlowData();
    }

    async loadFlowData() {
        // Cargar datos del flujo para el período y moneda seleccionados
        try {
            const flowData = await this.orm.call(
                "cash.register.executive.dashboard",
                "get_flow_data",
                [],
                { period: this.state.flowPeriod, currency: this.state.flowCurrency }
            );
            this.state.flowData = flowData;
            // Re-renderizar solo el gráfico de flujo
            if (this.charts.cashFlow) {
                this.charts.cashFlow.destroy();
            }
            this.renderCashFlowChart();
        } catch (error) {
            console.error("Error loading flow data:", error);
        }
    }

    async onViewCloses() {
        await this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Cierres de Caja',
            res_model: 'cash.register.close',
            view_mode: 'tree,form',
            views: [[false, 'list'], [false, 'form']],
            target: 'current',
        });
    }

    async onNewClose() {
        await this.action.doAction({
            type: 'ir.actions.act_window',
            name: 'Nuevo Cierre de Caja',
            res_model: 'cash.register.close',
            view_mode: 'form',
            views: [[false, 'form']],
            target: 'current',
        });
    }
}

CashRegisterExecutiveDashboard.template = "cash_register_close.ExecutiveDashboard";

registry.category("actions").add("cash_register_executive_dashboard", CashRegisterExecutiveDashboard);

