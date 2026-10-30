import { createBrowserRouter, Navigate } from 'react-router-dom';
import { RootLayout } from '@/layouts/RootLayout';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import LoginPage from '@/pages/auth/LoginPage';
import AuditorDashboardPage from '@/pages/auditor/AuditorDashboardPage';
import { AuditorQueuePage } from '@/pages/auditor/AuditorQueuePage';
import { AuditorCaseWorkspacePage } from '@/pages/auditor/AuditorCaseWorkspacePage';
import { AuditorEvidenceExplorerPage } from '@/pages/auditor/AuditorEvidenceExplorerPage';
import { AuditorFindingReviewPage } from '@/pages/auditor/AuditorFindingReviewPage';
import InstitutionApplicationsPage from '@/pages/institution/InstitutionApplicationsPage';
import NewApplicationPage from '@/pages/institution/NewApplicationPage';
import { InstitutionDocumentsPage } from '@/pages/institution/InstitutionDocumentsPage';
import { InstitutionRectificationPage } from '@/pages/institution/InstitutionRectificationPage';
import { InstitutionReportsPage } from '@/pages/institution/InstitutionReportsPage';
import LeadOverviewPage from '@/pages/lead/LeadOverviewPage';
import { LeadEscalatedQueuePage } from '@/pages/lead/LeadEscalatedQueuePage';
import { LeadCaseReviewPage } from '@/pages/lead/LeadCaseReviewPage';
import { LeadRecommendationsPage } from '@/pages/lead/LeadRecommendationsPage';
import { LeadInspectionReferralsPage } from '@/pages/lead/LeadInspectionReferralsPage';
import { LeadTemporalReplayPage } from '@/pages/lead/LeadTemporalReplayPage';
import { LeadAuditHistoryPage } from '@/pages/lead/LeadAuditHistoryPage';
import { AuditorAssistPage } from '@/pages/auditor/AuditorAssistPage';
import { InstitutionAssistPage } from '@/pages/institution/InstitutionAssistPage';
import { AdminUsersPage } from '@/pages/admin/AdminUsersPage';
import { AdminTeamsPage } from '@/pages/admin/AdminTeamsPage';
import { AdminRulesPage } from '@/pages/admin/AdminRulesPage';
import { AdminConnectorsPage } from '@/pages/admin/AdminConnectorsPage';
import { AdminHealthPage } from '@/pages/admin/AdminHealthPage';
import { AdminLogsPage } from '@/pages/admin/AdminLogsPage';
import { AdminSettingsPage } from '@/pages/admin/AdminSettingsPage';
import NotFoundPage from '@/pages/common/NotFoundPage';
import { AdminIndexRedirect, IndexRedirect } from '@/components/auth/IndexRedirect';
import WorkflowHubPage from '@/pages/workflow/WorkflowHubPage';
import RoleWorkspacePage from '@/pages/workflow/RoleWorkspacePage';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <LoginPage />,
  },
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <RootLayout />
      </ProtectedRoute>
    ),
    children: [
      {
        index: true,
        element: <IndexRedirect />,
      },
      { path: 'workflow', element: <WorkflowHubPage /> },
      // Auditor Routes
      {
        path: 'auditor',
        element: <ProtectedRoute requiredRole="AUDITOR" />,
        children: [
          {
            index: true,
            element: <Navigate to="/auditor/dashboard" replace />,
          },
          {
            path: 'dashboard',
            element: <AuditorDashboardPage />,
          },
          {
            path: 'queue',
            element: <AuditorQueuePage />,
          },
          {
            path: 'case-workspace',
            element: <AuditorCaseWorkspacePage />,
          },
          {
            path: 'evidence-explorer',
            element: <AuditorEvidenceExplorerPage />,
          },
          {
            path: 'source-verification',
            element: <AdminConnectorsPage />,
          },
          {
            path: 'finding-review',
            element: <AuditorFindingReviewPage />,
          },
          {
            path: 'activity',
            element: <LeadAuditHistoryPage />,
          },
          {
            path: 'reports',
            element: <InstitutionReportsPage />,
          },
          {
            path: 'assist',
            element: <AuditorAssistPage />,
          },
        ],
      },
      // Institution Routes
      {
        path: 'institution',
        element: <ProtectedRoute requiredRole="INSTITUTION_USER" />,
        children: [
          {
            index: true,
            element: <Navigate to="/institution/overview" replace />,
          },
          {
            path: 'overview',
            element: <RoleWorkspacePage workspace="institution" section="overview" />,
          },
          {
            path: 'applications',
            element: <InstitutionApplicationsPage />,
          },
          {
            path: 'applications/new',
            element: <NewApplicationPage />,
          },
          {
            path: 'documents',
            element: <InstitutionDocumentsPage />,
          },
          {
            path: 'rectification',
            element: <InstitutionRectificationPage />,
          },
          {
            path: 'activity',
            element: <LeadAuditHistoryPage />,
          },
          {
            path: 'reports',
            element: <InstitutionReportsPage />,
          },
          {
            path: 'assist',
            element: <InstitutionAssistPage />,
          },
          { path: 'obligations', element: <RoleWorkspacePage workspace="institution" section="obligations" /> },
          { path: 'renewals', element: <RoleWorkspacePage workspace="institution" section="renewals" /> },
          { path: 'notifications', element: <RoleWorkspacePage workspace="institution" section="notifications" /> },
        ],
      },
      // Processing Office: distinct Intake and Scrutiny permission packages
      {
        path: 'office',
        element: <ProtectedRoute requiredWorkspace="auditor" />,
        children: [
          { index: true, element: <RoleWorkspacePage workspace="auditor" section="overview" /> },
          { path: ':section', element: <RoleWorkspacePage workspace="auditor" /> },
        ],
      },
      // Regional coordination: region scope remains a backend permission boundary
      {
        path: 'regional',
        element: <ProtectedRoute requiredWorkspace="regional" />,
        children: [
          { index: true, element: <RoleWorkspacePage workspace="regional" section="overview" /> },
          { path: ':section', element: <RoleWorkspacePage workspace="regional" /> },
        ],
      },
      // Committee and EVC participant workspace
      {
        path: 'committee',
        element: <ProtectedRoute requiredWorkspace="committee" />,
        children: [
          { index: true, element: <RoleWorkspacePage workspace="committee" section="overview" /> },
          { path: ':section', element: <RoleWorkspacePage workspace="committee" /> },
        ],
      },
      // Bureau and competent-authority workspace
      {
        path: 'bureau',
        element: <ProtectedRoute requiredWorkspace="lead" />,
        children: [
          { index: true, element: <RoleWorkspacePage workspace="lead" section="overview" /> },
          { path: 'decisions', element: <ProtectedRoute requiredRole="COMPETENT_AUTHORITY"><RoleWorkspacePage workspace="lead" section="decisions" /></ProtectedRoute> },
          { path: ':section', element: <RoleWorkspacePage workspace="lead" /> },
        ],
      },
      // Lead Auditor Routes
      {
        path: 'lead',
        element: <ProtectedRoute requiredRole="LEAD_AUDITOR" />,
        children: [
          {
            index: true,
            element: <Navigate to="/lead/overview" replace />,
          },
          {
            path: 'overview',
            element: <LeadOverviewPage />,
          },
          {
            path: 'escalated-queue',
            element: <LeadEscalatedQueuePage />,
          },
          {
            path: 'case-review',
            element: <LeadCaseReviewPage />,
          },
          {
            path: 'recommendations',
            element: <LeadRecommendationsPage />,
          },
          {
            path: 'inspection-referrals',
            element: <LeadInspectionReferralsPage />,
          },
          {
            path: 'temporal-replay',
            element: <LeadTemporalReplayPage />,
          },
          {
            path: 'audit-history',
            element: <LeadAuditHistoryPage />,
          },
        ],
      },
      // Admin Routes
      {
        path: 'admin',
        element: <ProtectedRoute requiredWorkspace="admin" />,
        children: [
          {
            index: true,
            element: <AdminIndexRedirect />,
          },
          {
            path: 'overview',
            element: <ProtectedRoute requiredRole="ADMIN"><RoleWorkspacePage workspace="admin" section="overview" /></ProtectedRoute>,
          },
          {
            path: 'users',
            element: <ProtectedRoute requiredRole="ADMIN"><AdminUsersPage /></ProtectedRoute>,
          },
          {
            path: 'teams',
            element: <ProtectedRoute requiredRole="ADMIN"><AdminTeamsPage /></ProtectedRoute>,
          },
          {
            path: 'rules',
            element: <ProtectedRoute requiredRole="ADMIN"><AdminRulesPage /></ProtectedRoute>,
          },
          {
            path: 'connectors',
            element: <ProtectedRoute requiredRole="ADMIN"><AdminConnectorsPage /></ProtectedRoute>,
          },
          {
            path: 'health',
            element: <ProtectedRoute requiredRole="ADMIN"><AdminHealthPage /></ProtectedRoute>,
          },
          {
            path: 'logs',
            element: <ProtectedRoute requiredRole="ADMIN"><AdminLogsPage /></ProtectedRoute>,
          },
          {
            path: 'settings',
            element: <ProtectedRoute requiredRole="ADMIN"><AdminSettingsPage /></ProtectedRoute>,
          },
          { path: 'policy/sources', element: <ProtectedRoute requiredRole="REGULATORY_POLICY_PUBLISHER"><RoleWorkspacePage workspace="admin" section="sources" /></ProtectedRoute> },
          { path: 'policy/route-simulator', element: <ProtectedRoute requiredRole="REGULATORY_POLICY_PUBLISHER"><RoleWorkspacePage workspace="admin" section="route-simulator" /></ProtectedRoute> },
          { path: 'policy/deadlines', element: <ProtectedRoute requiredRole="REGULATORY_POLICY_PUBLISHER"><RoleWorkspacePage workspace="admin" section="deadlines" /></ProtectedRoute> },
          { path: 'policy/notifications', element: <ProtectedRoute requiredRole="REGULATORY_POLICY_PUBLISHER"><RoleWorkspacePage workspace="admin" section="notification-policies" /></ProtectedRoute> },
        ],
      },
      // Fallback
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
]);
