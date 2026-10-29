
---
name: frontend-engineering
description: Defines AIC-Flow frontend architecture, enterprise UI design system, page layouts, role-based navigation, component standards, interactions, accessibility and visual quality. Use when designing or implementing any frontend page or component.
---

# AIC-Flow Frontend Engineering

## 1. Product Design Direction

Build AIC-Flow as a professional enterprise approval-workflow and compliance operations platform.

The interface should resemble a mature government/regulatory case-management product, not:
- A generic admin dashboard template.
- A chatbot-first application.
- A flashy cybersecurity landing page.
- A collection of disconnected cards.
- A minimal prototype with placeholder content.

The application should feel reliable, structured, information-dense and easy to navigate.

Prioritise usability, evidence visibility, clear hierarchy and consistency.

## 2. Technology

Use:
- React
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- Lucide React
- React Router
- TanStack Query
- Recharts
- @xyflow/react for the evidence graph
- PDF.js or a suitable React PDF integration

Use compatible, stable versions and lock dependencies.

Do not introduce another frontend framework.

## 3. Visual Design System

### Overall theme

Use a light enterprise interface.

Primary background:
- Very light neutral/slate.

Sidebar:
- Deep navy or dark indigo.

Main content surfaces:
- White.

Primary action:
- Indigo.

Secondary accent:
- Teal.

Semantic colours:
- Green: verified/satisfied/success.
- Amber: warning/pending/manual review.
- Red: error/expired/critical.
- Grey: neutral/unavailable/inactive.

Do not communicate statuses through colour alone. Always include text labels and appropriate icons.

### Typography

Use Inter or an appropriate readable sans-serif font.

Establish consistent text hierarchy:
- Page titles.
- Section titles.
- Card labels.
- Body text.
- Metadata.
- Helper text.

Avoid oversized headings and unnecessarily large cards.

### Spacing and layout

Use a consistent spacing scale.

- Sidebar has fixed navigation width on desktop.
- Main content occupies available width.
- Use consistent page margins.
- Keep related information grouped.
- Use responsive layouts.
- Avoid horizontal overflow.
- Use subtle borders and restrained shadows.

Avoid excessive rounded cards, decorative gradients and unnecessary animation.

## 4. Common Application Shell

Implement one shared authenticated application shell.

Header:
- AIC-Flow brand.
- Synthetic Demo indicator.
- Academic year context.
- Notifications.
- Current user and role menu.

Sidebar:
- Role-specific navigation.
- Active navigation state.
- Expandable groups only when useful.
- Consistent icons.
- Responsive collapse behaviour.

Content area:
- Breadcrumbs where relevant.
- Page title.
- Short page description.
- Primary page actions.
- Main page content.

Use reusable layouts and components instead of duplicating the shell.

## 5. Mandatory Synthetic Data Indicator

Show a clearly visible SYNTHETIC DATA or DEMO ENVIRONMENT label in the authenticated application.

The interface must never imply that simulated issuer responses or synthetic records are actual AICTE production integrations.

Distinguish:
- SIMULATED
- SANDBOX
- PRODUCTION

These labels must be visible wherever source-verification results are shown.

## 6. Role-Based Navigation

Use four frontend workspaces mapped from the distinct backend permission packages; workspace mapping must never replace backend authorisation.

### Institution User

Navigation:
- Overview
- Applications
- New Application
- Checklist
- Document Center
- Rectification
- Status & Activity
- Reports
- AIC Assist

Applicant views must not expose:
- Internal finding severity.
- Internal reviewer notes.
- Hidden anomaly payloads.
- Internal investigation details.

Show only appropriate correction instructions and applicant-visible statuses.

### Auditor

Navigation:
- Dashboard
- Assigned Queue
- Case Workspace
- Evidence Explorer
- Source Verification
- Finding Review
- Case Activity
- Reports
- AIC Assist

Prioritise quick access to assigned cases and their supporting evidence.

### Lead Auditor

Navigation:
- Overview
- Escalated Queue
- Lead Case Review
- Recommendations
- Inspection Referrals
- Temporal Replay
- Audit History

### Admin

Navigation:
- Overview
- Users & Roles
- Review Teams
- Rule Configuration
- Issuer Connectors
- System Health
- Operational Logs
- Settings

Admin must not automatically gain access to application case content.

Enforce access on the backend, not merely by hiding sidebar links.

## 7. Dashboard Standards

Dashboards should contain useful operational information.

Potential components:
- Metric cards.
- Status distribution charts.
- Verification distribution.
- Pending action lists.
- Recent activity.
- Ageing cases.
- Filterable application tables.

All operational metrics must eventually come from backend APIs.

Do not hardcode numbers or create fake activity merely to make the dashboard look populated.

During UI development, clearly labelled design fixtures may be used temporarily.

Include:
- Loading states.
- Empty states.
- Error states.
- Retry actions.
- Responsive layouts.

## 8. Application and Checklist UI

The application interface must clearly present:

- Application reference.
- Institution.
- Application category.
- Academic year.
- Current revision.
- Application status.
- Checklist progress.

