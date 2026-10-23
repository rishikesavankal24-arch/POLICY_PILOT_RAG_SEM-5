"use client";

import { useAuth } from "@/contexts/AuthContext";
import { AuthenticatedLayout } from "@/components/layout/AuthenticatedLayout";
import { 
  FileText, 
  CheckCircle2, 
  Clock, 
  AlertCircle, 
  ArrowRight, 
  ShieldCheck, 
  FileWarning, 
  Bell, 
  Plus, 
  AlertTriangle,
  FolderOpen
} from "lucide-react";
import { useState, useEffect } from "react";
import Link from "next/link";
import { useLanguage } from "@/i18n/LanguageContext";

interface RequiredAction {
  id: string;
  type: string;
  title: string;
  description: string;
  action_url?: string;
  link?: string;
  urgency?: "HIGH" | "MEDIUM" | "LOW" | "URGENT";
  priority?: "HIGH" | "MEDIUM" | "LOW" | "URGENT";
  action_label?: string;
}

interface DashboardSummary {
  customer: { name: string; email: string };
  applications: {
    total: number;
    under_review: number;
    approved: number;
    draft: number;
    action_required: number;
    recent: any[];
  };
  documents: { total: number };
  notifications: { unread: number; recent: any[] };
  required_actions: RequiredAction[];
}

