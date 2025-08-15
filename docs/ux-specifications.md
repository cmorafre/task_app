# ScriptFlow UX Design Specifications

## Design System Overview

### Color Scheme
- **Primary**: #2C3E50 (Dark Blue-Gray) - Navigation, headers
- **Secondary**: #34495E (Medium Blue-Gray) - Accent elements
- **Success**: #27AE60 (Green) - Script success, completed tasks
- **Warning**: #F39C12 (Orange) - Scripts running, warnings
- **Danger**: #E74C3C (Red) - Script failures, errors
- **Background**: #F8F9FA (Light Gray) - Page background
- **White**: #FFFFFF - Card backgrounds, form fields
- **Text Primary**: #2C3E50 (Dark Blue-Gray)
- **Text Secondary**: #7F8C8D (Medium Gray)

### Typography
- **Primary Font**: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif
- **Headers**: 600 weight, proper hierarchy (h1: 28px, h2: 24px, h3: 20px, h4: 18px)
- **Body**: 400 weight, 16px base size, 1.5 line-height
- **Small Text**: 14px for timestamps, secondary info
- **Code/Logs**: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace

### Layout Grid
- **Container**: Bootstrap container-fluid with max-width: 1400px
- **Breakpoints**: lg (≥1024px) primary, md (≥768px) basic support
- **Spacing**: 8px base unit (rem multiples: 0.5rem, 1rem, 1.5rem, 2rem, 3rem)

---

## 1. Login Screen

### Wireframe (ASCII)
```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│                        ScriptFlow                          │
│                    Automation Made Simple                  │
│                                                             │
│               ┌─────────────────────────────┐               │
│               │                             │               │
│               │  ┌─────────────────────┐    │               │
│               │  │ Username            │    │               │
│               │  └─────────────────────┘    │               │
│               │                             │               │
│               │  ┌─────────────────────┐    │               │
│               │  │ Password            │    │               │
│               │  └─────────────────────┘    │               │
│               │                             │               │
│               │  □ Remember me              │               │
│               │                             │               │
│               │     ┌─────────────┐         │               │
│               │     │   Sign In   │         │               │
│               │     └─────────────┘         │               │
│               │                             │               │
│               └─────────────────────────────┘               │
│                                                             │
│                    © 2025 ScriptFlow v1.0                  │
└─────────────────────────────────────────────────────────────┘
```

### UI Specifications

**Layout**: 
- Centered card (400px width) on full viewport background
- Card elevation: shadow-lg for depth
- Padding: 2rem inside card

**Form Elements**:
- Input fields: Bootstrap form-control class
- Height: 48px for touch accessibility
- Border-radius: 4px
- Focus state: 2px blue outline
- Error state: Red border + error message below

**Accessibility**:
- Labels: Properly associated with for/id attributes
- ARIA labels for screen readers
- Tab navigation order: username → password → remember → sign in
- High contrast ratios (4.5:1 minimum)

**Responsive Behavior**:
- Mobile (≤768px): Card becomes full-width with 1rem margin
- Maintains vertical centering on all screen sizes

---

## 2. Dashboard Principal

