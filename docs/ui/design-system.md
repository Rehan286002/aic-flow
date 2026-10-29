
# AIC-Flow — Frontend Design System v1

## 1. Design Identity

Product: AIC-Flow
Category: Enterprise Regulatory Operations Platform
Interface: Professional government/regulatory case-management application.

The interface must communicate:
- Trust.
- Accuracy.
- Traceability.
- Security.
- Operational clarity.
- Regulatory professionalism.

Do not create a generic admin dashboard, chatbot interface, landing-page template or flashy hackathon design.

This document is the authoritative frontend visual specification.

## 2. Overall Theme

Use a LIGHT enterprise theme.

The interface must have:
- Deep navy sidebar.
- White top navigation.
- Very light grey/slate main background.
- Indigo primary actions.
- Teal secondary accents.
- Restrained semantic colours.
- Clear separation between content sections.

Do not automatically switch to dark mode based on the operating system.

## 3. Colour Palette

Use these as the target brand colours.

### Brand

- Primary indigo: #4F46E5
- Primary hover: #4338CA
- Secondary teal: #0F766E
- Secondary light: #CCFBF1

### Navigation

- Sidebar background: #17233B
- Sidebar secondary background: #1E2D49
- Sidebar active background: #293B5D
- Sidebar main text: #F8FAFC
- Sidebar muted text: #B7C3D6

### Application surfaces

- Main background: #F6F8FC
- White surface: #FFFFFF
- Secondary surface: #F8FAFC
- Border: #E2E8F0
- Primary text: #172033
- Secondary text: #64748B
- Muted text: #94A3B8

### Status colours

- Success: #15803D
- Success background: #DCFCE7
- Warning: #B45309
- Warning background: #FEF3C7
- Error: #B91C1C
- Error background: #FEE2E2
- Informational: #1D4ED8
- Information background: #DBEAFE
- Neutral: #475569
- Neutral background: #F1F5F9

Use semantic status labels alongside colours.

Never use colour alone to indicate a result.

Maintain the shadcn CSS variable structure. Map the selected brand colours to the appropriate existing tokens rather than replacing framework variables randomly.

## 4. Typography

## 4. Typography

Use the Geist font family supplied by the Nova preset.

- Geist Sans for application UI.
- Geist Mono for hashes, identifiers and technical references.

Do not introduce Inter or another font family unnecessarily.

Recommended hierarchy:

- Page title: 24–28px, semibold.
- Section title: 16–18px, semibold.
- Card heading: 14–16px, semibold.
- Body: 14px.
- Secondary information: 12–13px.
- Technical identifiers: 12–13px, monospace.

The current shadcn Nova preset has installed Geist fonts.

Use:
- Geist Sans for application UI.
- Geist Mono for hashes, identifiers, technical references and code-like content.

Do not load a second font family unnecessarily.

Recommended hierarchy:

- Page title: 24–28px, semibold.
- Section title: 16–18px, semibold.
- Card heading: 14–16px, semibold.
- Body: 14px.
- Secondary information: 12–13px.
- Technical identifiers: 12–13px, monospace.

Maintain readability and avoid excessively large text.

## 5. Global Application Layout

Desktop structure:

- Expanded sidebar: approximately 250px.
- Collapsed sidebar: approximately 72px.
- Header: approximately 64px high.
- Main content padding: 24–32px.
- Main content fills available horizontal space.

### Header

Include:
- AIC-Flow logo and product name.
- Clearly visible SYNTHETIC DEMO indicator.
- Academic year context: 2026–27.
- Notifications.
- Current user avatar and role.
- Account menu.

### Sidebar

Include:
- Role-specific navigation.
- Lucide icons.
- Clearly highlighted active route.
- Expand/collapse behaviour.
- Consistent navigation spacing.

### Main content

Include:
- Breadcrumbs where appropriate.
- Page title.
- Short page description.
- Primary action.
- Main content area.

Maintain the same shell across all four workspaces.

## 6. Component Design Standards

### Cards
- White backgrounds.
- Subtle borders.
- Approximately 10–12px corner radius.
- Very restrained shadows.
- Consistent internal padding.

### Buttons
- Primary indigo.
- Secondary neutral.
- Destructive red only when appropriate.
- Consistent 36–40px height.
- Distinguishable disabled and loading states.

### Inputs
- Consistent border and height.
- Visible focus ring.
- Labels and helpful validation messages.
- Clear error states.

### Tables
- Compact enterprise layout.
- Clear header row.
- Consistent row heights.
- Subtle row separators.
- Useful filters and search.
- Pagination when required.
- Proper empty and loading states.

### Dialogs
- Clear title and purpose.
- Appropriate confirmation.
- Consistent footer actions.

### Status badges
Use text labels with semantic colours.
Keep them compact and consistent.

## 7. Dashboard Design

The dashboard should prioritise useful operational data.

Use:
- Metric cards.
- Charts.
- Recent applications.
- Pending work.
- Ageing cases.
- Recent activity.
- Source verification status.

Charts should be restrained and readable.

Do not use unnecessary charts merely to fill space.

All production-style metrics must come from backend data.

During design development, clearly labelled synthetic fixtures are acceptable.

## 8. Evidence Contradiction Explorer

This is a signature AIC-Flow feature and must receive special design attention.

Use a three-panel investigation layout.

### Left panel
- Findings list.
- Requirement filters.
- Status and severity.
- Selected finding.

### Centre panel
- PDF document viewer.
- Page navigation.
- Highlighted evidence.
- Bounding boxes.
- Extracted field information.

### Right panel
- Submitted application value.
- Extracted document value.
- Synthetic source value.
- Source freshness.
- Applicable rule and version.
- Finding explanation.
- Review status.

Provide an interactive relationship graph with @xyflow/react.

Graph nodes must represent actual persisted relationships.

Clicking a document, page, field, source or rule node should open the corresponding details.

Do not create decorative evidence relationships.

## 9. Role-Based Visual Consistency

All role packages and their four mapped UI workspaces must use the same visual language.

Institution User:
Applicant-oriented, guided and clear.

Auditor:
Information-dense evidence investigation and case review.

Lead Auditor:
Escalation, historical review and recommendation-oriented.

Admin:
Configuration and operational monitoring.

Do not create unrelated visual themes for different roles.

## 10. Responsive Behaviour

Desktop:
Full sidebar, header and content layout.

Tablet:
Collapsible sidebar and adaptive content panels.

Smaller screens:
Stacked content, responsive tables and accessible navigation.

Evidence Explorer:
Convert side panels into tabs, drawers or stacked sections on narrower displays.

Never allow important information to disappear because of insufficient viewport width.

## 11. Motion and Interaction

Use subtle transitions only.

Support:
- Hover states.
- Focus states.
- Loading indicators.
- Toast notifications.
- Confirmation dialogs.
- Tooltips.
- Empty states.
- Error states.

Avoid excessive gradients, glowing effects, animated backgrounds and decorative motion.

## 12. Design Acceptance

Before declaring the design system complete:

- Consistent colours.
- Consistent typography.
- Consistent spacing.
- Consistent cards and inputs.
- Responsive navigation.
- Reusable components.
- Accessible contrast.
- Proper loading/error states.
- Functional interactions.

Every page must look as though it belongs to the same AIC-Flow application.

The visual design must serve evidence review and regulatory operations rather than distracting from them.
