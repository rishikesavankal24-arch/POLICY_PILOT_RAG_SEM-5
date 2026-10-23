"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { useAuth } from "@/contexts/AuthContext";
import { useLanguage } from "@/i18n/LanguageContext";
import { 
  FileText, 
  Search, 
  Filter, 
  RefreshCw, 
  ExternalLink, 
  ShieldAlert, 
  Lock, 
  FolderCheck,
  X
} from "lucide-react";

interface ApplicationQueueItem {
  id: string;
  user_id: string;
  loan_type: string;
  requested_amount: number;
  tenure: number;
  purpose: string;
  status: string;
  created_at: string | null;
  updated_at: string | null;
  applicant_name: string;
  applicant_email: string;
  is_own_application: boolean;
  document_count: number;
}

export default function EmployeeApplicationsQueuePage() {
  const { user } = useAuth();
  const { t, tStatus, tLoanType } = useLanguage();
  
  const [applications, setApplications] = useState<ApplicationQueueItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState("ALL");
  const [loanTypeFilter, setLoanTypeFilter] = useState("ALL");
  const [searchTerm, setSearchTerm] = useState("");

  const fetchApplications = async () => {
    try {
      setLoading(true);
      setError(null);
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
      
      const params = new URLSearchParams();
      if (statusFilter !== "ALL") params.append("status", statusFilter);
      if (loanTypeFilter !== "ALL") params.append("loan_type", loanTypeFilter);
      if (searchTerm.trim()) params.append("search", searchTerm.trim());

      const res = await fetch(`${apiUrl}/api/employee/applications?${params.toString()}`, {
        credentials: "include"
      });

      if (res.status === 403) {
        setError("Access Forbidden: Authorized employee verification required.");
        return;
      }
      if (!res.ok) {
        throw new Error(`Failed to fetch application queue (HTTP ${res.status})`);
      }
      const data = await res.json();
      setApplications(data || []);
    } catch (err: any) {
      setError(err.message || "Failed to load applications queue.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchApplications();
  }, [statusFilter, loanTypeFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchApplications();
  };

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
        
        {/* Header Strip */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-4">
          <div>
            <h1 className="text-2xl sm:text-[26px] font-bold tracking-tight text-slate-950 font-sans">
              Application Queue
            </h1>
          </div>

          <button
            onClick={fetchApplications}
            disabled={loading}
            className="px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 rounded-md text-[13px] sm:text-sm font-medium border border-slate-200 flex items-center gap-1.5 transition-colors shadow-2xs self-start sm:self-auto"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
            <span>Refresh Queue</span>
          </button>
        </div>

        {/* Error State */}
        {error && (
          <div className="p-4 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-[13px] sm:text-sm flex items-start gap-3 shadow-2xs">
            <ShieldAlert className="h-5 w-5 text-rose-600 shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="font-semibold text-rose-900 text-sm sm:text-[15px]">Operational Notice</p>
              <p className="mt-0.5">{error}</p>
            </div>
          </div>
        )}

        {/* Search & Filter Controls */}
        <div className="p-4 sm:p-5 bg-white border border-slate-200 rounded-lg space-y-4 shadow-2xs">
          <form onSubmit={handleSearchSubmit} className="flex flex-col sm:flex-row gap-3">
            <div className="relative flex-1">
              <Search className="h-4.5 w-4.5 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Search applicant name, email, loan product, or application ID..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-9 py-2.5 bg-white border border-slate-200 rounded-md text-[15px] sm:text-base text-slate-900 placeholder:text-[15px] placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-blue-600 focus:border-blue-600 transition-colors"
              />
              {searchTerm && (
                <button
                  type="button"
                  onClick={() => {
                    setSearchTerm("");
                    setTimeout(() => fetchApplications(), 50);
                  }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  <X className="h-4 w-4" />
                </button>
              )}
            </div>

            <button
              type="submit"
              className="px-5 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-md text-[14px] sm:text-[15px] font-semibold transition-colors shadow-2xs"
            >
              Search
            </button>
          </form>

          {/* Filter Pills */}
          <div className="flex flex-wrap items-center gap-2 pt-3 border-t border-slate-100 text-[13px] sm:text-sm">
            <span className="text-[13px] sm:text-sm font-mono uppercase tracking-wider text-slate-500 mr-1 flex items-center gap-1.5 font-medium">
              <Filter className="h-3.5 w-3.5" /> Status:
            </span>
            {["ALL", "SUBMITTED", "UNDER_REVIEW", "ADDITIONAL_INFO_REQUIRED", "APPROVED", "DECLINED"].map((st) => (
              <button
                key={st}
                onClick={() => setStatusFilter(st)}
                className={`px-3 py-1.5 rounded-md text-[14px] transition-all ${
                  statusFilter === st
                    ? "bg-blue-50 text-blue-700 border border-blue-200 font-semibold shadow-2xs"
                    : "bg-slate-50 text-slate-600 border border-slate-200 hover:bg-slate-100 hover:text-slate-900 font-medium"
                }`}
              >
                {st === "ALL" ? "All Cases" : tStatus(st)}
              </button>
            ))}

            <div className="ml-auto hidden md:flex items-center gap-2">
              <span className="text-[13px] sm:text-sm font-mono text-slate-500">Total in view:</span>
              <span className="text-[13px] sm:text-sm font-bold text-slate-900 bg-slate-100 px-2.5 py-0.5 rounded border border-slate-200">
                {applications.length}
              </span>
            </div>
          </div>
        </div>

        {/* Application Queue Table */}
        <div className="bg-white border border-slate-200 rounded-lg overflow-hidden shadow-2xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-slate-50 text-slate-600 uppercase font-mono text-[13px] tracking-wider border-b border-slate-200">
                <tr>
                  <th className="px-4 py-4 font-semibold whitespace-nowrap">Case Reference</th>
                  <th className="px-4 py-4 font-semibold whitespace-nowrap">Applicant Details</th>
                  <th className="px-4 py-4 font-semibold whitespace-nowrap">Product & Purpose</th>
                  <th className="px-4 py-4 font-semibold whitespace-nowrap">Amount / Tenure</th>
                  <th className="px-4 py-4 font-semibold whitespace-nowrap">Docs</th>
                  <th className="px-4 py-4 font-semibold whitespace-nowrap">Status</th>
                  <th className="px-4 py-4 font-semibold whitespace-nowrap">Timeline</th>
                  <th className="px-4 py-4 font-semibold text-right whitespace-nowrap">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-16 text-center text-slate-500">
                      <div className="flex flex-col items-center gap-2.5">
                        <div className="w-7 h-7 border-2 border-slate-900 border-t-transparent rounded-full animate-spin"></div>
                        <span className="text-sm">Loading queue records...</span>
                      </div>
                    </td>
                  </tr>
                ) : applications.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-4 py-16 text-center text-slate-500">
                      <FileText className="h-9 w-9 text-slate-400 mx-auto mb-2" />
                      <p className="text-sm font-semibold text-slate-700">No applications match current filters</p>
                      <p className="text-[13px] text-slate-500 mt-0.5">Try resetting search filters or check back later</p>
                    </td>
                  </tr>
                ) : (
                  applications.map((app) => (
                    <tr key={app.id} className="hover:bg-slate-50/80 transition-colors">
                      <td className="px-4 py-4 font-mono">
                        <span className="text-blue-700 font-semibold text-[15px]">{app.id.slice(0, 8)}</span>
                        <span className="text-slate-500 block text-[13px] mt-0.5">VER-{app.id.slice(9, 13)}</span>
                        {app.is_own_application && (
                          <span className="inline-flex items-center gap-1 mt-1 text-xs font-medium text-amber-800 bg-amber-50 border border-amber-200 px-2 py-0.5 rounded uppercase">
                            <Lock className="h-3 w-3" /> Self-Owned
                          </span>
                        )}
                      </td>
                      <td className="px-4 py-4">
                        <div className="font-semibold text-slate-900 text-[15px] sm:text-base">{app.applicant_name}</div>
                        <div className="text-[13px] sm:text-sm text-slate-500 truncate max-w-[200px] xl:max-w-[260px] mt-0.5">{app.applicant_email}</div>
                      </td>
                      <td className="px-4 py-4">
                        <span className="font-semibold text-slate-900 text-[15px] sm:text-base block">{tLoanType(app.loan_type)}</span>
                        <span className="text-[13px] sm:text-sm text-slate-500 truncate max-w-[220px] xl:max-w-[280px] block mt-0.5">
                          {app.purpose}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <span className="font-semibold text-slate-900 text-[15px] sm:text-base block">{formatINR(app.requested_amount)}</span>
                        <span className="text-slate-600 block text-[13px] sm:text-sm mt-0.5">{app.tenure} {t("common.months")}</span>
                      </td>
                      <td className="px-4 py-4">
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded bg-slate-50 text-slate-700 border border-slate-200 text-[14px] font-medium">
                          <FolderCheck className="h-3.5 w-3.5 text-slate-500" />
                          {app.document_count}
                        </span>
                      </td>
                      <td className="px-4 py-4">
                        <span className={`inline-block px-2.5 py-1 rounded-md text-[12px] sm:text-[13px] font-semibold uppercase tracking-wider border ${getStatusBadge(app.status)}`}>
                          {tStatus(app.status)}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-[13px] text-slate-600 font-mono whitespace-nowrap">
                        <div>Sub: {app.created_at ? new Date(app.created_at).toLocaleDateString() : "N/A"}</div>
                        {app.updated_at && app.updated_at !== app.created_at && (
                          <div className="text-[12px] text-slate-400 mt-0.5">Upd: {new Date(app.updated_at).toLocaleDateString()}</div>
                        )}
                      </td>
                      <td className="px-4 py-4 text-right whitespace-nowrap">
                        <Link
                          href={`/employee/applications/${app.id}`}
                          className="inline-flex items-center gap-1.5 px-3.5 py-2 bg-white hover:bg-slate-50 text-slate-700 hover:text-slate-900 rounded-md border border-slate-200 text-[14px] font-semibold shadow-2xs transition-colors"
                        >
                          <span>Inspect</span>
                          <ExternalLink className="h-3.5 w-3.5" />
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