### Wireframe (ASCII)
```
┌─────────────────────────────────────────────────────────────┐
│ ScriptFlow    Scripts  Schedules  Logs  Settings     User ▼ │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─ Dashboard ─────────────────────────────────────────────┐ │
│ │                                                         │ │
│ │ ┌─System Status────┐ ┌─Quick Stats─────┐ ┌─Actions─────┐ │ │
│ │ │ ● All Services   │ │ 12 Scripts      │ │ ┌─Upload───┐ │ │ │
│ │ │   Running        │ │  8 Active       │ │ │New Script│ │ │ │
│ │ │ ● Next Run       │ │  4 Scheduled    │ │ └─────────┘ │ │ │
│ │ │   in 2h 15m      │ │ 24 Executions   │ │ ┌─Schedule─┐ │ │ │
│ │ │                  │ │   (last 24h)    │ │ │New Job   │ │ │ │
│ │ └─────────────────┘ └─────────────────┘ │ └─────────┘ │ │ │
│ │                                         └─────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─ Recent Scripts ────────────────────────────────────────┐ │
│ │ Search: [________________] Filter: [All ▼] Status: [▼] │ │
│ │                                                         │ │
│ │ Script Name     │Type│Last Run │Next Run │Status │Actions │ │
│ │─────────────────┼────┼─────────┼─────────┼───────┼────────│ │
│ │ backup_daily.py │ PY │2h ago   │22:00    │ ● RUN │[▶][⚙][🗑]│ │
│ │ cleanup.bat     │BAT │Failed   │Daily 9AM│ ● ERR │[▶][⚙][🗑]│ │
│ │ report_gen.py   │ PY │Success  │Weekly   │ ● OK  │[▶][⚙][🗑]│ │
│ │ monitor.py      │ PY │Running  │Hourly   │ ● RUN │[⏹][⚙][🗑]│ │
│ │ sync_files.bat  │BAT │1d ago   │Manual   │ ● OK  │[▶][⚙][🗑]│ │
│ │                 │    │         │         │       │        │ │
│ │ ← Prev   Page 1 of 3                         Next → │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### UI Specifications

**Header Navigation**:
- Height: 60px, fixed position
- Logo: Left-aligned, 24px font-size
- Nav items: Horizontal spacing with hover states
- User dropdown: Right-aligned with avatar/username

**Status Cards** (Top Row):
- Grid: 3 columns on desktop, stack on mobile
- Height: 120px each
- Background: White with subtle border
- Icons: 20px status indicators with color coding

**Scripts Table**:
- Responsive table with horizontal scroll on mobile
- Row height: 48px for accessibility
- Alternating row colors for readability
- Status indicators: Colored circles (8px diameter)

**Action Buttons**:
- Size: 32x32px for touch targets
- Icons: Play (▶), Settings (⚙), Delete (🗑), Stop (⏹)
- Tooltips on hover with keyboard access

**Search & Filters**:
- Search: 300px width, debounced input
- Dropdowns: Bootstrap select with custom styling
- Clear filters button when active

**Accessibility**:
- Table headers: Proper scope attributes
- Action buttons: ARIA labels and keyboard navigation
- Status: Text alternatives for color-blind users
- Focus management: Visible focus indicators

---

## 3. Upload/Script Configuration

### Wireframe (ASCII)
```
┌─────────────────────────────────────────────────────────────┐
│ ScriptFlow    Scripts  Schedules  Logs  Settings     User ▼ │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─ Upload New Script ─────────────────────────────────────┐ │
│ │                                                         │ │
│ │ ┌─ Script File ──────────────────────────────────────┐  │ │
│ │ │                                                    │  │ │
│ │ │ Choose File: [Browse...] ▢ backup_daily.py        │  │ │
│ │ │ Supported: .py, .bat (max 10MB)                   │  │ │
│ │ │                                                    │  │ │
│ │ └────────────────────────────────────────────────────┘  │ │
│ │                                                         │ │
│ │ ┌─ Script Details ───────────────────────────────────┐  │ │
│ │ │ Name: [backup_daily                              ] │  │ │
│ │ │                                                   │  │ │
│ │ │ Description:                                      │  │ │
│ │ │ ┌─────────────────────────────────────────────────┐ │  │ │
│ │ │ │Daily backup script for user data               │ │  │ │
│ │ │ │Runs MySQL dump and copies to backup server     │ │  │ │
│ │ │ │                                                 │ │  │ │
│ │ │ └─────────────────────────────────────────────────┘ │  │ │
│ │ └───────────────────────────────────────────────────┘  │ │
│ │                                                         │ │
│ │ ┌─ Schedule Configuration (Optional) ─────────────────┐  │ │
│ │ │ □ Enable automatic scheduling                       │  │ │
│ │ │                                                     │  │ │
│ │ │ Frequency: [Daily        ▼]                        │  │ │
│ │ │ Time: [22] : [00] [UTC-5 ▼]                        │  │ │
│ │ │                                                     │  │ │
│ │ │ Next execution: Today at 10:00 PM                  │  │ │
│ │ └─────────────────────────────────────────────────────┘  │ │
│ │                                                         │ │
│ │ ┌─ Notifications ────────────────────────────────────┐  │ │
│ │ │ □ Email on success   □ Email on failure            │  │ │
│ │ │ Recipients: [admin@company.com                   ] │  │ │
│ │ └───────────────────────────────────────────────────┘  │ │
│ │                                                         │ │
│ │ [Cancel]                            [Upload Script]     │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### UI Specifications

