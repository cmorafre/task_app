# ScriptFlow Product Requirements Document (PRD)

## Goals and Background Context

### Goals
- Validar product-market fit com uma empresa piloto (máx 5 usuários)
- Desenvolver MVP funcional em 2-3 meses com orçamento de $20
- Simplificar automação de scripts Python/.bat sem complexidade do Airflow
- Criar interface intuitiva para agendamento e monitoramento
- Estabelecer base sólida para escalabilidade futura

### Background Context

O ScriptFlow surge da necessidade de pequenas empresas por ferramentas de automação simples e acessíveis. Enquanto soluções como Airflow requerem conhecimento técnico avançado em DAGs e Python frameworks, muitas PMEs precisam apenas executar scripts Python e .bat de forma confiável e monitorada.

O projeto adota uma abordagem de validação minimalista: começar com uma empresa piloto para comprovar o valor da solução antes de investir em escalabilidade. Esta estratégia permite aprendizado real do mercado com investimento mínimo e foco em funcionalidades essenciais.

### Change Log
| Date | Version | Description | Author |
|------|---------|-------------|---------|
| 2025-01-14 | 1.0 | Criação inicial do PRD baseado no Project Brief | Mary (Business Analyst) |

## Requirements

### Functional Requirements

1. **FR1**: O sistema deve permitir upload de arquivos .py e .bat através de interface web simples
2. **FR2**: O sistema deve permitir configurar agendamentos básicos (diário, semanal, mensal) através de formulário
3. **FR3**: O sistema deve executar scripts Python e .bat em ambiente Windows controlado
4. **FR4**: O sistema deve capturar e armazenar stdout/stderr de todas as execuções com timestamps
5. **FR5**: O sistema deve exibir dashboard com lista de scripts, última execução, próxima execução e status
6. **FR6**: O sistema deve enviar notificações por email quando scripts falham ou terminam
7. **FR7**: O sistema deve ter autenticação básica com login/senha simples
8. **FR8**: O sistema deve permitir visualizar logs de execuções anteriores
9. **FR9**: O sistema deve mostrar status em tempo real (executando/sucesso/falha) no dashboard
10. **FR10**: O sistema deve permitir editar ou deletar scripts e agendamentos existentes

### Non-Functional Requirements

1. **NFR1**: O sistema deve funcionar em ambiente Windows (Server 2016+ ou Windows 10/11)
2. **NFR2**: O sistema deve suportar até 5 usuários simultâneos (limite do piloto)
3. **NFR3**: O sistema deve ter uptime de 95%+ durante horário comercial
4. **NFR4**: O sistema deve executar scripts com isolamento básico para segurança
5. **NFR5**: O sistema deve funcionar com hosting de $6/mês máximo (Digital Ocean, VPS nacional)
6. **NFR6**: O sistema deve ter interface responsiva para browsers modernos (Chrome, Firefox, Edge)
7. **NFR7**: O sistema deve manter logs por no mínimo 30 dias
8. **NFR8**: O sistema deve permitir execução de até 10 scripts diferentes simultaneamente
9. **NFR9**: O sistema deve ter tempo de resposta de interface < 3 segundos para operações básicas
10. **NFR10**: O sistema deve ser deployável em até 1 hora em ambiente novo

## User Interface Design Goals

### Overall UX Vision
Interface minimalista e funcional inspirada em ferramentas administrativas clássicas. Prioriza eficiência e clareza sobre elementos visuais elaborados. O usuário deve conseguir executar todas as tarefas principais (upload, agendamento, monitoramento) em máximo 3 cliques, com feedback visual claro sobre o status de cada operação.

### Key Interaction Paradigms
- **Form-First Design**: Formulários simples e diretos para todas as configurações
- **Table-Based Data Display**: Listas tabulares para scripts e logs (familiar para administradores IT)  
- **Status-Driven UI**: Cores e ícones claros indicando status (verde=sucesso, vermelho=falha, amarelo=executando)
- **Minimal Confirmation Flow**: Confirmações apenas para ações destrutivas (deletar script/logs)

