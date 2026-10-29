import React, { useState } from 'react';
import {
  Users,
  CheckCircle2,
  Search,
} from 'lucide-react';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';

interface UserAccount {
  id: string;
  name: string;
  email: string;
  role: 'INSTITUTION_USER' | 'AUDITOR' | 'LEAD_AUDITOR' | 'ADMIN';
  organization: string;
  status: 'ACTIVE' | 'SUSPENDED';
  lastLogin: string;
}

export const AdminUsersPage: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');

  const users: UserAccount[] = [
    {
      id: 'USR-001',
      name: 'Dr. Anil Sharma',
      email: 'principal@apex.edu.in',
      role: 'INSTITUTION_USER',
      organization: 'Apex Institute of Technology (AICTE ID: 1-10948201)',
      status: 'ACTIVE',
      lastLogin: '2026-10-29 08:30:12',
    },
    {
      id: 'USR-002',
      name: 'Vikram Rao',
      email: 'v.rao@aicte.gov.in',
      role: 'AUDITOR',
      organization: 'Review Team Alpha (Western Regional Office)',
      status: 'ACTIVE',
      lastLogin: '2026-10-29 09:15:44',
    },
    {
      id: 'USR-003',
      name: 'Dr. H. V. Verma',
      email: 'h.verma@aicte.gov.in',
      role: 'LEAD_AUDITOR',
      organization: 'Supervisory Directorate (Western Regional Office)',
      status: 'ACTIVE',
      lastLogin: '2026-10-29 09:45:00',
    },
    {
      id: 'USR-004',
      name: 'Rajesh Mehta',
      email: 'admin.verify@aicte.gov.in',
      role: 'ADMIN',
      organization: 'Central Compliance Bureau HQ (New Delhi)',
      status: 'ACTIVE',
      lastLogin: '2026-10-29 07:55:10',
    },
  ];

  const filteredUsers = users.filter((u) => {
    const q = searchQuery.toLowerCase();
    return (
      u.name.toLowerCase().includes(q) ||
      u.email.toLowerCase().includes(q) ||
      u.role.toLowerCase().includes(q)
    );
  });

  return (
    <div className="space-y-6 max-w-6xl mx-auto pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground mb-1">
            <span>Platform Administration</span>
            <span>/</span>
            <span>User Directory &amp; RBAC</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2.5">
            <Users className="w-6 h-6 text-primary" />
            User Access &amp; Role-Based Access Control
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Statutory accounts mapped to the 4 regulatory roles with institution and review-team isolation
          </p>
        </div>

        <Badge variant="outline" className="font-mono text-xs border-primary/30 text-primary py-1 px-3 self-start sm:self-auto">
          {users.length} Active System Users
        </Badge>
      </div>

      {/* Search */}
      <div className="relative max-w-md">
        <Search className="w-4 h-4 absolute left-3 top-3 text-muted-foreground" />
        <Input
          placeholder="Search by name, email, or role..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-9 text-sm"
        />
      </div>

      {/* Users Table */}
      <div className="rounded-lg border bg-card text-card-foreground shadow-xs overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left border-collapse text-xs">
            <thead>
              <tr className="border-b bg-muted/40 font-semibold text-muted-foreground">
                <th className="py-3 px-4">User Name &amp; Email</th>
                <th className="py-3 px-4">Statutory Role</th>
                <th className="py-3 px-4">Organization / Scope</th>
                <th className="py-3 px-4">Last Activity</th>
                <th className="py-3 px-4">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {filteredUsers.map((user) => (
                <tr key={user.id} className="hover:bg-muted/30 transition-colors">
                  <td className="py-3 px-4">
                    <span className="font-bold text-foreground text-xs block">
                      {user.name}
                    </span>
                    <span className="text-[11px] font-mono text-muted-foreground block">
                      {user.email}
                    </span>
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <Badge
                      variant="outline"
                      className={
                        user.role === 'ADMIN'
                          ? 'border-red-400 text-red-700 bg-red-50 font-mono text-[10px]'
                          : user.role === 'LEAD_AUDITOR'
                          ? 'border-purple-400 text-purple-700 bg-purple-50 font-mono text-[10px]'
                          : user.role === 'AUDITOR'
                          ? 'border-blue-400 text-blue-700 bg-blue-50 font-mono text-[10px]'
                          : 'border-emerald-400 text-emerald-700 bg-emerald-50 font-mono text-[10px]'
                      }
                    >
                      {user.role}
                    </Badge>
                  </td>
                  <td className="py-3 px-4 text-muted-foreground text-xs">
                    {user.organization}
                  </td>
                  <td className="py-3 px-4 font-mono text-muted-foreground text-[11px] whitespace-nowrap">
                    {user.lastLogin}
                  </td>
                  <td className="py-3 px-4 whitespace-nowrap">
                    <div className="flex items-center gap-1 text-emerald-700 font-semibold text-[11px]">
                      <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                      <span>{user.status}</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
export default AdminUsersPage;