**Form Layout**:
- Card-based sections with clear visual separation
- Progressive disclosure: Schedule only visible when checkbox enabled
- Form width: 800px max with responsive scaling

**File Upload**:
- Drag & drop zone with visual feedback
- File type validation with clear error messages
- Progress indicator for large files
- Preview of selected file with remove option

**Form Controls**:
- Input fields: Consistent spacing (1rem margin-bottom)
- Textarea: Auto-resize with max-height
- Select dropdowns: Custom styled for consistency
- Checkboxes: Larger touch targets (20px)

**Schedule Section**:
- Time picker: Native input[type="time"] with timezone selector
- Frequency options: Daily, Weekly, Monthly with appropriate sub-options
- Preview calculation: Real-time next execution display

**Validation**:
- Real-time validation with inline error messages
- Submit button disabled until valid
- Success state with progress feedback

**Accessibility**:
- Form sections: Proper fieldset/legend structure
- Required fields: Visual and programmatic indicators
- Error messages: ARIA describedby associations
- Keyboard navigation: Logical tab order

---

## 4. Script Management

### Wireframe (ASCII)
```
┌─────────────────────────────────────────────────────────────┐
│ ScriptFlow    Scripts  Schedules  Logs  Settings     User ▼ │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─ Script Management ─────────────────────────────────────┐ │
│ │                                                         │ │
│ │ [➕ Upload New]  Search: [___________] [🔍] [Clear]    │ │
│ │                                                         │ │
│ │ ┌─ Filters ──────────────────────────────────────────┐  │ │
│ │ │ Type: [All ▼] Status: [All ▼] Schedule: [All ▼]   │  │ │
│ │ │ Modified: [Last 30 days ▼]  Show: [20 ▼] per page │  │ │
│ │ └────────────────────────────────────────────────────┘  │ │
│ │                                                         │ │
│ │ ┌─ Scripts List ─────────────────────────────────────┐  │ │
│ │ │                                                    │  │ │
│ │ │☑ Name           │Type│Modified │Status│Next Run│⚙  │  │ │
│ │ │──────────────────┼────┼─────────┼──────┼────────┼───│  │ │
│ │ │☑ backup_daily.py│ PY │2h ago   │● OK  │22:00   │ ⋮ │  │ │
│ │ │☑ cleanup.bat    │BAT │1d ago   │● ERR │Manual  │ ⋮ │  │ │
│ │ │☑ report_gen.py  │ PY │3d ago   │● OK  │Weekly  │ ⋮ │  │ │
│ │ │☑ sync_files.bat │BAT │1w ago   │● OK  │Manual  │ ⋮ │  │ │
│ │ │☑ monitor.py     │ PY │2w ago   │● RUN │Hourly  │ ⋮ │  │ │
│ │ │                 │    │         │      │        │   │  │ │
│ │ └────────────────────────────────────────────────────┘  │ │
│ │                                                         │ │
│ │ Bulk Actions: [▶ Run Selected] [📅 Schedule] [🗑 Delete] │ │
│ │                                                         │ │
│ │ ← Prev   Page 1 of 3   Showing 1-20 of 47   Next →    │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─ Script Details Modal ──────────────────────────────────┐ │
│ │ backup_daily.py                               [✕ Close] │ │
│ │ ───────────────────────────────────────────────────────── │ │
│ │ Type: Python  Size: 2.3KB  Modified: 2h ago           │ │
│ │ Description: Daily backup script for user data         │ │
│ │                                                         │ │
│ │ Last Execution: Success (2h ago) - Duration: 45s       │ │
│ │ Schedule: Daily at 22:00 UTC-5 (Active)               │ │
│ │                                                         │ │
│ │ [📝 Edit] [▶ Run Now] [📅 Schedule] [📊 View Logs]    │ │
│ │ [⬇ Download] [🗑 Delete]                               │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### UI Specifications

**List Management**:
- Sortable columns with visual indicators
- Bulk selection with select-all functionality
- Row actions accessible via context menu (⋮)
- Quick preview on row hover

**Filtering System**:
- Multiple filter criteria with AND logic
- Filter chips showing active filters
- Saved filter presets for common views
- Real-time results update

**Detail Modal**:
- Overlay: Semi-transparent backdrop
- Size: 600px width, max-height with scroll
- Quick actions: Prominent button layout
- Close: ESC key + click outside + X button

**Status Indicators**:
- Color-coded status dots with text labels
- Last execution: Relative timestamps
- Schedule: Human-readable format with status

**Bulk Operations**:
- Selection counter with clear action buttons
- Confirmation dialogs for destructive actions
- Progress feedback for bulk operations

**Accessibility**:
- Table: Proper headers and cell associations
- Modals: Focus trap and ARIA attributes
- Bulk actions: Clear selection state communication
- Keyboard shortcuts: Documented and consistent

---

## 5. Logs Visualization

### Wireframe (ASCII)
```
┌─────────────────────────────────────────────────────────────┐
│ ScriptFlow    Scripts  Schedules  Logs  Settings     User ▼ │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─ Execution Logs ────────────────────────────────────────┐ │
│ │                                                         │ │
│ │ ┌─ Filters ──────────────────────────────────────────┐  │ │
│ │ │ Script: [All Scripts     ▼] Status: [All ▼]       │  │ │
│ │ │ From: [2025-01-10] To: [2025-01-14]               │  │ │
│ │ │ Search Logs: [____________________] [🔍] [Clear]   │  │ │
│ │ └────────────────────────────────────────────────────┘  │ │
│ │                                                         │ │
│ │ ┌─ Execution History ────────────────────────────────┐  │ │
│ │ │                                                    │  │ │
│ │ │ Time       │Script        │Status│Duration│Output│   │ │
│ │ │────────────┼─────────────┼──────┼────────┼──────│   │ │
│ │ │ 14:30:25   │backup_daily │● OK  │45.2s   │ 📄   │   │ │
│ │ │ 14:15:10   │monitor      │● RUN │2m 15s  │ 👁   │   │ │
│ │ │ 13:45:00   │cleanup      │● ERR │2.1s    │ 📄   │   │ │
│ │ │ 12:30:15   │report_gen   │● OK  │1m 33s  │ 📄   │   │ │
│ │ │ 11:15:22   │sync_files   │● OK  │12.5s   │ 📄   │   │ │
│ │ │ 10:00:30   │backup_daily │● OK  │43.8s   │ 📄   │   │ │
│ │ │                                                    │   │ │
│ │ └────────────────────────────────────────────────────┘  │ │
│ │                                                         │ │
│ │ [📥 Export CSV] [🔄 Auto-refresh: 30s ▼] [⚙ Settings] │ │ │
│ │                                                         │ │
│ │ ← Prev   Page 1 of 12   Showing 1-50 of 573   Next →  │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─ Log Detail Modal ──────────────────────────────────────┐ │
│ │ Execution Log - backup_daily.py              [✕ Close] │ │
│ │ ───────────────────────────────────────────────────────── │ │
│ │ Started: 2025-01-14 14:30:25 UTC-5                     │ │
│ │ Duration: 45.2 seconds                                  │ │
│ │ Status: Success ● Exit Code: 0                         │ │
│ │                                                         │ │
│ │ ┌─ Output ────────────────────────────────────────────┐ │ │
│ │ │ 14:30:25 Starting backup process...                │ │ │
│ │ │ 14:30:26 Connecting to database...                 │ │ │
│ │ │ 14:30:27 Database connected successfully            │ │ │
│ │ │ 14:30:28 Creating backup: backup_20250114.sql      │ │ │
│ │ │ 14:30:45 Backup completed: 2.3MB                   │ │ │
│ │ │ 14:31:02 Copying to backup server...               │ │ │
│ │ │ 14:31:10 Backup process completed successfully     │ │ │
│ │ │ ──────────────────────────────────────────────────── │ │ │
│ │ │ [📋 Copy] [⬇ Download] [🔍 Search in Log]          │ │ │
│ │ └────────────────────────────────────────────────────┘ │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### UI Specifications