### Core Screens and Views
- **Login Screen**: Formulário básico de autenticação
- **Dashboard Principal**: Tabela com todos os scripts, status, próxima execução, ações rápidas
- **Upload/Configuração de Script**: Formulário para upload + configuração de agendamento
- **Visualização de Logs**: Interface para navegar e filtrar logs de execuções
- **Configurações**: Preferências básicas de usuário e notificações

### Accessibility: WCAG AA
Conformidade WCAG AA básica: contraste adequado, navegação por teclado, labels descritivos em formulários, textos alternativos para ícones de status.

### Branding
Visual limpo e profissional adequado para ambiente corporativo. Paleta de cores neutras (cinza/azul) com indicadores de status bem definidos. Sem elementos decorativos - foco total na funcionalidade.

### Target Device and Platforms: Web Responsive
Interface responsiva otimizada para desktop (uso principal) com suporte básico para tablets. Design mobile-friendly para consulta de status, mas funcionalidades principais otimizadas para telas ≥ 1024px.

## Technical Assumptions

### Repository Structure: Monorepo
Projeto único com estrutura simples: `/app` (backend Flask), `/templates` (frontend HTML/CSS), `/scripts` (área de upload), `/logs`, `/tests`. Evita complexidade de múltiplos repositórios para MVP.

### Service Architecture
**Arquitetura Monolítica Simples**: Aplicação Flask única que gerencia autenticação, upload, agendamento, execução e logging. Componentes separados por módulos Python mas executando em processo único para minimizar overhead de infraestrutura.

### Testing Requirements
**Unit + Integration Básico**: Testes unitários para funções críticas (execução de scripts, agendamento) e testes de integração para fluxos principais. Sem testes e2e complexos para manter simplicidade, mas com testes manuais estruturados.

### Additional Technical Assumptions and Requests

**Framework e Linguagem:**
- **Backend**: Python 3.9+ com Flask (simplicidade, comunidade, compatibilidade Windows)
- **Frontend**: Jinja2 templates + Bootstrap CSS (desenvolvimento rápido, sem JavaScript complexo)
- **Database**: SQLite para desenvolvimento/piloto, migração para PostgreSQL apenas se necessário
- **Task Scheduling**: APScheduler (biblioteca Python) para gerenciar agendamentos

**Deployment e Infraestrutura:**
- **Hosting**: Digital Ocean Droplet $6/mês ou VPS nacional equivalente
- **OS Target**: Ubuntu 20.04+ (familiar, suporte Python/Windows via Wine se necessário)
- **Web Server**: Gunicorn + Nginx para produção simples
- **Process Manager**: systemd para garantir restart automático

**Segurança e Isolamento:**
- **Script Execution**: subprocess.run() com timeout, working directory isolado
- **File Security**: Validação de extensões, quarentena de uploads, size limits
- **Authentication**: Flask-Login com sessions simples, sem OAuth complexo
- **Environment**: Virtual environment Python isolado para execução de scripts

**Monitoramento e Observabilidade:**
- **Logging**: Python logging module com rotação automática
- **Health Check**: Endpoint /health para monitoramento básico
- **Email**: SMTP simples (Gmail/SendGrid free tier) para notificações
- **Backup**: Snapshot manual semanal do SQLite + scripts

## Epic List

**Epic 1: Foundation & Authentication**  
Estabelece infraestrutura básica do projeto, autenticação e interface inicial funcional

**Epic 2: Script Management & Execution**  
Implementa funcionalidades core: upload, armazenamento e execução básica de scripts

**Epic 3: Scheduling & Automation**  
Adiciona agendamento automático e sistema de jobs para execução programada

**Epic 4: Monitoring & Notifications**  
Completa o MVP com logging avançado, dashboard e notificações por email

## Epic 1: Foundation & Authentication

**Epic Goal**: Estabelecer a fundação técnica do projeto com aplicação Flask deployável, sistema de autenticação funcional e interface web básica que permite acesso seguro ao sistema, criando a base para todas as funcionalidades subsequentes do ScriptFlow.

### Story 1.1: Project Setup & Infrastructure

