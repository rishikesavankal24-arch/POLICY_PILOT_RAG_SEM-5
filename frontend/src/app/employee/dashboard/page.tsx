"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { useAuth } from "@/contexts/AuthContext";
import { useLanguage } from "@/i18n/LanguageContext";
import { 
  FileText, 
  Clock, 
  CheckCircle2, 
  AlertCircle, 
  FolderCheck, 
  ShieldAlert, 
  UserCheck, 
  ArrowRight, 
  Shield, 
  Building2, 
  RefreshCw,
  ExternalLink,
  Lock,
  ChevronRight
} from "lucide-react";

interface EmployeeDashboardData {
  metrics: {
    total_submitted_applications: number;
    under_review: number;
    submitted: number;
    additional_info_required: number;
    approved: number;
    declined: number;
    my_assignments: number;
    pending_documents: number;
  };
  recent_applications: {
    id: string;
    user_id: string;
    loan_type: string;
    requested_amount: number;
    tenure: number;
    status: string;
    applicant_name: string;
    created_at: string | null;
    is_own_application: boolean;
  }[];
  employee_info: {
    id: string;
    full_name: string;
    email: string;
    role: string;
    organization: string;
    department: string;
    designation: string;
    employee_id: string | null;
  };
}

export default function EmployeeDashboardPage() {
  const { user } = useAuth();
  const { t, tStatus, tLoanType } = useLanguage();
  const [data, setData] = useState<EmployeeDashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    try {
      setLoading(true);
      setError(null);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      const res = await fetch(`${apiUrl}/api/employee/dashboard/summary`, {
        credentials: "include"
      });
      if (res.status === 403) {
        setError("Access Restricted: This operational console requires authorized employee credentials.");
        return;
      }
      if (!res.ok) {
        throw new Error(`Failed to load operations dashboard (HTTP ${res.status})`);
      }
      const json = await res.json();
      setData(json);
    } catch (err: any) {
      setError(err.message || "Failed to connect to institutional operations API.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const formatINR = (val: number) => {
    return new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: "INR",
      maximumFractionDigits: 0
    }).format(val);
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return "bg-emerald-50 text-emerald-700 border-emerald-200";
      case "DECLINED":
        return "bg-rose-50 text-rose-700 border-rose-200";
      case "UNDER_REVIEW":
        return "bg-blue-50 text-blue-700 border-blue-200";
      case "ADDITIONAL_INFO_REQUIRED":
        return "bg-amber-50 text-amber-800 border-amber-200";
      case "SUBMITTED":
      default:
        return "bg-slate-100 text-slate-700 border-slate-200";
    }
  };

  return (
    <EmployeeLayout>
      <div className="space-y-6">
        
        {/* Page Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-4">
          <div>
            <h1 className="text-xl font-bold tracking-tight text-slate-950 font-sans">
              Employee Dashboard
            </h1>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={fetchDashboardData}
              disabled={loading}
              className="px-3 py-1.5 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 rounded-md text-xs font-medium border border-slate-200 flex items-center gap-1.5 transition-colors shadow-2xs"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              <span>Refresh</span>
            </button>
            <Link
              href="/employee/applications"
              className="px-3.5 py-1.5 bg-[#0F172A] hover:bg-slate-800 text-white rounded-md text-xs font-semibold flex items-center gap-1.5 shadow-2xs transition-colors"
            >
              <span>Application Queue</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
        </div>

        {/* Error State */}
        {error && (
          <div className="p-3.5 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-start gap-2.5 shadow-2xs">
            <ShieldAlert className="h-4 w-4 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-rose-900">Operational Notice</p>
              <p className="mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Officer Information Strip */}
        {data?.employee_info && (
          <div className="bg-white border border-slate-200 rounded-lg p-3.5 sm:px-4 flex flex-col md:flex-row md:items-center justify-between gap-3 text-xs shadow-2xs">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 rounded bg-slate-100 border border-slate-200 text-slate-700 flex items-center justify-center shrink-0">
                <Building2 className="h-4 w-4 text-slate-600" />
              </div>
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-900">{data.employee_info.full_name}</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200">
                    {data.employee_info.employee_id || "OFFICER"}
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 mt-0.5">
                  {data.employee_info.designation} • {data.employee_info.department} ({data.employee_info.organization})
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Operational Metrics Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-lg bg-white border border-slate-200 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-slate-600">Queue Total</span>
              <FileText className="h-4 w-4 text-slate-400" />
            </div>
            <div className="text-2xl font-bold text-slate-950 mt-1.5">
              {loading ? "..." : data?.metrics.total_submitted_applications ?? 0}
            </div>
          </div>

          <div className="p-4 rounded-lg bg-white border border-slate-200 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-blue-700">Under Review</span>
              <Clock className="h-4 w-4 text-blue-600" />
            </div>
            <div className="text-2xl font-bold text-blue-700 mt-1.5">
              {loading ? "..." : data?.metrics.under_review ?? 0}
            </div>
          </div>

          <div className="p-4 rounded-lg bg-white border border-slate-200 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-amber-700">Action Required</span>
              <AlertCircle className="h-4 w-4 text-amber-600" />
            </div>
            <div className="text-2xl font-bold text-amber-800 mt-1.5">
              {loading ? "..." : data?.metrics.additional_info_required ?? 0}
            </div>
          </div>

          <div className="p-4 rounded-lg bg-white border border-slate-200 shadow-2xs">
            <div className="flex items-center justify-between text-slate-500">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-emerald-700">Sanctioned</span>
              <CheckCircle2 className="h-4 w-4 text-emerald-600" />
            </div>
            <div className="text-2xl font-bold text-emerald-700 mt-1.5">
              {loading ? "..." : data?.metrics.approved ?? 0}
            </div>
          </div>
        </div>

        {/* Secondary Supporting Metric Strip */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 rounded-lg bg-white border border-slate-200 shadow-2xs flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-900">Pending Document Audits</p>
              <p className="text-xl font-bold text-slate-900 mt-1">
                {loading ? "..." : data?.metrics.pending_documents ?? 0}
              </p>
            </div>
            <Link
              href="/employee/documents"
              className="w-9 h-9 rounded-md bg-slate-50 hover:bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200 flex items-center justify-center transition-colors"
              title="Open Document Audits"
            >
              <FolderCheck className="h-4 w-4" />
            </Link>
          </div>

          <div className="p-4 rounded-lg bg-white border border-slate-200 shadow-2xs flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-900">Initial Review Intake</p>
              <p className="text-xl font-bold text-slate-900 mt-1">
                {loading ? "..." : data?.metrics.submitted ?? 0}
              </p>
            </div>
            <Link
              href="/employee/applications"
              className="w-9 h-9 rounded-md bg-slate-50 hover:bg-slate-100 text-slate-600 hover:text-slate-900 border border-slate-200 flex items-center justify-center transition-colors"
              title="Open Application Intake"
            >
              <FileText className="h-4 w-4" />
            </Link>
          </div>

          <div className="p-4 rounded-lg bg-white border border-slate-200 shadow-2xs flex items-center justify-between">
            <div>
              <p className="text-xs font-semibold text-slate-900">Queue Model</p>
              <p className="text-xs font-bold text-slate-800 mt-1 uppercase font-mono">
                Shared Pooled Queue
              </p>
            </div>
            <div className="w-9 h-9 rounded-md bg-slate-50 text-slate-600 border border-slate-200 flex items-center justify-center">
              <UserCheck className="h-4 w-4" />
            </div>
          </div>
        </div>

        {/* Operational Applications Queue Preview */}
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-2xs">
          <div className="px-5 py-3.5 bg-slate-50/70 border-b border-slate-200 flex items-center justify-between">
            <div>
              <h2 className="text-sm font-bold text-slate-900 uppercase tracking-wide">
                Recent Applications
              </h2>
            </div>
            <Link
              href="/employee/applications"
              className="text-xs font-semibold text-blue-600 hover:text-blue-800 flex items-center gap-1 transition-colors"
            >
              <span>View Full Queue</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </Link>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-600 uppercase font-mono text-[11px] tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3 font-semibold">Applicant / Case</th>
                  <th className="px-4 py-3 font-semibold">Product</th>
                  <th className="px-4 py-3 font-semibold">Amount</th>
                  <th className="px-4 py-3 font-semibold">Tenure</th>
                  <th className="px-4 py-3 font-semibold">Status</th>
                  <th className="px-4 py-3 font-semibold">Submitted</th>
                  <th className="px-4 py-3 font-semibold text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                      Loading queue data...
                    </td>
                  </tr>
                ) : !data?.recent_applications || data.recent_applications.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                      No customer applications currently in the operational queue.
                    </td>
                  </tr>
                ) : (
                  data.recent_applications.map((app) => (
                    <tr key={app.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-900">
                          {app.applicant_name}
                        </div>
                        <div className="text-[10px] text-slate-500 font-mono mt-0.5">
                          ID: {app.id.slice(0, 8)}...
                        </div>
                        {app.is_own_application && (
                          <span className="inline-flex items-center gap-1 mt-1 text-[10px] font-medium text-amber-800 bg-amber-50 border border-amber-200 px-1.5 py-0.2 rounded">
                            <Lock className="h-3 w-3" /> Conflict: Self-owned
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-3 text-slate-700 font-medium">
                        {tLoanType(app.loan_type)}
                      </td>
                      <td className="px-4 py-3 font-semibold text-slate-900">
                        {formatINR(app.requested_amount)}
                      </td>
                      <td className="px-4 py-3 text-slate-600">
                        {app.tenure} {t("common.months")}
                      </td>
                      <td className="px-4 py-3">
                        <span className={`inline-block px-2 py-0.5 rounded text-[10px] font-semibold uppercase tracking-wider border ${getStatusBadge(app.status)}`}>
                          {tStatus(app.status)}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-600 font-mono text-[11px]">
                        {app.created_at ? new Date(app.created_at).toLocaleDateString() : "N/A"}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <Link
                          href={`/employee/applications/${app.id}`}
                          className="inline-flex items-center gap-1 px-2.5 py-1 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 rounded border border-slate-200 text-xs font-semibold shadow-2xs transition-colors"
                        >
                          <span>Inspect</span>
                          <ExternalLink className="h-3 w-3" />
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
    </EmployeeLayout>
  );
}
