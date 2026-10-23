"use client";

import Link from "next/link";
import { EmployeeLayout } from "@/components/layout/EmployeeLayout";
import { 
  ShieldCheck, 
  BookOpen, 
  FileCheck, 
  CheckCircle2, 
  AlertCircle, 
  Building2, 
  Layers, 
  Shield, 
  ExternalLink,
  ClipboardList
} from "lucide-react";

export default function EmployeeCompliancePage() {
  const directives = [
    {
      code: "RBI/DOR/2024-25/112",
      title: "Master Direction – Digital Lending Guidelines (Updated 2024)",
      description: "Direct loan disbursal mandate, cooling-off/look-up period, and mandatory key fact statement (KFS) disclosures.",
      status: "COMPLIANT",
      category: "LENDING OPERATIONS"
    },
    {
      code: "RBI/FIDD/2023-24/098",
      title: "Priority Sector Lending (PSL) Targets and Classifications",
      description: "Mandatory quotas for agriculture, MSME micro-enterprises, and education credit quotas.",
      status: "MONITORED",
      category: "CREDIT ALLOCATION"
    },
    {
      code: "RBI/DBR/2023-24/074",
      title: "Master Direction – Know Your Customer (KYC) Direction",
      description: "Customer identification procedures (CIP), Central KYC Registry (CKYCR) linkage, and risk categorization.",
      status: "ACTIVE",
      category: "AML / KYC"
    },
    {
      code: "RBI/DPSS/2024-25/019",
      title: "Cyber Security Framework for Regulated Entities",
      description: "Data residency in Indian data centers, audit trail integrity, and end-to-end payload encryption.",
      status: "VERIFIED",
      category: "SECURITY & DATA"
    }
  ];

  return (
    <EmployeeLayout>
      <div className="space-y-6">
        
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-4 border-b border-slate-200 gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold tracking-tight text-slate-950 font-sans">
                Policy Directives & Compliance Console
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-semibold bg-slate-100 text-slate-700 border border-slate-200">
                RBI GUIDELINE REFERENCE 2024-25
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Reference banking guidelines, regulatory directives, and policy review rules
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Link
              href="/employee/applications"
              className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 text-white rounded-md text-xs font-semibold flex items-center gap-1.5 transition-colors shadow-2xs"
            >
              <ClipboardList className="h-4 w-4" />
              <span>Application Queue</span>
            </Link>
          </div>
        </div>


        {/* Regulatory Directives Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {directives.map((dir, idx) => (
            <div key={idx} className="p-4 bg-white border border-slate-200 rounded-lg space-y-3 shadow-2xs">
              <div className="flex items-center justify-between">
                <span className="text-[10px] font-mono font-semibold text-slate-700 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                  {dir.code}
                </span>
                <span className="text-[10px] font-mono font-semibold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">
                  {dir.status}
                </span>
              </div>

              <div>
                <h3 className="text-sm font-bold text-slate-900">{dir.title}</h3>
                <p className="text-xs text-slate-600 mt-1 leading-relaxed">{dir.description}</p>
              </div>

              <div className="pt-2 border-t border-slate-100 flex items-center justify-between text-[11px] text-slate-500 font-mono">
                <span>CATEGORY: {dir.category}</span>
                <span className="text-slate-600 flex items-center gap-1">
                  Enforced <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                </span>
              </div>
            </div>
          ))}
        </div>

        {/* Underwriter Statutory Checklist */}
        <div className="bg-white border border-slate-200 rounded-lg p-5 shadow-2xs space-y-4">
          <div className="flex items-center gap-2 pb-3 border-b border-slate-100 text-slate-900">
            <BookOpen className="h-4 w-4 text-blue-600" />
            <h2 className="text-xs font-bold uppercase tracking-wider text-slate-900">
              Underwriter Statutory Due Diligence Checklist
            </h2>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-start gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-900">Mandatory KYC Verification</p>
                <p className="text-[11px] text-slate-600 mt-0.5">
                  Verify government identity card against national database prior to credit sanction.
                </p>
              </div>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-start gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-900">Income & Debt-to-Income Audit</p>
                <p className="text-[11px] text-slate-600 mt-0.5">
                  Ensure fixed obligation to income ratio (FOIR) remains within institutional thresholds.
                </p>
              </div>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-start gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-900">Conflict of Interest Clearance</p>
                <p className="text-[11px] text-slate-600 mt-0.5">
                  Strictly confirm that neither applicant nor close relatives are the evaluating officer.
                </p>
              </div>
            </div>

            <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg flex items-start gap-2.5">
              <CheckCircle2 className="h-4 w-4 text-emerald-600 shrink-0 mt-0.5" />
              <div>
                <p className="font-semibold text-slate-900">Key Fact Statement (KFS) Issuance</p>
                <p className="text-[11px] text-slate-600 mt-0.5">
                  Approved offers must provide an itemized APR disclosure before customer acceptance.
                </p>
              </div>
            </div>
          </div>
        </div>

      </div>
    </EmployeeLayout>
  );
}
