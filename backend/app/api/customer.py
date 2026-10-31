from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timezone
import uuid
import shutil

from app.db.session import get_db
from app.core.security import get_current_user
from app.api.documents import STORAGE_DIR, sanitize_filename
from app.db.models import (
    User, Role, Application, Document, DocumentStatus, Notification, ApplicationStatus,
    InformationRequestStatus, AdditionalInformationRequest, ApplicationAuditEvent
)
from app.services.document_validator import DocumentValidator
from app.services.document_processor import DocumentProcessor
from app.services.rag.service import RAGService
from app.services.answer_generator import AnswerGenerator

router = APIRouter()


class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None
    language: Optional[str] = None


@router.get("/profile")
def get_profile(current_user: User = Depends(get_current_user)):
    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(
            status_code=403,
            detail="Only customers can access the customer profile"
        )

    return {
        "full_name": current_user.full_name,
        "email": current_user.email,
        "phone_number": current_user.phone_number,
        "date_of_birth": current_user.date_of_birth,
        "address": current_user.address,
        "city": current_user.city,
        "state": current_user.state,
        "pincode": current_user.pincode,
        "language": current_user.language
    }


@router.patch("/profile")
def update_profile(
    profile_data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(
            status_code=403,
            detail="Only customers can update customer profile"
        )

    update_dict = profile_data.model_dump(exclude_unset=True)
    if not update_dict:
        return {"message": "No fields to update"}

    user_in_db = db.query(User).filter(User.id == current_user.id).first()

    for key, value in update_dict.items():
        setattr(user_in_db, key, value)

    db.commit()
    db.refresh(user_in_db)

    return {"message": "Profile updated successfully"}


@router.get("/dashboard/summary")
def get_customer_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns an operational summary of the customer's dashboard and real required actions.
    Enforces authorization to ensure only the authenticated user's data is retrieved.
    """
    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(
            status_code=403,
            detail="Only customers can access the customer dashboard"
        )

    applications = (
        db.query(Application)
        .filter(Application.user_id == current_user.id)
        .order_by(Application.updated_at.desc())
        .all()
    )

    documents_count = (
        db.query(Document)
        .filter(Document.user_id == current_user.id)
        .count()
    )

    notifications = (
        db.query(Notification)
        .filter(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )

    under_review_count = sum(
        1 for app in applications
        if app.status == ApplicationStatus.UNDER_REVIEW.value
    )

    approved_count = sum(
        1 for app in applications
        if app.status == ApplicationStatus.APPROVED.value
    )

    draft_count = sum(
        1 for app in applications
        if app.status == ApplicationStatus.DRAFT.value
    )

    action_required_count = sum(
        1 for app in applications
        if app.status == ApplicationStatus.ADDITIONAL_INFO_REQUIRED.value
    )

    unread_notifications = sum(
        1 for n in notifications
        if not n.is_read
    )

    # Derive real required actions from database state
    required_actions = []

    # 1. Draft applications that need completion and submission
    for app in applications:
        if app.status == ApplicationStatus.DRAFT.value:
            required_actions.append({
                "id": f"draft_{app.id}",
                "type": "COMPLETE_DRAFT",
                "title": f"Complete Draft: {app.loan_type}",
                "description": (
                    f"Reference #{str(app.id)[:8].upper()} is saved as draft. "
                    "Review and submit for underwriting."
                ),
                "application_id": str(app.id),
                "link": f"/dashboard/applications/{app.id}",
                "action_url": f"/dashboard/applications/{app.id}",
                "priority": "HIGH",
                "urgency": "HIGH",
                "action_label": "Resume Application"
            })

    # 2. Deficient documents requiring replacement (REQUIRES_REUPLOAD)
    reupload_docs = (
        db.query(Document)
        .join(Application)
        .filter(
            Application.user_id == current_user.id,
            Document.status == DocumentStatus.REQUIRES_REUPLOAD.value
        )
        .all()
    )

    for doc in reupload_docs:
        doc_name = doc.document_type.replace('_', ' ').title()

        reason = (
            doc.review_notes
            if (
                doc.review_notes
                and doc.review_notes.strip().lower() not in ["nil", "none"]
            )
            else "Correction or clearer copy required"
        )

        required_actions.append({
            "id": f"reupload_{doc.id}",
            "type": "DOCUMENT_REPLACEMENT_REQUIRED",
            "title": f"Document Replacement Required: {doc_name}",
            "description": f"Reason: {reason}",
            "document_id": str(doc.id),
            "document_type": doc.document_type,
            "document_name": doc_name,
            "deficiency_reason": reason,
            "application_id": str(doc.application_id),
            "link": (
                f"/dashboard/applications/{doc.application_id}"
                f"?replace_doc={doc.id}"
            ),
            "action_url": (
                f"/dashboard/applications/{doc.application_id}"
                f"?replace_doc={doc.id}"
            ),
            "priority": "URGENT",
            "urgency": "HIGH",
            "action_label": "Replace Document"
        })

    # 3. Specific open supplementary information requests from credit desk
    open_requests = (
        db.query(AdditionalInformationRequest)
        .join(Application)
        .filter(
            Application.user_id == current_user.id,
            AdditionalInformationRequest.status == InformationRequestStatus.OPEN.value
        )
        .all()
    )

    seen_apps = set()

    for ir in open_requests:
        seen_apps.add(str(ir.application_id))

        required_actions.append({
            "id": f"inforeq_{ir.id}",
            "type": "INFORMATION_REQUEST",
            "title": f"Additional Information Required: {ir.title}",
            "description": ir.description,
            "application_id": str(ir.application_id),
            "request_id": str(ir.id),
            "requested_document_type": ir.requested_document_type,
            "link": f"/dashboard/applications/{ir.application_id}",
            "action_url": f"/dashboard/applications/{ir.application_id}",
            "priority": "URGENT",
            "urgency": "HIGH",
            "action_label": "Respond / Upload"
        })

    # 3. Fallback for any application in ADDITIONAL_INFO_REQUIRED
    # without individual request items
    for app in applications:
        if (
            app.status == ApplicationStatus.ADDITIONAL_INFO_REQUIRED.value
            and str(app.id) not in seen_apps
        ):
            required_actions.append({
                "id": f"info_{app.id}",
                "type": "PROVIDE_INFO",
                "title": f"Action Required: {app.loan_type}",
                "description": (
                    "Credit desk requested supplementary documentation "
                    f"for reference #{str(app.id)[:8].upper()}."
                ),
                "application_id": str(app.id),
                "link": f"/dashboard/applications/{app.id}",
                "action_url": f"/dashboard/applications/{app.id}",
                "priority": "URGENT",
                "urgency": "HIGH",
                "action_label": "Provide Details"
            })

    # 3. Documents needed if applications exist but zero documents uploaded
    if len(applications) > 0 and documents_count == 0:
        required_actions.append({
            "id": "upload_initial_docs",
            "type": "UPLOAD_DOCUMENTS",
            "title": "Mandatory Compliance Documents",
            "description": (
                "Upload required identity and income proofs "
                "to expedite regulatory verification."
            ),
            "application_id": None,
            "link": "/dashboard/documents",
            "action_url": "/dashboard/documents",
            "priority": "HIGH",
            "urgency": "HIGH",
            "action_label": "Upload Documents"
        })

    # 4. Unread urgent or important notifications
    for n in notifications:
        if not n.is_read and n.type in ["WARNING", "SECURITY"]:
            required_actions.append({
                "id": f"notif_{n.id}",
                "type": "REVIEW_NOTIFICATION",
                "title": n.title,
                "description": n.message,
                "application_id": None,
                "link": "/dashboard/notifications",
                "action_url": "/dashboard/notifications",
                "priority": "NORMAL",
                "urgency": "MEDIUM",
                "action_label": "View Notice"
            })

    return {
        "customer": {
            "name": current_user.full_name,
            "email": current_user.email,
        },
        "applications": {
            "total": len(applications),
            "under_review": under_review_count,
            "approved": approved_count,
            "draft": draft_count,
            "action_required": action_required_count,
            "recent": [
                {
                    "id": str(app.id),
                    "type": app.loan_type,
                    "status": app.status,
                    "amount": app.requested_amount,
                    "created_at": (
                        app.created_at.strftime("%Y-%m-%d")
                        if app.created_at
                        else None
                    ),
                    "updated_at": (
                        app.updated_at.strftime("%Y-%m-%d")
                        if app.updated_at
                        else app.created_at.strftime("%Y-%m-%d")
                    )
                }
                for app in applications[:5]
            ]
        },
        "documents": {
            "total": documents_count
        },
        "notifications": {
            "unread": unread_notifications,
            "recent": [
                {
                    "id": str(n.id),
                    "title": n.title,
                    "message": n.message,
                    "type": n.type,
                    "is_read": n.is_read,
                    "created_at": n.created_at.strftime("%Y-%m-%d %H:%M")
                }
                for n in notifications[:5]
            ]
        },
        "required_actions": required_actions
    }


@router.get("/actions")
def get_customer_actions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Dedicated endpoint returning real pending required actions
    for the authenticated customer.
    """
    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(
            status_code=403,
            detail="Only customers can access customer actions"
        )

    summary = get_customer_dashboard_summary(
        current_user=current_user,
        db=db
    )

    return {
        "customer": summary["customer"],
        "actions": summary["required_actions"],
        "total_actions": len(summary["required_actions"])
    }


class CustomerAIQueryRequest(BaseModel):
    query: str
    application_id: Optional[str] = None


@router.post("/ai/query")
def customer_ai_query(
    request: CustomerAIQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Customer AI Assistance integrated with RAG and Ollama.

    RAG retrieves and evaluates authoritative active policy evidence.
    When sufficient supporting evidence exists, AnswerGenerator sends
    that evidence to Phi-3 through Ollama to generate the final
    customer-facing AI answer.

    If evidence is insufficient, the LLM is not called.
    """

    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(
            status_code=403,
            detail="Only customers can access Customer AI Assistance"
        )

    # -------------------------------------------------------------------
    # Derive applicability context from the authenticated user's application.
    # All values come from server-side authoritative data; client input is
    # only used to identify which application — not to set filter values.
    # -------------------------------------------------------------------
    app_context = None
    rag_loan_type: Optional[str] = None
    rag_institution: Optional[str] = None
    rag_jurisdiction: Optional[str] = None

    if request.application_id:
        try:
            app_uuid = UUID(request.application_id)
        except ValueError:
            raise HTTPException(
                status_code=404,
                detail="Application dossier not found or unauthorized"
            )

        app = db.query(Application).filter(
            Application.id == app_uuid,
            Application.user_id == current_user.id
        ).first()

        if not app:
            raise HTTPException(
                status_code=404,
                detail="Application dossier not found or unauthorized"
            )

        docs_count = (
            db.query(Document)
            .filter(
                Document.application_id == app.id,
                Document.user_id == current_user.id
            )
            .count()
        )

        app_context = {
            "id": str(app.id),
            "reference": str(app.id),
            "type": app.loan_type,
            "status": app.status,
            "requested_amount": app.requested_amount,
            "tenure": app.tenure,
            "documents_attached": docs_count
        }

        # Derive applicability filters from the application's loan_type.
        # institution / jurisdiction come from the policy applicability table,
        # not from the Application model directly, because we must not trust
        # arbitrary application data to drive security-relevant policy scoping.
        # We use loan_type (from the application) to constrain which policies
        # are eligible; institution/jurisdiction are passed only if they are
        # available from the application record itself (they are optional on
        # Application and may be null).
        if app.loan_type:
            rag_loan_type = app.loan_type.strip()

    # -------------------------------------------------------------------
    # STEP 1: RAG retrieval and evidence evaluation.
    # -------------------------------------------------------------------
    rag = RAGService()

    rag_response = rag.query(
        db=db,
        query=request.query,
        loan_type=rag_loan_type,
    )

    evidence_status = rag_response.get(
        "evidence_status",
        "insufficient"
    )

    evidence_list = rag_response.get(
        "evidence",
        []
    )

    # -------------------------------------------------------------------
    # STEP 2: Generate the final AI response using Phi-3.
    #
    # Only supporting evidence that passed the RAG evidence evaluator
    # reaches the LLM.
    # -------------------------------------------------------------------
    if evidence_status == "sufficient" and evidence_list:

        answer_generator = AnswerGenerator()

        try:
            customer_safe_text = answer_generator.generate(
                query=request.query,
                evidence=evidence_list,
            )
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(
                    "Policy evidence was retrieved successfully, but the "
                    "AI answer-generation service is currently unavailable."
                ),
            ) from exc

        engine_status = "RAG_GROUNDED_LLM_GENERATION"

    # -------------------------------------------------------------------
    # STEP 3: No sufficient evidence means no LLM generation.
    #
    # This prevents Phi-3 from answering a question that PolicyPilot's
    # retrieval layer could not substantiate.
    # -------------------------------------------------------------------
    else:
        customer_safe_text = (
            "No specific active policy clause was found directly "
            "addressing your query. Please refer to standard "
            "application guidelines or contact your loan officer."
        )

        engine_status = "INSUFFICIENT_EVIDENCE"

    # -------------------------------------------------------------------
    # STEP 4: Return the AI answer together with the evidence used
    # to ground it.
    # -------------------------------------------------------------------
    return {
        "status": "SUCCESS",
        "query": request.query,
        "application_id": request.application_id,
        "application_context": app_context,
        "customer_safe_response": customer_safe_text,
        "explanation": customer_safe_text,
        "engine_status": engine_status,
        "evidence_status": evidence_status,
        "evidence": evidence_list,
        "disclaimer": (
            "This guidance is generated using authoritative active "
            "policy documents and AI-assisted analysis. It is provided "
            "for advisory purposes only."
        )
    }


@router.post("/applications/{application_id}/information-requests/{request_id}/respond")
def respond_to_information_request(
    application_id: UUID,
    request_id: UUID,
    file: UploadFile = File(...),
    notes: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Customer responds to an open information request by uploading
    the requested document.

    Saves file to real filesystem storage, creates a persistent Document,
    links it to the request, transitions request status to RESPONDED,
    updates application status to UNDER_REVIEW, and logs an audit event
    and employee notification.
    """
    if current_user.role != Role.CUSTOMER.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only customers can respond to information requests"
        )

    app = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id
    ).first()

    if not app:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found or unauthorized"
        )

    info_req = db.query(AdditionalInformationRequest).filter(
        AdditionalInformationRequest.id == request_id,
        AdditionalInformationRequest.application_id == app.id
    ).first()

    if not info_req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Information request not found"
        )

    if info_req.status != InformationRequestStatus.OPEN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Information request is already in '{info_req.status}' state."
        )

    doc_type = (
        info_req.requested_document_type
        or "ADDITIONAL_DOCUMENT"
    )

    # Centralized validation of document type, extension, size,
    # magic bytes, MIME, and SHA-256
    validation = DocumentValidator.validate(
        file,
        doc_type
    )

    # Save document file using real storage
    doc_id = uuid.uuid4()
    safe_filename = sanitize_filename(
        validation.original_filename
    )

    doc_dir = (
        STORAGE_DIR / str(doc_id)
    ).resolve()

    doc_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    target_path = (
        doc_dir / safe_filename
    ).resolve()

    try:
        target_path.relative_to(STORAGE_DIR)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid storage path"
        )

    # Rewind upload file stream before writing
    file.file.seek(0)

    try:
        with open(target_path, "wb") as buffer:
            shutil.copyfileobj(
                file.file,
                buffer
            )

        proc_metadata = DocumentProcessor.process_document(
            target_path,
            validation.mime_type
        )

    except Exception:
        if doc_dir.exists():
            shutil.rmtree(
                doc_dir,
                ignore_errors=True
            )
        raise

    new_doc = Document(
        id=doc_id,
        user_id=current_user.id,
        application_id=app.id,
        document_type=validation.document_type,
        file_url=f"documents/{doc_id}/{safe_filename}",
        status=DocumentStatus.UPLOADED.value,
        original_filename=validation.original_filename,
        file_size_bytes=validation.file_size_bytes,
        mime_type=validation.mime_type,
        file_hash=validation.file_hash,
        page_count=proc_metadata.get("page_count")
    )

    db.add(new_doc)

    # Link response document to request and mark responded
    info_req.response_document_id = new_doc.id
    info_req.response_notes = (
        notes.strip()
        if notes
        else None
    )
    info_req.status = InformationRequestStatus.RESPONDED.value
    info_req.responded_at = datetime.now(timezone.utc)

    # Transition application status back to UNDER_REVIEW
    app.status = ApplicationStatus.UNDER_REVIEW.value
    app.updated_at = datetime.now(timezone.utc)

    # Persist audit event
    audit = ApplicationAuditEvent(
        application_id=app.id,
        user_id=current_user.id,
        event_type="CUSTOMER_RESPONDED",
        title="Customer Submitted Requested Document",
        description=(
            f"Applicant submitted '{doc_type}' in response to "
            f"query: {info_req.title}."
        )
    )

    db.add(audit)

    # Create notification for reviewing employee
    notif = Notification(
        user_id=info_req.requested_by,
        title="Customer Responded to Information Request",
        message=(
            "Applicant submitted supplementary document for application "
            f"#{str(app.id)[:8].upper()}."
        ),
        type="STATUS_UPDATE",
        related_entity_id=app.id
    )

    db.add(notif)

    # Invalidate review readiness if application was marked review-ready
    from app.api.employee import invalidate_review_readiness

    invalidate_review_readiness(
        app,
        db,
        current_user.id,
        (
            f"Applicant responded to information request "
            f"'{info_req.title}' with document '{doc_type}'."
        )
    )

    db.commit()

    db.refresh(info_req)
    db.refresh(new_doc)

    return {
        "message": "Response submitted successfully.",
        "request": {
            "id": str(info_req.id),
            "status": info_req.status,
            "response_document_id": str(info_req.response_document_id),
            "responded_at": info_req.responded_at.isoformat()
        },
        "document": {
            "id": str(new_doc.id),
            "document_type": new_doc.document_type,
            "file_url": f"/api/documents/{new_doc.id}/content",
            "status": new_doc.status
        },
        "application_status": app.status
    }