**Log Table**:
- Monospace font for consistent timestamp alignment
- Color-coded rows based on execution status
- Hover effects with quick action tooltips
- Sortable by all columns with persistent state

**Filtering Interface**:
- Date range picker with common presets (Today, Last 7 days, etc.)
- Script selector with search/filter capability
- Status multi-select with visual indicators
- Search: Full-text search across log content

**Log Detail Modal**:
- Full-screen option for detailed log analysis
- Syntax highlighting for structured logs
- Line numbers for reference
- Search within log content

**Real-time Features**:
- Auto-refresh toggle with interval selection
- Live update indicators for running executions
- WebSocket connection for real-time log streaming
- Visual notification for new log entries

**Export Functionality**:
- CSV export with current filter criteria
- Date range selection for export
- Progress indicator for large exports
- Email delivery option for scheduled exports

**Accessibility**:
- Log content: Proper contrast for readability
- Table navigation: Keyboard shortcuts
- Modal: Focus management and screen reader support
- Auto-refresh: Pause on focus for accessibility

---

## 6. Schedule Management

### Wireframe (ASCII)
```
┌─────────────────────────────────────────────────────────────┐
│ ScriptFlow    Scripts  Schedules  Logs  Settings     User ▼ │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ ┌─ Schedule Management ───────────────────────────────────┐ │
│ │                                                         │ │
│ │ [➕ New Schedule]  View: [📅 Calendar] [📋 List]      │ │
│ │                                                         │ │
│ │ ┌─ Active Schedules ─────────────────────────────────┐  │ │
│ │ │                                                    │  │ │
│ │ │☑ Script          │Schedule │Next Run    │Last │⚙   │  │ │
│ │ │──────────────────┼─────────┼───────────┼─────┼────│  │ │
│ │ │☑●backup_daily.py │Daily 22:00│in 7h 30m │● OK │ ⋮  │  │ │
│ │ │☑●cleanup.bat     │Mon-Fri 9AM│Tomorrow  │● ERR│ ⋮  │  │ │
│ │ │☑●report_gen.py   │Weekly Sun │in 3 days │● OK │ ⋮  │  │ │
│ │ │☑⚪monitor.py      │Hourly     │in 45m    │● OK │ ⋮  │  │ │
│ │ │☑⚪sync_files.bat  │Manual only│-         │● OK │ ⋮  │  │ │
│ │ │                 │         │          │     │    │  │ │
│ │ └────────────────────────────────────────────────────┘  │ │
│ │                                                         │ │
│ │ ┌─ Quick Stats ──────────────────────────────────────┐  │ │
│ │ │ Active: 4  │  Disabled: 1  │  Next: 45m  │  Avg/day: 12 │ │
│ │ └────────────────────────────────────────────────────┘  │ │
│ │                                                         │ │
│ │ Bulk Actions: [⏸ Pause] [▶ Activate] [🗑 Delete]      │ │
│ │                                                         │ │
│ └─────────────────────────────────────────────────────────┘ │
│                                                             │
│ ┌─ Schedule Editor Modal ─────────────────────────────────┐ │
│ │ Edit Schedule - backup_daily.py           [✕ Close]    │ │
│ │ ───────────────────────────────────────────────────────── │ │
│ │ ┌─ Basic Settings ───────────────────────────────────┐  │ │
│ │ │ Status: ● Active  ⚪ Disabled                       │  │ │
│ │ │ Script: [backup_daily.py            ▼]            │  │ │
│ │ │ Description: [Daily backup automation           ] │  │ │
│ │ └───────────────────────────────────────────────────┘  │ │
│ │                                                         │ │
│ │ ┌─ Schedule Pattern ─────────────────────────────────┐  │ │
│ │ │ Frequency: ● Daily  ⚪ Weekly  ⚪ Monthly  ⚪ Custom│  │ │
│ │ │                                                   │  │ │
│ │ │ Time: [22] : [00]  Timezone: [UTC-5    ▼]        │  │ │
│ │ │                                                   │  │ │
│ │ │ ┌─ Preview ────────────────────────────────────┐   │  │ │
│ │ │ │ Next 5 executions:                          │   │  │ │
│ │ │ │ • Today 22:00 (in 7h 30m)                   │   │  │ │
│ │ │ │ • Tomorrow 22:00                            │   │  │ │
│ │ │ │ • Wed Jan 16 22:00                          │   │  │ │
│ │ │ │ • Thu Jan 17 22:00                          │   │  │ │
│ │ │ │ • Fri Jan 18 22:00                          │   │  │ │
│ │ │ └─────────────────────────────────────────────┘   │  │ │
│ │ └───────────────────────────────────────────────────┘  │ │
│ │                                                         │ │
│ │ ┌─ Notifications ────────────────────────────────────┐  │ │
│ │ │ ☑ Email on failure  ☑ Daily summary               │  │ │
│ │ │ Recipients: [admin@company.com; it@company.com   ] │  │ │
│ │ └───────────────────────────────────────────────────┘  │ │
│ │                                                         │ │
│ │ [Cancel]      [Test Run]               [Save Schedule] │ │
│ └─────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### UI Specifications

**Schedule List**:
- Status indicators: Green dot (active), Gray dot (disabled)
- Next run: Relative time with precise timestamp on hover
- Last execution: Status with quick log access
- Drag-and-drop reordering for priority management

**Calendar View** (Alternative):
- Monthly calendar with execution dots on dates
- Color coding: Green (successful), Red (failed), Yellow (running)
- Click dates to see scheduled executions
- Navigation between months with keyboard support

**Schedule Editor**:
- Progressive disclosure: Show relevant options based on frequency
- Real-time preview of next executions
- Timezone handling with user preference
- Test run functionality with immediate feedback

**Quick Actions**:
- Bulk operations with confirmation dialogs
- Pause/Resume toggle with visual feedback
- Delete confirmation with impact warning
- Export schedule configuration

**Statistics Dashboard**:
- Execution frequency charts
- Success rate trends
- Resource utilization patterns
- Performance benchmarks

**Accessibility**:
- Schedule status: Text + visual indicators
- Time input: Accessible time pickers
- Calendar navigation: Keyboard support
- Form validation: Immediate error feedback

---

## Global UI Components

### Navigation Component
```
┌─────────────────────────────────────────────────────────────┐
│ [🔧 ScriptFlow]  Dashboard  Scripts  Schedules  Logs       │
│                                                    [User ▼] │
└─────────────────────────────────────────────────────────────┘
```

**Specifications**:
- Fixed header: 60px height, z-index: 1000
- Logo: Clickable home link with keyboard focus
- Active state: Underline + bold text
- User menu: Avatar + dropdown with logout
- Mobile: Hamburger menu with slide-out navigation

### Status Indicators
- **Success**: ● Green circle (#27AE60) + "Success" text
- **Error**: ● Red circle (#E74C3C) + "Failed" text  
- **Running**: ● Orange circle (#F39C12) + "Running" text
- **Disabled**: ● Gray circle (#95A5A6) + "Disabled" text

### Button System
- **Primary**: Blue background, white text, 4px border-radius
- **Secondary**: White background, blue border and text
- **Danger**: Red background, white text for destructive actions
- **Ghost**: Transparent background for tertiary actions
- **Sizes**: Small (32px), Medium (40px), Large (48px)

### Form Elements
- **Inputs**: 40px height, 4px border-radius, focus outline
- **Textareas**: Min 80px height, auto-resize capability
- **Selects**: Custom styling matching input appearance
- **Checkboxes/Radios**: 20px touch targets with custom styling

### Modal System
- **Backdrop**: rgba(0,0,0,0.5) with click-to-close
- **Container**: White background, 8px border-radius, shadow
- **Sizes**: Small (400px), Medium (600px), Large (800px), Full-screen
- **Animation**: 200ms slide-in from top

### Loading States
- **Buttons**: Spinner + disabled state + "Loading..." text
- **Tables**: Skeleton rows with shimmer animation
- **Pages**: Full-page spinner with ScriptFlow logo
- **Forms**: Field-level validation with immediate feedback

---

## Responsive Behavior

### Desktop (≥1024px) - Primary Experience
- Full table layouts with all columns visible
- Side-by-side card layouts for dashboard
- Modal overlays for detailed views
- Hover states and advanced interactions

### Tablet (768px-1023px) - Adapted Experience  
- Stacked cards on dashboard
- Horizontal scrolling for wide tables
- Touch-optimized button sizes (44px minimum)
- Simplified navigation with larger targets

### Mobile (≤767px) - Essential Experience
- Single column layouts
- Simplified tables with priority columns only
- Full-screen modals instead of overlays
- Thumb-friendly navigation and forms

---

## Accessibility Implementation

### WCAG AA Compliance
- **Color Contrast**: 4.5:1 minimum for all text
- **Focus Management**: Visible focus indicators on all interactive elements
- **Keyboard Navigation**: Tab order follows logical sequence
- **Screen Readers**: Proper ARIA labels and descriptions
- **Alternative Text**: Meaningful descriptions for all icons

### Implementation Notes
- Use semantic HTML5 elements (main, nav, section, article)
- Implement skip navigation links
- Ensure all form fields have associated labels
- Provide text alternatives for status indicators
- Test with screen readers (NVDA, JAWS, VoiceOver)
- Implement keyboard shortcuts for common actions

---

## Development Implementation Guide

### CSS Framework Integration
- **Bootstrap 5.x**: Use utility classes where appropriate
- **Custom CSS**: Override Bootstrap variables for brand colors
- **Responsive Utilities**: Leverage Bootstrap's responsive classes
- **Component Library**: Build reusable components for consistency

### JavaScript Requirements
- **Vanilla JS or Alpine.js**: Keep JavaScript minimal for forms
- **No SPA Framework**: Server-side rendered templates with progressive enhancement
- **WebSocket**: For real-time log streaming and status updates
- **Form Validation**: Client-side validation with server-side backup

### Performance Considerations
- **Critical CSS**: Inline critical styles, load non-critical async
- **Image Optimization**: Use appropriate formats (WebP where supported)
- **Font Loading**: Use font-display: swap for web fonts
- **Table Performance**: Implement virtual scrolling for large datasets

This comprehensive UX design specification provides a complete foundation for implementing ScriptFlow's user interface that meets all PRD requirements while ensuring professional appearance, optimal usability, and full accessibility compliance. The design prioritizes the form-first approach and table-based data display while maintaining the clean, status-driven interface suitable for system administrators.