As a **developer**,  
I want **to set up the basic Flask project structure with database and configuration**,  
so that **I have a solid foundation to build the ScriptFlow application**.

#### Acceptance Criteria
1. Flask application structure created with proper folder organization (app/, templates/, static/, tests/)
2. SQLite database initialized with basic schema for users and future entities
3. Configuration system implemented with development/production environments
4. Basic requirements.txt with Flask, SQLAlchemy, and essential dependencies
5. Application runs successfully on localhost with "Hello ScriptFlow" page
6. Git repository initialized with proper .gitignore for Python projects
7. Basic logging configuration implemented for development debugging

### Story 1.2: User Authentication System

As a **system administrator**,  
I want **to log in securely to access the ScriptFlow system**,  
so that **only authorized users can manage automation scripts**.

#### Acceptance Criteria
1. User model created in database with username, password hash, and basic profile fields
2. Login form rendered with username/password fields and submit button
3. Password hashing implemented using secure methods (bcrypt/werkzeug)
4. Session management configured to maintain login state
5. Login POST endpoint validates credentials and creates user session
6. Logout functionality clears session and redirects to login page
7. Protected routes decorator implemented to require authentication
8. Default admin user created during database initialization

### Story 1.3: Basic Dashboard Interface

As a **logged-in user**,  
I want **to see a main dashboard after logging in**,  
so that **I have a central place to access all ScriptFlow features**.

#### Acceptance Criteria
1. Dashboard template created with navigation menu and main content area
2. User authentication state displayed (username, logout link)
3. Navigation menu includes placeholders for future features (Scripts, Logs, Settings)
4. Responsive layout implemented using Bootstrap CSS framework
5. Dashboard accessible only after successful authentication
6. Basic styling applied for professional appearance matching design goals
7. Footer with ScriptFlow branding and version information
8. Page loads within 2 seconds on local development environment

## Epic 2: Script Management & Execution

**Epic Goal**: Implementar as funcionalidades centrais do ScriptFlow para upload, armazenamento e execução manual de scripts Python e .bat, permitindo que usuários gerenciem e executem seus scripts através da interface web, entregando o valor core da aplicação.

### Story 2.1: Script Upload & Storage

As a **system administrator**,  
I want **to upload Python and .bat files through the web interface**,  
so that **I can store my automation scripts in the ScriptFlow system**.

#### Acceptance Criteria
1. Script model created in database with filename, file_path, script_type, upload_date, and user_id
2. Upload form rendered with file input, script name field, and description textarea
3. File validation implemented for .py and .bat extensions only
4. File size limit enforced (max 10MB per script)
5. Uploaded files stored in secure directory with unique filenames
6. Script metadata saved to database with relationship to uploading user
7. Success message displayed after successful upload with script details
8. Error handling for invalid files, size limits, and duplicate names

### Story 2.2: Script Management Interface

As a **user with uploaded scripts**,  
I want **to view, edit, and delete my scripts**,  
so that **I can manage my automation library effectively**.

#### Acceptance Criteria
1. Scripts list page displays all user's scripts in table format
2. Table shows script name, type, upload date, last execution, and action buttons
3. View script functionality displays file content in read-only format
4. Edit script functionality allows updating script content and metadata
5. Delete script functionality with confirmation dialog removes script and file
6. Search/filter functionality to find scripts by name or type
7. Scripts sorted by most recently uploaded by default
8. Pagination implemented if more than 20 scripts exist

### Story 2.3: Manual Script Execution

As a **user with uploaded scripts**,  
I want **to execute scripts manually with immediate feedback**,  
so that **I can test and run my automation scripts on demand**.

#### Acceptance Criteria
1. Execute button available on script list and detail pages
2. Script execution runs in isolated subprocess with timeout (5 minutes default)
3. Execution output (stdout/stderr) captured and displayed in real-time interface
4. Execution status tracked (running, completed, failed, timeout) with visual indicators
5. Working directory isolated for each execution to prevent file conflicts
6. Execution results stored in database with timestamp, status, and output logs
7. Kill/cancel functionality for long-running scripts
8. Python scripts executed in virtual environment for basic isolation