The seven evidence areas must have distinct rows or sections.

Each requirement should show:
- Requirement code.
- Requirement title.
- Applicability.
- Current status.
- Supporting document.
- Applicable rule reference.
- Permitted action.

Differentiate:
- Applicable.
- Not Applicable.
- Pending determination.
- Unable to Determine.
- Satisfied.
- Deficient.
- Under Review.

Do not collapse different requirement states into generic green/red icons.

## 9. Document Center

Create a practical document-management experience.

Include:
- Drag-and-drop upload.
- File selection.
- Accepted format and size guidance.
- Upload progress.
- Processing status.
- Document type.
- Version history.
- SHA-256 display.
- OCR status.
- Extraction summary.
- Document detail view.

The original document must remain immutable.

A replacement upload must create a new version.

Private documents must only be served through authorised backend endpoints.

## 10. Evidence Viewer and Contradiction Explorer

This is one of the most important interface areas.

Design the Evidence Contradiction Explorer as an investigation workspace, not a simple discrepancy table.

Recommended layout:

Left panel:
- Findings list.
- Requirement filters.
- Finding status.
- Severity.

Centre panel:
- PDF document viewer.
- Page navigation.
- Highlighted evidence region.
- Bounding boxes where available.
- Extracted field details.

Right panel:
- Submitted application value.
- Extracted document value.
- Institutional/source value.
- Source freshness.
- Applicable regulatory rule.
- Explanation.
- Evidence references.

Include a relationship graph using @xyflow/react.

Graph nodes should be clickable and represent:
- Application.
- Application revision.
- Document.
- Document version.
- PDF page.
- Extracted field.
- Source record.
- Rule version.
- Validation result.
- Finding.
- Reviewer action.

Selecting a graph node must display its actual related information.

Avoid decorative or fabricated connections.

## 11. Auditor Review UI

Provide clear review actions:
- Accept Flag.
- Dismiss Flag.
- Request Clarification.
- Escalate to Lead.
- Mark Resolved, where permitted.
- Add Note.

Require appropriate rationale where applicable.

Display previous review actions and timestamps.

Never silently modify previous review history.

## 12. Rectification UI

Show the institution user:
- What correction is requested.
- Which requirement needs attention.
- What document or response is permitted.
- Submission status.
- Deadline, when applicable.

Do not display hidden reviewer findings.

The new submission must be represented as a new revision.

## 13. Temporal Replay UI

Provide a clear comparison between:
- Historical validation run.
- Original application revision.
- Pinned rule versions.
- Pinned source-record versions.
- Current source records.
- New validation run.

Make it visually obvious that replay uses the historical inputs rather than silently querying current source data.

## 14. Reports and AIC Assist

Reports:
- Summary information.
- Validation result counts.
- Requirement-level outcomes.
- Applicable rules.
- Evidence references.
- Source verification metadata.
- Generation timestamp.

Provide JSON and PDF download actions through actual backend endpoints.

AIC Assist:
- Simple conversation interface.
- Clear citations.
- Handbook section and page references.
- Retrieval-only indication where appropriate.

Do not let the assistant execute regulatory workflow actions.

## 15. Reusable Components

Create shared components where appropriate:

- AppShell
- Sidebar
- Topbar
- Breadcrumbs
- PageHeader
- MetricCard
- StatusBadge
- DataTable
- FilterBar
- SearchInput
- DocumentUploader
- DocumentPreview
- EvidenceCard
- FindingCard
- Timeline
- ConfirmationDialog
- EmptyState
- ErrorState
- LoadingSkeleton
- NotificationPanel

Avoid duplicating components across role workspaces.

## 16. Interaction Standards

Every visible interactive control must work.

Examples:
- Sidebar links navigate.
- Filters change displayed results.
- Search performs meaningful search.
- Buttons perform their advertised operations.
- Dialogs open and close.
- Forms validate and submit.
- Tables sort and paginate where required.
- Graph nodes open relevant details.
- PDF navigation changes the viewed page.

Never use decorative buttons that do nothing.

Never use frontend-only role checks as security enforcement.

Use TanStack Query or a consistent API integration layer for server communication.

Handle network failures and expired sessions properly.

## 17. Accessibility and Responsive Behaviour

- Use semantic HTML.
- Support keyboard navigation.
- Provide labels for form controls.
- Maintain readable contrast.
- Provide visible focus states.
- Do not rely solely on colour.
- Support standard desktop, laptop and tablet widths.
- Ensure critical tables and evidence tools remain usable at smaller widths.

## 18. Development Workflow

Before creating or modifying a page:

1. Read its corresponding prototype specification section.
2. Check the role and permission boundary.
3. Identify required API data.
4. Reuse the established design system.
5. Implement actual interactions.
6. Verify responsive behaviour.
7. Test success, loading, empty and error states.
8. Check that existing screens remain consistent.

Do not generate the entire frontend in one uncontrolled operation.

Implement pages in logical groups and verify them incrementally.

The final interface should be visually consistent, operationally useful and integrated with the actual backend.
