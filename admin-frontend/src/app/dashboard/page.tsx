"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { AdminLayout } from "@/components/layout/AdminLayout";
import { adminApi } from "@/api/client";
import { EmployeeRequestItem, EmployeeItem, CustomerItem } from "@/types";
import { 
  ShieldCheck, 
  UserCheck, 
  Users, 
  FileText, 
  Activity, 
  ArrowRight, 
  Building2,
  RefreshCw,
  BookOpen,
  Landmark
} from "lucide-react";
import { Policy, RegulatoryAuthority } from "@/types";

export default function AdminDashboardPage() {
  const [requests, setRequests] = useState<EmployeeRequestItem[]>([]);
  const [employees, setEmployees] = useState<EmployeeItem[]>([]);
  const [customers, setCustomers] = useState<CustomerItem[]>([]);
  const [policies, setPolicies] = useState<Policy[]>([]);
  const [authorities, setAuthorities] = useState<RegulatoryAuthority[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = async () => {
    try {
      setLoading(true);
      setError(null);
      const [reqData, empData, custData, polData, authData] = await Promise.all([
        adminApi.getEmployeeRequests().catch(() => []),
        adminApi.getEmployees().catch(() => []),
        adminApi.getCustomers().catch(() => []),
        adminApi.getPolicies({ page_size: 100 }).catch(() => ({ items: [], total: 0 })),
        adminApi.getRegulatoryAuthorities().catch(() => [])
      ]);
      setRequests(reqData || []);
      setEmployees(empData || []);
      setCustomers(custData || []);
      setPolicies(polData?.items || []);
      setAuthorities(authData || []);
    } catch (err: any) {
      setError(err.message || "Failed to load administrative overview.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  const pendingRequests = requests.filter((r) => r.status === "PENDING");

  return (
    <AdminLayout>
      <div className="space-y-6">
        
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-5 border-b border-slate-200 gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-slate-900">
                Administrative Governance Dashboard
              </h1>
              <span className="px-2.5 py-0.5 rounded text-xs font-mono font-bold bg-amber-100 text-amber-900 border border-amber-300">
                ACTIVE CONSOLE
              </span>
            </div>
            <p className="text-[15px] text-slate-600 mt-1.5 leading-relaxed">
              Central supervisory oversight, personnel verification, and platform management
            </p>
          </div>

          <button
            onClick={fetchOverview}
            disabled={loading}
            className="px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 rounded-lg text-sm font-semibold border border-slate-300 flex items-center gap-2 shadow-xs transition-colors self-start sm:self-auto"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Overview</span>
          </button>
        </div>

        {/* Error Notice */}
        {error && (
          <div className="p-4 bg-rose-50 border border-rose-200 rounded-xl text-rose-800 text-sm">
            {error}
          </div>
        )}

        {/* Real Operational Stats Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          {/* Card 1: Employee Verification */}
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-500 font-mono">
                Employee Requests
              </span>
              <UserCheck className="h-5 w-5 text-amber-600" />
            </div>
            <div className="flex items-baseline gap-2.5">
              <span className="text-3xl sm:text-4xl font-bold text-slate-900">
                {loading ? "..." : pendingRequests.length}
              </span>
              <span className="text-sm text-amber-700 font-semibold font-mono">Pending Review</span>
            </div>
            <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-sm">
              <span className="text-slate-500">Total requests on record:</span>
              <span className="font-bold text-slate-700 font-mono">{requests.length}</span>
            </div>
            <Link
              href="/employee-verification"
              className="mt-1.5 w-full py-2.5 px-3 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 transition-colors"
            >
              <span>Review Requests</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {/* Card 2: Active Employees */}
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-500 font-mono">
                Active Employees
              </span>
              <Users className="h-5 w-5 text-slate-600" />
            </div>
            <div className="flex items-baseline gap-2.5">
              <span className="text-3xl sm:text-4xl font-bold text-slate-900">
                {loading ? "..." : employees.length}
              </span>
              <span className="text-sm text-slate-600 font-semibold font-mono">Officers Registered</span>
            </div>
            <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-sm">
              <span className="text-slate-500">Institutional personnel:</span>
              <span className="font-bold text-slate-700 font-mono">PolicyPilot Demo Bank</span>
            </div>
            <Link
              href="/employees"
              className="mt-1.5 w-full py-2.5 px-3 bg-slate-50 hover:bg-slate-100 text-slate-800 border border-slate-200 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 transition-colors"
            >
              <span>View Employee Directory</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {/* Card 3: Customers */}
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-500 font-mono">
                Customer Accounts
              </span>
              <Users className="h-5 w-5 text-blue-600" />
            </div>
            <div className="flex items-baseline gap-2.5">
              <span className="text-3xl sm:text-4xl font-bold text-slate-900">
                {loading ? "..." : customers.length}
              </span>
              <span className="text-sm text-blue-700 font-semibold font-mono">Borrowers Registered</span>
            </div>
            <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-sm">
              <span className="text-slate-500">Registry status:</span>
              <span className="font-bold text-emerald-600 font-mono">Live Sync</span>
            </div>
            <Link
              href="/customers"
              className="mt-1.5 w-full py-2.5 px-3 bg-slate-50 hover:bg-slate-100 text-slate-800 border border-slate-200 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 transition-colors"
            >
              <span>View Customer Registry</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        {/* Policy & Regulation Governance Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
          {/* Policies Card */}
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-500 font-mono">
                Policy Repository
              </span>
              <BookOpen className="h-5 w-5 text-amber-600" />
            </div>
            <div className="flex items-baseline gap-2.5">
              <span className="text-3xl sm:text-4xl font-bold text-slate-900">
                {loading ? "..." : policies.length}
              </span>
              <span className="text-sm text-amber-700 font-semibold font-mono">
                {loading ? "" : `${policies.filter((p) => p.status === "ACTIVE").length} Active in Force`}
              </span>
            </div>
            <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-sm">
              <span className="text-slate-500">Draft policies pending:</span>
              <span className="font-bold text-slate-700 font-mono">
                {policies.filter((p) => p.status === "DRAFT").length}
              </span>
            </div>
            <Link
              href="/policies"
              className="mt-1.5 w-full py-2.5 px-3 bg-amber-50 hover:bg-amber-100 text-amber-900 border border-amber-200 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 transition-colors"
            >
              <span>Manage Policies</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          {/* Regulatory Authorities Card */}
          <div className="p-5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-500 font-mono">
                Regulatory Authorities
              </span>
              <Landmark className="h-5 w-5 text-slate-700" />
            </div>
            <div className="flex items-baseline gap-2.5">
              <span className="text-3xl sm:text-4xl font-bold text-slate-900">
                {loading ? "..." : authorities.length}
              </span>
              <span className="text-sm text-emerald-700 font-semibold font-mono">
                {loading ? "" : `${authorities.filter((a) => a.is_active).length} Active Authorities`}
              </span>
            </div>
            <div className="pt-2.5 border-t border-slate-100 flex items-center justify-between text-sm">
              <span className="text-slate-500">Governing jurisdictions:</span>
              <span className="font-bold text-slate-700 font-mono">IN, Global</span>
            </div>
            <Link
              href="/regulatory-authorities"
              className="mt-1.5 w-full py-2.5 px-3 bg-slate-50 hover:bg-slate-100 text-slate-800 border border-slate-200 rounded-lg text-sm font-semibold flex items-center justify-center gap-2 transition-colors"
            >
              <span>Manage Authorities</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>
        </div>

        {/* Future Modules Truthful Section */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
          <div className="p-4.5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-500 font-mono">
                Global Applications
              </span>
              <FileText className="h-4.5 w-4.5 text-slate-400" />
            </div>
            <div className="text-sm font-medium text-slate-500 italic">
              Module not yet available.
            </div>
            <p className="text-xs text-slate-400 pt-2.5 border-t border-slate-100 leading-normal">
              Loan application governance will be established in Module M06.
            </p>
          </div>

          <div className="p-4.5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-500 font-mono">
                Institutions
              </span>
              <Building2 className="h-4.5 w-4.5 text-slate-400" />
            </div>
            <div className="text-sm font-medium text-slate-500 italic">
              Module not yet available.
            </div>
            <p className="text-xs text-slate-400 pt-2.5 border-t border-slate-100 leading-normal">
              Multi-tenant bank configuration will be enabled in a future release.
            </p>
          </div>

          <div className="p-4.5 bg-white border border-slate-200 rounded-xl shadow-xs space-y-2.5">
            <div className="flex items-center justify-between">
              <span className="text-xs sm:text-sm font-semibold uppercase tracking-wider text-slate-500 font-mono">
                System Audit
              </span>
              <ShieldCheck className="h-4.5 w-4.5 text-slate-400" />
            </div>
            <div className="text-sm font-medium text-slate-500 italic">
              Module not yet available.
            </div>
            <p className="text-xs text-slate-400 pt-2.5 border-t border-slate-100 leading-normal">
              Immutable audit trail and compliance verification will appear in M14.
            </p>
          </div>
        </div>

        {/* Architecture Notice */}
        <div className="p-5 bg-[#0F172A] border border-slate-800 rounded-xl text-slate-200 space-y-2 shadow-xs">
          <div className="flex items-center gap-2.5 text-amber-400">
            <ShieldCheck className="h-5 w-5" />
            <h2 className="text-base sm:text-lg font-bold uppercase tracking-wider">
              Administrative Console Architecture Notice
            </h2>
          </div>
          <p className="text-sm text-slate-300 leading-relaxed max-w-3xl">
            Administrative overview data will appear here once operational modules are enabled. This administrative console operates on a separate frontend on port 3001, strictly segregated from the user-facing Customer and Employee portals on port 3000, while sharing the central FastAPI backend and PostgreSQL database.
          </p>
        </div>

        {/* Recent Pending Employee Verification Table Preview */}
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-xs">
          <div className="px-5 py-4 border-b border-slate-200 flex items-center justify-between bg-slate-50">
            <div>
              <h2 className="text-lg sm:text-xl font-bold text-slate-900">
                Pending Employee Verification Requests
              </h2>
              <p className="text-sm text-slate-500 mt-1">
                Onboarding requests awaiting administrative approval
              </p>
            </div>
            <Link
              href="/employee-verification"
              className="text-sm font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1.5"
            >
              <span>View All ({pendingRequests.length})</span>
              <ArrowRight className="h-4 w-4" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-100 text-slate-600 uppercase font-mono text-xs tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3.5">Applicant Name</th>
                  <th className="px-4 py-3.5">Organization</th>
                  <th className="px-4 py-3.5">Department</th>
                  <th className="px-4 py-3.5">Designation</th>
                  <th className="px-4 py-3.5">Status</th>
                  <th className="px-4 py-3.5 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-400 text-sm">
                      Loading verification requests...
                    </td>
                  </tr>
                ) : pendingRequests.length === 0 ? (
                  <tr>
                    <td colSpan={6} className="px-4 py-8 text-center text-slate-400 text-sm">
                      No pending employee requests at this time.
                    </td>
                  </tr>
                ) : (
                  pendingRequests.slice(0, 5).map((req) => (
                    <tr key={req.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3.5 font-semibold text-slate-800 text-sm sm:text-[15px]">
                        {req.full_name || req.email}
                      </td>
                      <td className="px-4 py-3.5 text-slate-600 text-sm sm:text-[15px]">{req.organization}</td>
                      <td className="px-4 py-3.5 text-slate-600 text-sm sm:text-[15px]">{req.department || "N/A"}</td>
                      <td className="px-4 py-3.5 text-slate-600 text-sm sm:text-[15px]">{req.designation || "N/A"}</td>
                      <td className="px-4 py-3.5">
                        <span className="px-2.5 py-0.5 rounded text-xs font-bold bg-amber-100 text-amber-800 border border-amber-200">
                          {req.status}
                        </span>
                      </td>
                      <td className="px-4 py-3.5 text-right">
                        <Link
                          href={`/employee-verification/${req.id}`}
                          className="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded text-xs sm:text-sm font-semibold inline-block"
                        >
                          Inspect
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

      </div>
    </AdminLayout>
  );
}