### Story 2.4: Execution History & Results

As a **user who has executed scripts**,  
I want **to view execution history and results**,  
so that **I can track script performance and troubleshoot issues**.

#### Acceptance Criteria
1. Execution history page lists all past executions for user's scripts
2. History table shows script name, execution time, duration, status, and view details link
3. Execution details page displays full output logs with timestamps
4. Filter executions by script, date range, or status (success/failure)
5. Export execution results to text file for external analysis
6. Execution logs retained for 30 days as per NFR requirements
7. Color-coded status indicators (green=success, red=failure, yellow=running)
8. Search functionality to find specific execution output content

## Epic 3: Scheduling & Automation

**Epic Goal**: Implementar sistema de agendamento automático que permite configurar execuções programadas de scripts (diário, semanal, mensal), transformando o ScriptFlow de ferramenta de execução manual em plataforma de automação completa, entregando o diferencial competitivo principal versus soluções básicas.

### Story 3.1: Schedule Configuration Interface

As a **user with uploaded scripts**,  
I want **to configure execution schedules for my scripts**,  
so that **I can automate recurring tasks without manual intervention**.

#### Acceptance Criteria
1. Schedule model created in database with script_id, schedule_type, schedule_config, next_execution, is_active
2. Schedule configuration form with frequency options (daily, weekly, monthly)
3. Time picker for execution hour/minute with timezone handling
4. Weekly schedule allows selecting specific days of week (checkboxes)
5. Monthly schedule allows selecting specific day of month (1-31 dropdown)
6. Schedule preview shows next 5 execution times before saving
7. Active/inactive toggle to temporarily disable schedules without deletion
8. Form validation prevents invalid combinations (e.g., Feb 31st monthly schedule)

### Story 3.2: Schedule Management & Monitoring

As a **user with scheduled scripts**,  
I want **to view and manage all my active schedules**,  
so that **I can monitor and control my automated tasks**.

#### Acceptance Criteria
1. Schedules overview page lists all user's schedules with key information
2. Table displays script name, schedule type, next execution, last execution, status
3. Edit schedule functionality allows modifying frequency and timing
4. Delete schedule with confirmation removes scheduling but keeps script
5. Bulk actions to activate/deactivate multiple schedules
6. Schedule status indicators show active/inactive/error states
7. Quick actions to run scheduled script immediately (manual trigger)
8. Sort schedules by next execution time, creation date, or script name

### Story 3.3: Background Job Execution Engine

As a **system administrator**,  
I want **scheduled scripts to execute automatically in background**,  
so that **automation runs reliably without user intervention**.

#### Acceptance Criteria
1. APScheduler integrated with Flask application for job management
2. Job scheduler service starts with application and persists jobs across restarts
3. Scheduled executions run in background without blocking web interface
4. Job execution uses same isolation and logging as manual executions
5. Failed job executions automatically retry once after 5-minute delay
6. Scheduler handles multiple concurrent executions without conflicts
7. Job persistence survives application restarts using database storage
8. Scheduler status endpoint shows running jobs and next scheduled executions

### Story 3.4: Schedule Execution Tracking

As a **user with scheduled scripts**,  
I want **to track execution history and success rates of my scheduled jobs**,  
so that **I can ensure my automations are running reliably**.

#### Acceptance Criteria
1. Scheduled execution records tagged differently from manual executions
2. Schedule performance metrics show success rate, avg duration, last 30 days
3. Schedule detail page displays execution calendar view with success/failure indicators
4. Failed schedule execution generates alert flag requiring user acknowledgment
5. Schedule reliability dashboard shows overall system health metrics
6. Execution trend charts show performance over time for each schedule
7. Schedule can be automatically disabled after 3 consecutive failures
8. Notification preferences per schedule (immediate failure alerts vs daily summaries)

## Epic 4: Monitoring & Notifications

**Epic Goal**: Completar o MVP com sistema robusto de monitoramento, logging avançado e notificações por email, proporcionando visibilidade completa sobre o estado e performance das automações, essencial para uso em ambiente de produção.

