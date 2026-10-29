import { createBrowserRouter, Navigate } from 'react-router-dom';
import { RootLayout } from '@/layouts/RootLayout';
import { ProtectedRoute } from '@/components/auth/ProtectedRoute';
import LoginPage from '@/pages/auth/LoginPage';
import InstitutionOverviewPage from '@/pages/institution/InstitutionOverviewPage';
import InstitutionApplicationsPage from '@/pages/institution/InstitutionApplicationsPage';
import NewApplicationPage from '@/pages/institution/NewApplicationPage';
import { InstitutionDocumentsPage } from '@/pages/institution/InstitutionDocumentsPage';
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
      {
        path: 'institution',
        element: <ProtectedRoute requiredRole="INSTITUTION_USER" />,
        children: [
          {
            index: true,
            element: <Navigate to="/workflow" replace />,
          },
          { path: 'overview', element: <InstitutionOverviewPage /> },
          { path: 'applications', element: <InstitutionApplicationsPage /> },
          { path: 'applications/new', element: <NewApplicationPage /> },
          { path: 'documents', element: <InstitutionDocumentsPage /> },
          { path: '*', element: <Navigate to="/workflow" replace /> },
        ],
      },
      // All case-processing roles use the same scoped workflow dossier.
      // Older workspace URLs resolve to the consolidated role-aware queue.
      { path: 'auditor/*', element: <Navigate to="/workflow" replace /> },
      { path: 'lead/*', element: <Navigate to="/workflow" replace /> },
      { path: 'admin/*', element: <Navigate to="/workflow" replace /> },
      {
        path: '*',
        element: <NotFoundPage />,
      },
    ],
  },
]);
