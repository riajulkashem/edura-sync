# EduraSync — UI/UX Redesign Blueprint

> A complete visual and interaction design specification for modernising the EduraSync desktop application built with PySide6.

---

## Table of Contents

1. [Design Philosophy](#1-design-philosophy)
2. [Design System](#2-design-system)
   - 2.1 Color Palette
   - 2.2 Typography
   - 2.3 Spacing & Layout Grid
   - 2.4 Elevation & Surfaces
   - 2.5 Icons
3. [Application Shell](#3-application-shell)
4. [Screen Designs](#4-screen-designs)
   - 4.1 Dashboard (Home)
   - 4.2 Devices
   - 4.3 Attendance
   - 4.4 Settings
   - 4.5 About
5. [Component Library](#5-component-library)
6. [Interaction & Motion](#6-interaction--motion)
7. [System Tray Redesign](#7-system-tray-redesign)
8. [First-Run Onboarding Flow](#8-first-run-onboarding-flow)
9. [Notification Design](#9-notification-design)
10. [Accessibility](#10-accessibility)
11. [Implementation Roadmap](#11-implementation-roadmap)

---

## 1. Design Philosophy

### Core Principles

**Calm by default, informative on demand.**
EduraSync runs silently in the background for most of its life. The UI should feel uncluttered and confident at rest, with rich detail available on demand — not dumped in one overwhelming screen.

**Trust through feedback.**
Syncing attendance data is mission-critical for schools and institutions. Every action must have a clear, immediate response: what happened, whether it succeeded, and what to do if it didn't.

**Flat and purposeful.**
No gradients. No decorative shadows. No rainbow colour. Colour is reserved for status signals (online/offline, success/error) and a single accent. Everything else is neutral.

**Respect the operating system.**
The app lives in the Windows and macOS ecosystem. It should feel native — use system fonts, respect system dark/light mode, and behave like a tray app that is politely invisible until needed.

---

## 2. Design System

### 2.1 Color Palette

The palette has three tiers: **background**, **surface**, and **accent**. All values are defined as PySide6 `QPalette` roles or stylesheet tokens so they automatically adapt to system dark/light mode.

#### Light Mode

| Token | Hex | Usage |
|-------|-----|-------|
| `bg-base` | `#F8F9FA` | Application window background |
| `bg-surface` | `#FFFFFF` | Cards, panels, inputs |
| `bg-subtle` | `#F1F3F5` | Alternating rows, inactive headers |
| `border` | `#DEE2E6` | Dividers, input borders |
| `text-primary` | `#212529` | Body text, labels |
| `text-secondary` | `#6C757D` | Timestamps, hints, captions |
| `text-disabled` | `#ADB5BD` | Disabled controls |
| `accent` | `#228BE6` | Primary buttons, links, active tabs |
| `accent-hover` | `#1C7ED6` | Button hover state |
| `accent-muted` | `#E7F5FF` | Accent background (selected rows) |
| `success` | `#2F9E44` | Online status, sync success |
| `success-bg` | `#EBFBEE` | Success badge background |
| `warning` | `#E67700` | Partial device status |
| `warning-bg` | `#FFF9DB` | Warning badge background |
| `danger` | `#C92A2A` | Errors, destructive actions |
| `danger-bg` | `#FFF5F5` | Error badge background |

#### Dark Mode

| Token | Hex | Usage |
|-------|-----|-------|
| `bg-base` | `#1A1B1E` | Application window background |
| `bg-surface` | `#25262B` | Cards, panels, inputs |
| `bg-subtle` | `#2C2E33` | Alternating rows, inactive headers |
| `border` | `#373A40` | Dividers, input borders |
| `text-primary` | `#C1C2C5` | Body text, labels |
| `text-secondary` | `#868E96` | Timestamps, hints |
| `accent` | `#4DABF7` | Primary buttons, links, active tabs |
| `success` | `#51CF66` | Online status |
| `warning` | `#FFD43B` | Warning status |
| `danger` | `#FF6B6B` | Error status |

> **Implementation note:** Define all tokens in a `theme.py` module and apply them via `QApplication.setPalette()` + a single global stylesheet. Detect system preference using `QStyleHints.colorScheme()` (Qt 6.5+) or fall back to `QPalette.window().color().lightness()`.

---

### 2.2 Typography

Use the system default UI font stack — the same font the OS uses for its own controls.

```
Windows : "Segoe UI", sans-serif
macOS   : -apple-system, "SF Pro Text", sans-serif
Linux   : "Ubuntu", "Cantarell", sans-serif
```

#### Type Scale

| Role | Size | Weight | Line height | Usage |
|------|------|--------|-------------|-------|
| `heading-xl` | 20px | 600 | 1.3 | Screen titles |
| `heading-lg` | 16px | 600 | 1.3 | Section headers, group labels |
| `heading-md` | 13px | 600 | 1.4 | Card titles, column headers |
| `body` | 12px | 400 | 1.5 | All body text |
| `body-sm` | 11px | 400 | 1.5 | Captions, table cells, metadata |
| `mono` | 11px | 400 | 1.5 | IP addresses, IDs, log lines |

---

### 2.3 Spacing & Layout Grid

Use a **4 px base unit** throughout.

| Token | Value | Usage |
|-------|-------|-------|
| `space-xs` | 4px | Icon gaps, inline padding |
| `space-sm` | 8px | Between related items |
| `space-md` | 12px | Intra-section padding |
| `space-lg` | 16px | Between sections |
| `space-xl` | 24px | Between major layout regions |
| `space-2xl` | 32px | Page margin |
| `radius-sm` | 4px | Badges, small buttons |
| `radius-md` | 6px | Cards, inputs, buttons |
| `radius-lg` | 8px | Panels, dialogs |

**Window minimum size:** 960 × 640 px (resizable; sidebar is fixed at 200px).

---

### 2.4 Elevation & Surfaces

No box shadows. Elevation is expressed through **background contrast** and **borders only**.

| Level | Background | Border | Usage |
|-------|-----------|--------|-------|
| 0 — Base | `bg-base` | none | Window background |
| 1 — Surface | `bg-surface` | 1px `border` | Cards, panels |
| 2 — Raised | `bg-surface` | 1px `border`, left 2px `accent` stripe | Selected sidebar item, focus card |
| 3 — Overlay | `bg-surface` | 1px `border` | Dialogs, dropdowns |

---

### 2.5 Icons

Use **[Phosphor Icons](https://phosphoricons.com/)** — SVG-based, MIT licensed, available as Python bindings or rendered to `QPixmap` at build time.

Preferred weight: **Regular** (24×24 viewport, 1.5px stroke) for toolbar. **Bold** (20×20) for status indicators.

All icons are **monochrome** and inherit the current text color via `color: inherit` or `QPainter` fill. Never use colored icons except for status indicators (success/warning/danger).

---

## 3. Application Shell

### Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  ╔══════╗  EduraSync                        ● Online  [─][□][✕] │  ← Title bar
│  ╚══════╝                                                        │
├──────────┬──────────────────────────────────────────────────────┤
│          │                                                        │
│ Sidebar  │  Content Area (scrollable)                            │
│ 200px    │                                                        │
│          │                                                        │
│          │                                                        │
│          │                                                        │
│          │                                                        │
├──────────┴──────────────────────────────────────────────────────┤
│  Status bar: current operation or "Ready"           v1.0.0      │  ← Status bar
└─────────────────────────────────────────────────────────────────┘
```

### Sidebar

Replace the top tab bar with a **persistent vertical sidebar**. This scales better as screens are added and is the standard pattern for desktop management tools (VS Code, Notion, Figma).

```
┌─────────────┐
│ [Logo]      │
│             │
│ ▐ Dashboard │  ← Active (left accent stripe, accent-muted bg)
│   Devices   │
│   Attendance│
│   Settings  │
│             │
│  ──────     │
│   About     │
└─────────────┘
```

**Sidebar item anatomy:**
- 36px tall, full-width, 12px horizontal padding
- 16px icon + 8px gap + label text (body weight 500)
- Active state: `bg-subtle`, 2px left border in `accent`
- Hover state: `bg-subtle`
- No tooltips needed (labels always visible)

### Status Indicator (Title Bar)

A small pill in the top-right of the window content area shows the global system state:

| State | Color | Label |
|-------|-------|-------|
| All devices online | `success` | `● All Online (3/3)` |
| Partial | `warning` | `◐ Partial (2/3)` |
| All offline | `danger` | `○ Offline` |
| Operation running | `accent` (animated) | `↻ Syncing…` |

**Implementation:** Connect to `OperationManager` state callbacks + periodic device stats refresh.

### Status Bar (Bottom)

Single line, 24px tall. Left side shows the current operation message (`Fetching device logs…`) or `Ready`. Right side shows `vX.Y.Z`. No progress bar — use inline progress within the content area instead.

---

## 4. Screen Designs

### 4.1 Dashboard (Home)

**Purpose:** At-a-glance health check. "Is everything working?"

```
Dashboard
─────────────────────────────────────────────────────────────

  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
  │ 3        │  │ 2        │  │ 1,247    │  │ 83       │
  │ Devices  │  │ Online   │  │ Users    │  │ Pending  │
  └──────────┘  └──────────┘  └──────────┘  └──────────┘

  ── Last Activity ───────────────────────────────────────────
  Last synced   Today, 08:00        ↑ Cloud upload  ✓ Success
  Last pulled   Today, 08:00        ↓ Device pull   ✓ Success

  ── Devices ─────────────────────────────────────────────────
  IP Address          Model       Status      Users   Last seen
  192.168.1.100       K40         ● Online    412     2 min ago
  192.168.1.101       ZK9500      ● Online    403     2 min ago
  192.168.1.102       F22         ○ Offline   432     3 hrs ago

  ── Quick Actions ───────────────────────────────────────────
  [↓ Fetch Logs]  [↑ Upload]  [↔ Full Sync]  [👤 Sync Users]
```

**Design notes:**
- Four `Stat` cards at the top: Devices total, Online, Total Users, Pending uploads.
- "Online" card uses `success` tone, "Pending" uses `warning` if > 0 else neutral.
- Last Activity row shows `last_sync` / `last_post` from the Settings model — surfacing data that already exists but was never shown.
- Devices table is **read-only** here. Click a row → navigate to the Devices screen with that device selected.
- Quick Actions: icon + label buttons, full-width, 40px tall, `accent` style. They are **disabled with a spinner** while `OperationManager` holds a lock. The spinner replaces the icon in-place (no separate loading screen).

---

### 4.2 Devices Screen

**Purpose:** Manage ZKTeco machines and inspect their live data.

**Layout:** Two-column split (40 / 60).

```
Devices                                          [+ Add Machine]
─────────────────────────────────────────────────────────────────
┌──────────────────────┬──────────────────────────────────────────┐
│ MACHINES (3)         │  192.168.1.102 — K40                     │
│ ──────────────────── │  ○ Offline — Failed 3h ago               │
│ 192.168.1.100  ● K40 │  ─────────────────────────────────────── │
│ 192.168.1.101  ● ZK9 │  [Connect] [Test] [Reset] [Remove]       │
│ 192.168.1.102  ○ K40 │                                          │
│  ← selected          │  [Users]  [Attendance]  [Info]           │
│                      │  ───────────────────────────────────────  │
│                      │  Users (412)              [+ Add User]   │
│                      │  Cloud ID  Name      Role  Card  ⋯       │
│                      │  7596      Ali Hassan User  4829  ⋯       │
│                      │  7597      Sara Mim  User  0     ⋯       │
└──────────────────────┴──────────────────────────────────────────┘
```

**Left panel — Machine list:**
- Compact rows: IP + model name + status dot.
- Selected row has left accent stripe.
- `[+ Add Machine]` in the top-right corner of the panel header (not the screen header).

**Right panel — Device detail:**
- Header: large IP + model, status badge (Online / Offline + time since last contact).
- Four action buttons in a horizontal row — **Connect** (accent), **Test** (secondary), **Reset** (danger-outlined), **Remove** (danger-outlined).
  - **Reset** and **Remove** require confirmation dialogs.
  - All actions run in `DeviceConnectionThread` — buttons show an inline spinner during operation.
- Three tabs: **Users**, **Attendance**, **Info**.

**Users sub-tab:**
- Table: Cloud ID | Name | Role | Card Number | Actions (⋯ context menu).
- `[+ Add User]` top right.
- Each row's `⋯` opens a small dropdown: Edit / Delete (no full dialog re-open from the table — context menu is faster).

**Attendance sub-tab:**
- Table: User Name | Cloud ID | Timestamp | Method | Check Type | Uploaded?.
- Method and Check Type shown as small readable pills (Fingerprint, Check IN, etc.).
- `Uploaded` column: green checkmark / grey dash.
- Sortable columns (click header).

**Info sub-tab:**
- Read-only key/value layout: Firmware, Platform, Serial, Connected At, Last Error.
- "Fetch live info" button that runs a connection test and populates the fields.

---

### 4.3 Attendance Screen

**Purpose:** Review pending and posted records; trigger uploads.

```
Attendance                                [↑ Upload Pending (83)]
─────────────────────────────────────────────────────────────────
Filter: [All Devices ▾]  [All Types ▾]  [Today ▾]   [Search…  ]

  Pending upload: 83 records
  ──────────────────────────────────────────────────────────────
  Name          Cloud ID  Device IP      Time        Type      
  Ali Hassan    7596      192.168.1.100  08:03 AM    Check IN  
  Sara Mim      7597      192.168.1.100  08:07 AM    Check IN  
  …

  ═══ Uploaded ══════════════════════════════════════════════════
  Ali Hassan    7596      192.168.1.100  Yesterday   Check OUT ✓
```

**Design notes:**
- A `Callout` banner at the top when pending > 0: "83 records waiting to upload. [Upload Now]" — disappears after successful upload.
- Separator between pending and uploaded sections — posted records appear below in a secondary section.
- Filters are `QComboBox` dropdowns styled as pills. Date filter: Today / Yesterday / This Week / All.
- Clicking a row shows an expandable bottom drawer with full record detail (status code, punch code, UID, device info).
- Pagination (50 rows per page) with a "Load more" button — never loads the entire table.

---

### 4.4 Settings Screen

**Purpose:** Configure credentials and automation schedule.

```
Settings
─────────────────────────────────────────────────────────────────

  ── Connection ─────────────────────────────────────────────────
  Cloud API URL
  ┌──────────────────────────────────────┐
  │ https://api.edurabd.com              │
  └──────────────────────────────────────┘

  Sync ID
  ┌─────────────────────┐  [Test Connection]
  │ ••••••••••••••••    │
  └─────────────────────┘
  [Show]

  ── Schedule ───────────────────────────────────────────────────
  ┌─┐ Enable automatic daily sync
  └─┘
  Daily sync time  [08:00]

  ── Actions ────────────────────────────────────────────────────
  [Save Settings]

  ── Advanced ─────────────────────────────────────────────────── (collapsible)
  ▼ Danger Zone
    Reset Machine      [Select Machine ▾]  [Reset Machine]
    Flush Local Data   [Flush Database]
```

**Design notes:**
- **Sync ID field** has a password mask toggle `[Show / Hide]` next to the field.
- **Test Connection** button is inline next to the Sync ID field — result shows as a small status badge (✓ Connected / ✗ Failed) that replaces the button text temporarily, then resets.
- **Schedule:** A checkbox enables the `QTimeEdit`. When unchecked, the time picker is greyed out and `sync_time = None` is saved — no more accidental midnight syncs.
- **Advanced / Danger Zone** is behind a collapsible `QGroupBox` that is **collapsed by default**. Users must consciously expand it.
- Destructive buttons (**Reset Machine**, **Flush Database**) use a danger-outlined style and trigger a multi-step confirmation:
  1. Confirmation dialog with impact description.
  2. Password field asking for Sync ID.
  3. Only then the action fires.
- Settings are **auto-validated on blur** (red border + inline error text under the field) so users know about a bad URL before clicking Save.

---

### 4.5 About Screen

```
About
─────────────────────────────────────────────────────────────────

  [Logo — 120×120]

  EduraSync
  Version 1.0.0

  Attendance synchronization system for ZKTeco biometric devices.
  Built by Softzenix Limited.

  ── Developers ─────────────────────────────────────────────────
  Rupan Chakraborty         Riajul Kashem
  +880 1912-884839          +880 1777-824258
  rupan@softzenix.com       riajul@softzenix.com

  ── Links ──────────────────────────────────────────────────────
  [edurabd.com]  [GitHub]  [LinkedIn]

  ── License ────────────────────────────────────────────────────
  MIT License. Open source — see LICENSE file.
```

**Design notes:**
- Logo centered, 120px. Plain `QLabel` with `QPixmap`.
- Developer info in a two-column `QGridLayout` — name, phone (clickable `tel:` link), email (clickable `mailto:` link).
- Links open in the default browser via `QDesktopServices.openUrl()`.
- Replaces the `QTextEdit` (read-only text box) which feels like an afterthought.

---

## 5. Component Library

### Button Variants

All buttons: 32px tall, 8px horizontal padding, `radius-md`, 12px font, 500 weight, no box-shadow.

| Variant | Background | Border | Text | Usage |
|---------|-----------|--------|------|-------|
| Primary | `accent` | none | white | Main CTAs (Save, Upload, Sync) |
| Secondary | `bg-surface` | 1px `border` | `text-primary` | Neutral actions (Refresh, Cancel) |
| Danger | `bg-surface` | 1px `danger` | `danger` | Destructive actions (Reset, Flush) |
| Ghost | transparent | none | `accent` | Inline actions (Show, Learn more) |
| Disabled | `bg-subtle` | none | `text-disabled` | Any disabled state |

**Loading state:** icon is replaced by a 14px spinning circle animation. Label stays visible. Button is non-interactive.

### Status Badge / Pill

Small horizontal pill, 6px v-padding, 10px h-padding, `radius-sm`, 11px font, 600 weight.

| Status | Background | Text |
|--------|-----------|------|
| Online | `success-bg` | `success` |
| Offline | `bg-subtle` | `text-secondary` |
| Error | `danger-bg` | `danger` |
| Pending | `warning-bg` | `warning` |
| Synced | `success-bg` | `success` |

### Input Fields

Height: 32px, `radius-md`, 1px `border`, `bg-surface` background.  
Focus state: 2px `accent` border (no glow).  
Error state: 2px `danger` border + small red label below.

### Cards / Panels

1px `border`, `bg-surface` background, `radius-lg`, 16px internal padding.  
No shadow. Use border contrast against `bg-base` for separation.

### Stat Cards

64px tall, `bg-surface`, 1px `border`, `radius-md`.  
Large number: 28px, 700 weight, `text-primary`.  
Label: 11px, 400 weight, `text-secondary`.  
Optional tone: left 3px border stripe in `success` / `warning` / `danger`.

### Inline Progress

A 4px tall `QProgressBar` placed directly under the action button that triggered the operation — not in the status bar. Visible only during active operations, hidden when idle.

### Confirmation Dialogs

Use a custom `QDialog` (not `QMessageBox`) styled to match the application theme:
- 400px wide, centered on parent window
- `danger` icon (large, 32px) for destructive confirmations
- Title (heading-lg), body text explaining impact
- Two buttons: **Cancel** (secondary) and **Confirm** (danger / primary) — `Cancel` on the left so it is the default
- For destructive ops requiring a password: a labelled input + validation before enabling `Confirm`

---

## 6. Interaction & Motion

### Principles

- Animations are **functional**, not decorative. They communicate state change — not entertainment.
- Maximum duration: **150ms**. Never animate layout shifts.
- Use `QPropertyAnimation` on opacity or max-height only.

### Specific Animations

| Trigger | Animation | Duration |
|---------|-----------|----------|
| Button click | Background color crossfade (hover→active) | 80ms |
| Operation start | Button icon → spinner (opacity fade) | 100ms |
| Status badge update | Opacity: 0→1 | 120ms |
| Sidebar nav | Content area: opacity 0→1 | 120ms |
| Callout appear | Height: 0→auto + opacity 0→1 | 150ms |
| Dialog open | Opacity 0→1 | 100ms |
| Progress bar fill | Smooth increment | native |

### Spinner

A 14px × 14px `QLabel` that cycles through 8 rotation frames (0°, 45°, 90° … 315°) using a `QTimer` at 100ms intervals. Rendered from a single arrow SVG `QPixmap` rotated via `QTransform`. No dependencies.

---

## 7. System Tray Redesign

### Menu Structure

```
─────────────────────────────
  EduraSync                     ← title (non-clickable)
  ● All Online (3/3)            ← live status (non-clickable, updated every 60s)
─────────────────────────────
  Open Dashboard
─────────────────────────────
  Fetch Device Logs
  Upload Attendance
  Full Sync (Fetch + Upload)
  Sync User Profiles
─────────────────────────────
  ✓ Auto-Check (every 60s)      ← checkable, shows current state
─────────────────────────────
  Quit
─────────────────────────────
```

**Design notes:**
- **Single "Full Sync"** item replaces the confusing separate Fetch + Upload items when users want both.
- **Auto-Check** is a single `QAction` with `setCheckable(True)` — a checkmark appears when running. Clicking toggles it. No separate Start/Stop items.
- **Live status line** is a `QAction` with `setEnabled(False)` so it's visible but not clickable. Updated by a `QTimer` every 60 seconds.
- Double-click tray icon → Open Dashboard (cross-platform).

---

## 8. First-Run Onboarding Flow

When the application launches with no saved settings, show a **setup wizard** instead of the default dashboard.

```
Step 1 of 3 — Welcome
─────────────────────────────────────────────────────────────────
  [Logo]

  Welcome to EduraSync

  Let's get you set up in 3 quick steps.
  You'll need your Cloud API URL and Sync ID from your dashboard.

  [Get Started →]
```

```
Step 2 of 3 — Connect to Cloud
─────────────────────────────────────────────────────────────────
  Cloud API URL
  ┌──────────────────────────────────────┐
  │ https://                             │
  └──────────────────────────────────────┘

  Sync ID
  ┌──────────────────────────────────────┐
  │                                      │
  └──────────────────────────────────────┘

  [Test Connection]  → shows ✓ or ✗ inline

  [← Back]  [Next →]  (Next enabled only after successful test)
```

```
Step 3 of 3 — Schedule (Optional)
─────────────────────────────────────────────────────────────────
  Enable daily automatic sync?

  ┌─┐ Yes — sync at  [08:00]  every day
  └─┘ No — I'll sync manually from the tray

  [← Back]  [Finish]
```

After Finish:
- Save settings and close the wizard.
- Trigger `sync_users()` automatically in the background.
- Show the Dashboard with a banner: "First sync in progress…"

---

## 9. Notification Design

### Desktop Notifications (notify-py)

Current notifications fire for almost every operation including debug events. Redesign the notification rules:

| Event | Show? | Type |
|-------|-------|------|
| Full sync completed | Yes | info |
| Upload completed (> 0 records) | Yes | info |
| Device connection error | Yes | warning |
| Auth failure (API 401) | Yes | error (persistent) |
| DB failure at startup | Yes | error (persistent) |
| "No pending records to sync" | No | — (silent, just log) |
| Device check completed (all ok) | No | — (silent) |
| Individual user fetch / save | No | — (silent) |

**Notification format:**
```
EduraSync
Attendance uploaded — 83 records synced successfully.
```
Title is always `EduraSync`. Message is a single plain-English sentence. No technical IDs or stack traces in the notification body.

---

## 10. Accessibility

- All interactive elements must be reachable via **Tab** key in logical order.
- `QToolTip` on every icon-only button (`setToolTip()`).
- Minimum contrast ratio **4.5:1** for all text vs background (WCAG AA).
- Status icons should **never rely on color alone** — pair color with a symbol (●/◐/○) or label.
- Keyboard shortcuts for primary actions:
  - `Ctrl+Shift+F` — Fetch device logs
  - `Ctrl+Shift+U` — Upload attendance
  - `Ctrl+Shift+S` — Full sync
  - `Ctrl+,` — Open settings
- All dialogs are **modal**, centered on the parent window, and respond to `Escape` (cancel).

---

## 11. Implementation Roadmap

Prioritise by user-facing impact vs implementation effort.

### Phase 1 — Foundation (1–2 days)

- [ ] Extract all hardcoded colors and fonts into `interfaces/gui_pyside6/theme.py`
- [ ] Implement `get_theme()` function that returns a `QPalette` + global stylesheet string based on system dark/light mode
- [ ] Apply theme to `QApplication` at startup
- [ ] Define all spacing constants (`SPACE_SM`, `SPACE_MD`, etc.)
- [ ] Create `StatusBadge(QLabel)` reusable widget

### Phase 2 — Shell (1 day)

- [ ] Replace `QTabWidget` (top tabs) with a vertical sidebar `QListWidget`-based nav
- [ ] Add `QStackedWidget` for content area
- [ ] Add global status indicator pill in top-right (connected to `OperationManager`)
- [ ] Clean up the status bar (remove duplicate progress bar)

### Phase 3 — Dashboard Screen (1 day)

- [ ] Rebuild stat cards using a `QGridLayout` with the new `StatCard` widget
- [ ] Add Last Activity row reading `settings.last_sync` / `settings.last_post`
- [ ] Rebuild device status as a proper `QTableWidget` with status badges
- [ ] Wire Quick Action buttons to `OperationManager` state → disable/enable + spinner

### Phase 4 — Devices Screen (2 days)

- [ ] Build two-column splitter layout
- [ ] Implement machine list (left panel) with status dots
- [ ] Build detail panel with Connect/Test/Reset/Remove buttons running in thread
- [ ] Fix `edit_user()` column indices (already done in bug-fix pass)
- [ ] Add context menu (⋯) per user row for Edit/Delete

### Phase 5 — Attendance Screen (1 day)

- [ ] New dedicated Attendance screen in sidebar
- [ ] Filters (device, type, date range)
- [ ] Paginated table (50 rows + load more)
- [ ] Pending callout banner
- [ ] Expandable row detail drawer

### Phase 6 — Settings & About (1 day)

- [ ] Inline Test Connection result badge
- [ ] Schedule enable/disable checkbox
- [ ] Collapsible Danger Zone group
- [ ] Multi-step destructive confirmation dialogs
- [ ] About screen with clickable developer contact links

### Phase 7 — Onboarding & Notifications (1 day)

- [ ] First-run wizard (3-step `QDialog`)
- [ ] Reduce notification verbosity to the table in Section 9
- [ ] Tray menu restructure (Auto-Check toggle, Full Sync item, live status)

### Phase 8 — Polish (1 day)

- [ ] Spinner widget implementation
- [ ] `QPropertyAnimation` on status badges and callouts
- [ ] Keyboard shortcuts
- [ ] Full keyboard tab-order audit
- [ ] High-DPI icon set verification

---

## File Structure After Redesign

```
interfaces/gui_pyside6/
├── theme.py                  ← NEW: color tokens, palette factory, stylesheet
├── widgets/                  ← NEW: shared reusable widgets
│   ├── __init__.py
│   ├── stat_card.py          ← StatCard widget
│   ├── status_badge.py       ← StatusBadge pill
│   ├── sidebar.py            ← Sidebar navigation
│   ├── spinner.py            ← Spinner animation widget
│   └── confirm_dialog.py     ← Multi-step confirmation dialog
├── screens/                  ← NEW: one file per screen
│   ├── __init__.py
│   ├── dashboard_screen.py
│   ├── devices_screen.py
│   ├── attendance_screen.py
│   ├── settings_screen.py
│   └── about_screen.py
├── onboarding.py             ← NEW: first-run wizard
├── tray.py                   ← existing (refactor tray menu)
├── main_window.py            ← NEW: replaces dashboard.py, owns shell + sidebar
├── device_management.py      ← existing (absorb into devices_screen.py)
├── dashboard_content.py      ← to be retired
├── dashboard_settings.py     ← to be retired
├── dashboard_status.py       ← to be retired
└── gui_utils.py              ← keep, trim dead helpers
```

---

*This document is a living specification. Update it as design decisions are finalised during implementation.*

**Author:** Riajul Kashem — Softzenix Limited  
**Last updated:** April 2026
