import { createBrowserRouter, Navigate } from 'react-router-dom';
import { RootLayout } from '@/layouts/RootLayout';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import LoginPage from '@/pages/auth/LoginPage';
import AuditorDashboardPage from '@/pages/auditor/AuditorDashboardPage';
import { AuditorQueuePage } from '@/pages/auditor/AuditorQueuePage';
import { AuditorCaseWorkspacePage } from '@/pages/auditor/AuditorCaseWorkspacePage';
import { AuditorEvidenceExplorerPage } from '@/pages/auditor/AuditorEvidenceExplorerPage';
import { AuditorFindingReviewPage } from '@/pages/auditor/AuditorFindingReviewPage';
import InstitutionOverviewPage from '@/pages/institution/InstitutionOverviewPage';
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
import AdminOverviewPage from '@/pages/admin/AdminOverviewPage';
import { AdminUsersPage } from '@/pages/admin/AdminUsersPage';
import { AdminTeamsPage } from '@/pages/admin/AdminTeamsPage';
import { AdminRulesPage } from '@/pages/admin/AdminRulesPage';
import { AdminConnectorsPage } from '@/pages/admin/AdminConnectorsPage';
import { AdminHealthPage } from '@/pages/admin/AdminHealthPage';
import { AdminLogsPage } from '@/pages/admin/AdminLogsPage';
import { AdminSettingsPage } from '@/pages/admin/AdminSettingsPage';
import NotFoundPage from '@/pages/common/NotFoundPage';
import { IndexRedirect } from '@/components/auth/IndexRedirect';
import WorkflowHubPage from '@/pages/workflow/WorkflowHubPage';

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
            element: <InstitutionOverviewPage />,
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
        element: <ProtectedRoute requiredRole="ADMIN" />,
        children: [
          {
            index: true,
            element: <Navigate to="/admin/overview" replace />,
          },
          {
            path: 'overview',
            element: <AdminOverviewPage />,
          },
          {
            path: 'users',
            element: <AdminUsersPage />,
          },
          {
            path: 'teams',
            element: <AdminTeamsPage />,
          },
          {
            path: 'rules',
            element: <AdminRulesPage />,
          },
          {
            path: 'connectors',
            element: <AdminConnectorsPage />,
          },
          {
            path: 'health',
            element: <AdminHealthPage />,
          },
          {
            path: 'logs',
            element: <AdminLogsPage />,
          },
          {
            path: 'settings',
            element: <AdminSettingsPage />,
          },
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