function CustomerDashboard() {
  const { user } = useAuth();
  const { t, tStatus, tLoanType } = useLanguage();
  
  const [data, setData] = useState<DashboardSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
      const res = await fetch(`${apiUrl}/api/customer/dashboard/summary`, { 
        credentials: 'include' 
      });

      if (!res.ok) {
        throw new Error(t("dashboard.unavailableSubtitle"));
      }

      const summaryData = await res.json();
      setData(summaryData);
    } catch (err: any) {
      console.error("Dashboard fetch error:", err);
      setError(t("dashboard.unavailableSubtitle"));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  if (isLoading) {
    return (
      <div className="flex flex-col h-64 items-center justify-center space-y-3">
        <div className="animate-spin rounded-full h-8 w-8 border-2 border-[#0B192C] border-t-transparent"></div>
        <p className="text-xs text-slate-500 font-medium tracking-wide uppercase">{t("common.loading")}</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 flex flex-col items-center justify-center text-center space-y-3">
        <AlertTriangle className="h-10 w-10 text-red-600" />
        <div>
          <h3 className="text-base sm:text-lg font-bold text-red-900">{t("dashboard.unavailableTitle")}</h3>
          <p className="text-[13px] sm:text-sm text-red-700 mt-1">{error || t("dashboard.unavailableSubtitle")}</p>
        </div>
        <button 
          onClick={fetchDashboardData}
          className="px-4 py-2 bg-[#0B192C] text-white rounded-md text-[14px] sm:text-[15px] font-semibold hover:bg-slate-800 transition-colors shadow-xs"
        >
          {t("dashboard.retry")}
        </button>
      </div>
    );
  }

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "APPROVED":
        return "bg-emerald-50 text-emerald-800 border-emerald-300";
      case "DECLINED":
        return "bg-red-50 text-red-800 border-red-300";
      case "ADDITIONAL_INFO_REQUIRED":
        return "bg-amber-50 text-amber-800 border-amber-300";
      case "UNDER_REVIEW":
        return "bg-blue-50 text-blue-800 border-blue-300";
      case "SUBMITTED":
        return "bg-slate-100 text-slate-800 border-slate-300";
      default:
        return "bg-slate-50 text-slate-700 border-slate-200";
    }
  };

  return (
    <div className="space-y-6 sm:space-y-7 text-slate-900">
      
      {/* Official Dossier Overview Header */}
      <div className="bg-white border border-slate-200 rounded-lg p-5 sm:p-6 shadow-xs">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="text-[13px] sm:text-sm font-bold text-slate-500 uppercase tracking-wider">{t("dashboard.applicantDossier")}</span>
              <span className="inline-block w-1.5 h-1.5 rounded-full bg-slate-300"></span>
              <span className="text-[12px] sm:text-[13px] font-semibold text-emerald-700 bg-emerald-50 px-2.5 py-0.5 rounded-md border border-emerald-200">
                ACTIVE ACCOUNT
              </span>
            </div>
            <h2 className="text-xl sm:text-[22px] font-bold tracking-tight text-slate-950 mt-1.5 font-sans">
              {data.customer.name || user?.full_name || t("nav.customer")}
            </h2>
            <p className="text-[13px] sm:text-sm text-slate-500 mt-1">
              Primary Identification: <span className="font-mono text-slate-800">{data.customer.email || user?.email}</span>
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/dashboard/applications/new"
              className="inline-flex items-center gap-2 px-4 py-2.5 bg-[#0B192C] text-white rounded-md text-[14px] sm:text-[15px] font-semibold hover:bg-slate-800 transition-colors shadow-xs"
            >
              <Plus className="h-4.5 w-4.5" />
              <span>{t("applications.newApplication")}</span>
            </Link>
          </div>
        </div>
      </div>

      {/* Operational KPI Matrix */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        {/* Total Applications */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[14px] sm:text-[15px] font-semibold uppercase tracking-wider">{t("dashboard.kpiApplications")}</span>
            <FileText className="h-5 w-5 text-slate-400" />
          </div>
          <div className="text-[28px] sm:text-[30px] font-bold text-slate-900 mt-2 font-mono leading-tight">{data.applications.total}</div>
          <div className="text-[13px] sm:text-sm text-slate-500 mt-1.5">Registered credit dossiers</div>
        </div>

        {/* Under Review */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
          <div className="flex items-center justify-between text-blue-700">
            <span className="text-[14px] sm:text-[15px] font-semibold uppercase tracking-wider">{t("dashboard.kpiUnderReview")}</span>
            <Clock className="h-5 w-5 text-blue-600" />
          </div>
          <div className="text-[28px] sm:text-[30px] font-bold text-blue-950 mt-2 font-mono leading-tight">{data.applications.under_review}</div>
          <div className="text-[13px] sm:text-sm text-blue-700 mt-1.5">In active underwriting review</div>
        </div>

        {/* Sanctioned / Approved */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
          <div className="flex items-center justify-between text-emerald-700">
            <span className="text-[14px] sm:text-[15px] font-semibold uppercase tracking-wider">{t("dashboard.kpiApproved")}</span>
            <CheckCircle2 className="h-5 w-5 text-emerald-600" />
          </div>
          <div className="text-[28px] sm:text-[30px] font-bold text-emerald-950 mt-2 font-mono leading-tight">{data.applications.approved}</div>
          <div className="text-[13px] sm:text-sm text-emerald-700 mt-1.5">Compliant & approved facilities</div>
        </div>

        {/* Pending Actions */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-xs">
          <div className="flex items-center justify-between text-amber-700">
            <span className="text-[14px] sm:text-[15px] font-semibold uppercase tracking-wider">{t("dashboard.kpiActionRequired")}</span>
            <AlertCircle className="h-5 w-5 text-amber-600" />
          </div>
          <div className="text-[28px] sm:text-[30px] font-bold text-amber-950 mt-2 font-mono leading-tight">
            {data.required_actions?.length || data.applications.action_required || 0}
          </div>
          <div className="text-[13px] sm:text-sm text-amber-700 mt-1.5">Mandatory compliance actions</div>
        </div>
      </div>

      {/* SECTION: What Needs Your Attention */}
      <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div>
            <h3 className="text-[15px] sm:text-base font-bold text-slate-900 uppercase tracking-wider">
              {t("dashboard.attentionTitle")}
            </h3>
            <p className="text-[13px] sm:text-sm text-slate-500 mt-1">
              {t("dashboard.attentionSubtitle")}
            </p>
          </div>
          {data.required_actions && data.required_actions.length > 0 && (
            <span className="text-[12px] sm:text-[13px] font-semibold bg-amber-100 text-amber-900 px-2.5 py-0.5 rounded-md border border-amber-200">
              {data.required_actions.length} Pending
            </span>
          )}
        </div>

        <div className="p-4 sm:p-5">
          {!data.required_actions || data.required_actions.length === 0 ? (
            <div className="flex items-start gap-3.5 p-4 sm:p-5 bg-emerald-50/60 border border-emerald-200 rounded-lg">
              <ShieldCheck className="h-6 w-6 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <h4 className="text-[15px] sm:text-base font-bold text-emerald-900">{t("dashboard.noAttentionTitle")}</h4>
                <p className="text-[13px] sm:text-sm text-emerald-700 mt-1">
                  {t("dashboard.noAttentionDesc")}
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              {data.required_actions.map((act) => (
                <div 
                  key={act.id} 
                  className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 p-4 bg-slate-50/80 border border-slate-200 rounded-lg hover:bg-slate-50 transition-colors"
                >
                  <div className="flex items-start gap-3.5 min-w-0">
                    {(act.urgency === "HIGH" || act.priority === "HIGH" || act.priority === "URGENT") ? (
                      <AlertCircle className="h-5 w-5 text-amber-600 shrink-0 mt-0.5" />
                    ) : (
                      <FileWarning className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
                    )}
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[15px] sm:text-base font-bold text-slate-900">{act.title}</span>
                        {(act.urgency === "HIGH" || act.priority === "HIGH" || act.priority === "URGENT") && (
                          <span className="text-[12px] sm:text-[13px] font-semibold text-red-700 bg-red-50 border border-red-200 px-2 py-0.5 rounded-md">
                            Action Required
                          </span>
                        )}
                      </div>
                      <p className="text-[14px] sm:text-[15px] text-slate-600 mt-1 leading-relaxed">
                        {act.description}
                      </p>
                    </div>
                  </div>

                  <Link
                    href={act.action_url || act.link || "/dashboard"}
                    className="inline-flex items-center justify-center gap-2 px-4 py-2 bg-[#0B192C] text-white rounded-md text-[14px] sm:text-[15px] font-semibold hover:bg-slate-800 transition-colors shadow-xs shrink-0 self-start sm:self-auto"
                  >
                    <span>{act.action_label || "Proceed"}</span>
                    <ArrowRight className="h-4 w-4" />
                  </Link>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* SECTION: Recent Applications Ledger */}
      <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <h3 className="text-[15px] sm:text-base font-bold text-slate-900 uppercase tracking-wider">
              {t("dashboard.recentApplications")}
            </h3>
            <span className="text-[13px] sm:text-sm font-medium text-slate-500 font-mono">
              ({data.applications.recent.length})
            </span>
          </div>
          <Link 
            href="/dashboard/applications" 
            className="text-[14px] sm:text-[15px] font-semibold text-blue-700 hover:text-blue-900 hover:underline flex items-center gap-1.5"
          >
            <span>{t("applications.filterAll")}</span>
            <ArrowRight className="h-4 w-4" />
          </Link>
        </div>

        <div className="p-0">
          {data.applications.recent.length === 0 ? (
            <div className="text-center py-12 px-4">
              <FolderOpen className="h-11 w-11 text-slate-300 mx-auto mb-2.5" />
              <h4 className="text-base font-bold text-slate-800">{t("dashboard.noApplicationsTitle")}</h4>
              <p className="text-[13px] sm:text-sm text-slate-500 mt-1 max-w-sm mx-auto">{t("dashboard.noApplicationsSubtitle")}</p>
              <Link
                href="/dashboard/applications/new"
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-[#0B192C] text-white rounded-md text-[14px] sm:text-[15px] font-semibold hover:bg-slate-800 transition-colors shadow-xs"
              >
                <Plus className="h-4 w-4" />
                <span>{t("dashboard.startFirstApp")}</span>
              </Link>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left border-collapse">
                <thead className="text-[13px] text-slate-600 uppercase font-mono font-semibold tracking-wider bg-slate-100/70 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-4 font-semibold whitespace-nowrap">{t("dashboard.tableId")}</th>
                    <th className="px-4 py-4 font-semibold whitespace-nowrap">{t("dashboard.tableType")}</th>
                    <th className="px-4 py-4 font-semibold whitespace-nowrap">{t("dashboard.tableAmount")}</th>
                    <th className="px-4 py-4 font-semibold whitespace-nowrap">{t("dashboard.tableStatus")}</th>
                    <th className="px-4 py-4 font-semibold whitespace-nowrap">{t("dashboard.tableDate")}</th>
                    <th className="px-4 py-4 font-semibold text-right whitespace-nowrap">{t("applications.tableAction")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 font-sans">
                  {data.applications.recent.map((app: any) => (
                    <tr key={app.id} className="hover:bg-slate-50/70 transition-colors">
                      <td className="px-4 py-4 font-mono font-semibold text-[14px] sm:text-[15px] text-slate-900">
                        {app.id}
                      </td>
                      <td className="px-4 py-4 font-medium text-[14px] sm:text-[15px] text-slate-800">
                        {tLoanType(app.type)}
                      </td>
                      <td className="px-4 py-4 font-mono font-semibold text-[14px] sm:text-[15px] text-slate-900">
                        {app.requested_amount ? `₹${Number(app.requested_amount).toLocaleString('en-IN')}` : "—"}
                      </td>
                      <td className="px-4 py-4">
                        <span className={`inline-flex items-center px-2.5 py-1 rounded-md text-[12px] sm:text-[13px] font-semibold border ${getStatusBadge(app.status)}`}>
                          {tStatus(app.status)}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-slate-600 font-mono text-[13px] sm:text-sm whitespace-nowrap">
                        {app.created_at ? new Date(app.created_at).toLocaleDateString('en-IN', {
                          day: '2-digit',
                          month: 'short',
                          year: 'numeric'
                        }) : "—"}
                      </td>
                      <td className="px-4 py-4 text-right whitespace-nowrap">
                        <Link
                          href={`/dashboard/applications/${app.id}`}
                          className="inline-flex items-center gap-1.5 font-semibold text-blue-700 hover:text-blue-900 hover:underline text-[13px] sm:text-[14px]"
                        >
                          <span>{t("dashboard.viewDossier")}</span>
                          <ArrowRight className="h-3.5 w-3.5" />
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      </div>

      {/* Grid: Compliance Documents & Official Notices */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        
        {/* Documents Ledger Summary */}
        <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
            <h3 className="text-[15px] sm:text-base font-bold text-slate-900 uppercase tracking-wider">{t("dashboard.documentsCardTitle")}</h3>
            <Link 
              href="/dashboard/documents" 
              className="text-[14px] sm:text-[15px] font-semibold text-blue-700 hover:text-blue-900 hover:underline"
            >
              View Document Center →
            </Link>
          </div>
          <div className="p-5 sm:p-6 flex-1 flex flex-col justify-center">
            {data.documents.total === 0 ? (
              <div className="text-center py-6">
                <FolderOpen className="h-9 w-9 text-slate-300 mx-auto mb-2" />
                <h4 className="text-[14px] sm:text-[15px] font-bold text-slate-800">{t("dashboard.noDocsTitle")}</h4>
                <p className="text-[13px] sm:text-sm text-slate-500 mt-1">{t("dashboard.noDocsSubtitle")}</p>
              </div>
            ) : (
              <div className="space-y-3">
                <div className="p-3.5 bg-slate-50 border border-slate-200 rounded-md flex items-center justify-between">
                  <div className="flex items-center gap-2.5">
                    <ShieldCheck className="h-5 w-5 text-emerald-600" />
                    <span className="text-[14px] font-medium text-slate-800">Total Statutory Documents</span>
                  </div>
                  <span className="font-mono font-bold text-base text-slate-900">{data.documents.total}</span>
                </div>
                <p className="text-[13px] text-slate-500 italic">
                  Note: Document verification status will be confirmed after underwriter inspection.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Notifications & System Bulletins */}
        <div className="bg-white border border-slate-200 rounded-lg shadow-xs overflow-hidden flex flex-col">
          <div className="px-5 py-4 border-b border-slate-200 bg-slate-50 flex items-center justify-between">
            <h3 className="text-[15px] sm:text-base font-bold text-slate-900 uppercase tracking-wider">{t("dashboard.recentNotificationsTitle")}</h3>
            <Link 
              href="/dashboard/notifications" 
              className="text-[14px] sm:text-[15px] font-semibold text-blue-700 hover:text-blue-900 hover:underline"
            >
              {t("header.viewAllNotifications")}
            </Link>
          </div>
          <div className="p-5 sm:p-6 flex-1 flex flex-col justify-center">
            {data.notifications.recent.length === 0 ? (
              <div className="text-center py-6">
                <Bell className="h-9 w-9 text-slate-300 mx-auto mb-2" />
                <h4 className="text-[14px] sm:text-[15px] font-bold text-slate-800">{t("dashboard.noNotifsTitle")}</h4>
                <p className="text-[13px] sm:text-sm text-slate-500 mt-1">{t("dashboard.noNotifsSubtitle")}</p>
              </div>
            ) : (
              <ul className="space-y-3">
                {data.notifications.recent.slice(0, 3).map((notif: any, idx) => (
                  <li key={idx} className="p-3.5 bg-slate-50/70 border border-slate-200 rounded-md">
                    <div className="flex items-center justify-between">
                      <span className="font-bold text-[14px] sm:text-[15px] text-slate-900">{notif.title}</span>
                      <span className="text-[12px] sm:text-[13px] text-slate-400 font-mono">
                        {new Date(notif.created_at).toLocaleDateString('en-IN', { month: 'short', day: 'numeric' })}
                      </span>
                    </div>
                    <p className="text-[13px] sm:text-sm text-slate-600 mt-1 leading-relaxed">{notif.message}</p>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>

      </div>

    </div>
  );
}

function EmployeeDashboard() {
  const { user } = useAuth();
  const isPending = user?.onboarding_status === "PENDING_VERIFICATION";
  
  return (
    <div className="space-y-6">
      <div className="bg-white border border-slate-200 rounded p-5 shadow-xs">
        <h2 className="text-lg font-bold text-slate-900 mb-1">Employee Portal Operations</h2>
        <p className="text-xs text-slate-600">Compliance & Regulatory Review Management</p>
      </div>

      {isPending ? (
        <div className="bg-white border border-slate-200 rounded shadow-xs p-10 text-center text-slate-500 text-xs">
          <Clock className="h-8 w-8 text-amber-600 mx-auto mb-3" />
          <h3 className="text-sm font-bold text-slate-900">Account Authorization Pending</h3>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Your credentials have been submitted for supervisory review. Full underwriting tools will activate upon signoff.
          </p>
        </div>
      ) : (
        <div className="p-8 bg-[#0F172A] border border-slate-800 rounded-xl text-slate-100 space-y-4 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-amber-500/20 text-amber-400 border border-amber-500/40 flex items-center justify-center font-bold">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-white uppercase tracking-wide">
                  Enterprise Underwriting Desk Active
                </h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Verified officer account • Centralized operations workspace
                </p>
              </div>
            </div>
            <Link
              href="/employee/dashboard"
              className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-slate-950 font-bold rounded-lg text-xs flex items-center justify-center gap-1.5 transition-colors shadow-sm"
            >
              <span>Launch Operations Console</span>
              <ArrowRight className="h-3.5 w-3.5" />
            </Link>
          </div>
          <p className="text-xs text-slate-400 leading-relaxed border-t border-slate-800 pt-3">
            Your verified employee console includes the complete institutional queue, customer evidence inspection, statutory compliance checks, and non-repudiation audit logging.
          </p>
        </div>
      )}
    </div>
  );
}

export default function DashboardPage() {
  const { user, isLoading } = useAuth();
  const { t } = useLanguage();

  if (isLoading) {
    return (
      <AuthenticatedLayout containerClassName="w-[calc(100%-32px)] sm:w-[calc(100%-48px)] max-w-[1600px] px-4 sm:px-6">
        <div className="flex h-64 items-center justify-center">
          <div className="animate-spin rounded-full h-8 w-8 border-2 border-[#0B192C] border-t-transparent"></div>
        </div>
      </AuthenticatedLayout>
    );
  }

  const isEmployee = user?.requested_role === "EMPLOYEE";

  return (
    <AuthenticatedLayout containerClassName="w-[calc(100%-32px)] sm:w-[calc(100%-48px)] max-w-[1600px] px-4 sm:px-6">
      <div className="mb-6 flex flex-col sm:flex-row sm:items-center sm:justify-between border-b border-slate-200 pb-5">
        <div>
          <h1 className="text-2xl sm:text-[26px] font-bold tracking-tight text-slate-950 uppercase font-sans">{t("dashboard.title")}</h1>
          <p className="text-[13px] sm:text-sm text-slate-500 mt-1">Government & Regulated Banking Service Desk</p>
        </div>
      </div>
      {isEmployee ? <EmployeeDashboard /> : <CustomerDashboard />}
    </AuthenticatedLayout>
  );
}
