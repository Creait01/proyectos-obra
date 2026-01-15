# Módulo de Cierre de Caja Diario - Odoo 16

## Descripción

Módulo completo y automatizado para la gestión de cierres de caja diarios en Odoo 16. Permite realizar cierres de múltiples cuentas de efectivo de forma automatizada, con soporte completo para **dual currency (Bolívares y USD)**, control de denominaciones de billetes, billetes en mal estado, y generación de reportes PDF profesionales.

## Características Principales

### 🚀 Automatización
- **Cierre masivo**: Cierre de todas las cuentas de efectivo de múltiples empresas con un solo clic
- **Generación automática de líneas**: El sistema detecta automáticamente las cuentas marcadas como "Cuenta de Efectivo"
- **Cálculo automático**: Saldo inicial, ingresos, egresos y saldo final calculados automáticamente

### 💵 Soporte Dual Currency (Bs/USD)
- **Integración con account_dual_currency**: Automáticamente usa `debit_usd/credit_usd` para cuentas en USD
- **Totales separados**: Dashboard muestra totales en Bolívares (Bs) y en USD por separado
- **Reportes dual currency**: PDF con secciones para ambas monedas
- **Detección automática**: Si la cuenta está configurada en USD, usa los campos USD del módulo dual currency
- **Fallback inteligente**: Si no está instalado account_dual_currency, funciona con campos estándar

### 💰 Control de Efectivo
- **Denominaciones de billetes y monedas**: Sistema completo de conteo por denominación
- **Soporte multi-moneda**: USD, EUR, VES (Bolívares) y cualquier otra moneda configurada
- **Control de billetes en mal estado**: Registro de billetes dañados, rotos, desgastados o sospechosos

### 📊 Dashboard y Vistas
- **Vista Kanban moderna**: Tarjetas visuales con estados y totales Bs/USD
- **Vista calendario**: Visualización de cierres por fecha
- **Vista pivot y gráficos**: Análisis de datos históricos por moneda
- **Dashboard interactivo**: Estadísticas en tiempo real para ambas monedas

### 📄 Reportes PDF
- **Reporte profesional**: Diseño moderno y estilizado
- **Secciones por moneda**: Resumen en Bolívares y resumen en USD
- **Detalle de denominaciones**: Desglose completo del conteo
- **Listado de movimientos**: Todos los movimientos del día por cuenta

## Instalación

1. Copiar la carpeta `cash_register_close` en el directorio de addons de Odoo
2. Actualizar la lista de aplicaciones
3. Instalar el módulo "Cierre de Caja Diario"
4. **Recomendado**: Tener instalado `account_dual_currency` para el soporte completo de USD

## Configuración

### 1. Marcar Cuentas de Efectivo
1. Ir a **Contabilidad > Configuración > Plan Contable**
2. Seleccionar las cuentas de caja/efectivo
3. Activar el campo "Cuenta de Efectivo"
4. **Importante**: Configurar la "Moneda de Caja":
   - Seleccionar **USD** para cuentas en dólares (usará debit_usd/credit_usd)
   - Seleccionar **VES** o dejar vacío para cuentas en Bolívares (usará debit/credit)

### 2. Configurar Denominaciones (Opcional)
El módulo incluye denominaciones predeterminadas para USD, EUR y VES. Para agregar más:
1. Ir a **Contabilidad > Cierre de Caja > Configuración > Denominaciones**
2. Crear las denominaciones necesarias para cada moneda

## Uso

### Crear un Cierre de Caja

#### Opción 1: Cierre Individual
1. Ir a **Contabilidad > Cierre de Caja > Cierres de Caja**
2. Clic en **Crear**
3. Seleccionar fecha y empresa
4. Clic en **Generar Líneas**
5. Completar el conteo de cada cuenta
6. Clic en **Cerrar Caja**

#### Opción 2: Cierre Masivo (Recomendado)
1. Ir a **Contabilidad > Cierre de Caja > Cierre Masivo**
2. Seleccionar fecha
3. Marcar "Cerrar Todas las Compañías" o seleccionar empresas específicas
4. Clic en **Generar Cierres**

### Contar Efectivo
1. En la línea de la cuenta, clic en el icono de calculadora
2. Ingresar la cantidad de cada denominación
3. Registrar billetes en mal estado si los hay
4. Clic en **Confirmar Conteo**

### Generar Reporte PDF
1. Con el cierre en estado "En Proceso" o "Cerrado"
2. Clic en **Imprimir Reporte**
3. El PDF incluye:
   - Resumen general
   - Detalle por cuenta
   - Denominaciones contadas
   - Billetes en mal estado
   - Listado de movimientos

## Estados del Cierre

| Estado | Descripción |
|--------|-------------|
| **Borrador** | Cierre creado, pendiente de generar líneas |
| **En Proceso** | Líneas generadas, pendiente de conteo |
| **Cerrado** | Conteo completado y cierre finalizado |
| **Cancelado** | Cierre anulado |

## Modelo de Datos

### Modelos Principales
- `cash.register.close`: Cierre de caja principal
- `cash.register.close.line`: Línea de cierre por cuenta
- `cash.denomination`: Denominaciones de billetes/monedas
- `cash.register.denomination.line`: Conteo de denominaciones
- `cash.register.bad.bills`: Billetes en mal estado

### Campo Agregado
- `account.account.is_cash_account`: Campo booleano para marcar cuentas de efectivo

## Seguridad

### Grupos de Usuarios
- **Cierre de Caja: Usuario**: Puede crear y gestionar cierres
- **Cierre de Caja: Administrador**: Acceso completo incluyendo eliminación y configuración

### Reglas de Registro
- Filtrado por compañía (multi-empresa)

## Soporte Multi-Empresa

El módulo soporta completamente entornos multi-empresa:
- Cada cierre pertenece a una empresa específica
- El cierre masivo puede procesar múltiples empresas simultáneamente
- Las cuentas de efectivo son específicas por empresa

## Personalización

### Agregar Nuevas Monedas
1. Crear las denominaciones en **Configuración > Denominaciones**
2. Asignar la moneda correspondiente

### Modificar Estilos
Los estilos se encuentran en:
- `static/src/scss/cash_register.scss`

### Modificar Reporte PDF
La plantilla del reporte está en:
- `reports/cash_register_report_template.xml`

## Requisitos

- Odoo 16.0
- Módulos dependientes:
  - `account`
  - `account_accountant`
  - `base`
  - `web`

## Licencia

LGPL-3

## Autor

Tu Empresa

## Soporte

Para soporte técnico, contactar a: soporte@tuempresa.com