### Story 4.1: Enhanced Logging System

As a **system administrator**,  
I want **comprehensive logging of all system activities and script executions**,  
so that **I can troubleshoot issues and monitor system health effectively**.

#### Acceptance Criteria
1. Structured logging implemented with consistent format across all system components
2. Log levels properly configured (DEBUG, INFO, WARNING, ERROR, CRITICAL)
3. Log rotation configured to prevent disk space issues (max 100MB per log file)
4. Separate log files for different components (web, scheduler, script execution)
5. System events logged (user login/logout, script uploads, schedule changes)
6. Performance metrics logged (execution times, memory usage, concurrent jobs)
7. Log search interface allows filtering by level, component, date range
8. Log export functionality for external analysis tools

### Story 4.2: Email Notification System

As a **user with automated scripts**,  
I want **to receive email notifications about script execution results**,  
so that **I can stay informed about my automations without constantly checking the dashboard**.

#### Acceptance Criteria
1. SMTP configuration interface for email settings (server, port, credentials)
2. Email templates created for different notification types (success, failure, warnings)
3. User notification preferences configurable per script or globally
4. Immediate failure notifications sent within 1 minute of script failure
5. Daily/weekly summary reports with execution statistics
6. Email content includes relevant details (script name, execution time, error logs)
7. Notification history tracked to prevent spam and allow audit
8. Email sending resilient with retry logic for temporary SMTP failures

### Story 4.3: System Health Dashboard

As a **system administrator**,  
I want **to monitor overall system health and performance metrics**,  
so that **I can ensure ScriptFlow is running optimally and identify potential issues**.

#### Acceptance Criteria
1. System metrics dashboard shows CPU usage, memory usage, disk space
2. Scheduler health indicators display active jobs, queue status, last execution times
3. Success rate metrics for last 24 hours, 7 days, 30 days
4. Alert indicators for system issues (high resource usage, failed services)
5. Database health status (connection pool, query performance, table sizes)
6. Real-time updates of dashboard metrics without page refresh
7. Historical trend charts for key performance indicators
8. System status page suitable for sharing with stakeholders

### Story 4.4: Advanced Script Analytics

As a **user with multiple automated scripts**,  
I want **detailed analytics and insights about my script performance**,  
so that **I can optimize my automations and identify patterns or issues**.

#### Acceptance Criteria
1. Script performance analytics page with execution time trends
2. Success/failure rate analysis with statistical breakdowns
3. Resource usage analytics (memory, CPU time) per script execution
4. Execution pattern analysis (peak times, frequency distribution)
5. Comparative analytics between different scripts and schedules
6. Anomaly detection for unusual execution times or failure patterns
7. Performance recommendations based on execution history
8. Analytics data export for external business intelligence tools

## Next Steps

### UX Expert Prompt
Review the PRD and create detailed wireframes and user interface specifications for ScriptFlow. Focus on the form-first design approach and table-based data display. Ensure the interface meets WCAG AA accessibility standards while maintaining the clean, professional aesthetic suitable for system administrators. Pay special attention to status indicators and the dashboard layout for optimal user experience.

### Architect Prompt
Based on this PRD, create a detailed technical architecture for ScriptFlow. Design the Flask application structure, database schema, and deployment architecture that can handle the MVP requirements within the $20 budget constraint. Focus on the monolithic approach using SQLite initially, with clear migration path to PostgreSQL. Include security considerations for script execution isolation and detailed implementation plan for the APScheduler integration.

## Summary

This PRD defines a comprehensive MVP for ScriptFlow that delivers core automation value while maintaining budget constraints and realistic timelines. The 4-epic structure ensures incremental delivery of value, with each epic building upon the previous foundation. The system prioritizes simplicity and reliability over complex features, making it ideal for validation with a pilot company before scaling.

Key differentiators include native Windows script support, simplified scheduling without DAG complexity, and focus on small business needs rather than enterprise-scale features. The technical decisions favor proven, simple technologies that can be developed quickly by a single developer while maintaining professional quality suitable for production use.