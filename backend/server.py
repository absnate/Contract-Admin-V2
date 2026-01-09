import os
import json
from datetime import datetime, timedelta
from bson import ObjectId
from fastapi import FastAPI, UploadFile, File, HTTPException, Body, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from motor.motor_asyncio import AsyncIOMotorClient
import gridfs
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv
import io

# Load environment variables
load_dotenv()

from utils import extract_text_from_pdf, extract_text_from_docx, serialize_doc, create_pdf_from_text
from llm_service import analyze_contract_text, chat_with_context

# --- Configuration ---
MONGO_URL = os.environ.get("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.environ.get("DB_NAME", "abs_contract_admin")
PORT = 8001
RETENTION_DAYS = 90  # Contract reviews retained for 90 days

app = FastAPI(title="ABS Contract Admin Agent")

# --- CORS ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, lock this down
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Database ---
client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# For simpler async GridFS:
from motor.motor_asyncio import AsyncIOMotorGridFSBucket
fs_bucket = AsyncIOMotorGridFSBucket(db)

# --- Retention Policy (TTL Indexes) ---
async def ensure_ttl_indexes():
    """Ensures data retention policies."""
    try:
        # Contract reviews retained for 90 days (7776000 seconds)
        await db.contract_reviews.create_index("created_at", expireAfterSeconds=RETENTION_DAYS * 24 * 60 * 60)
        # Documents linked to reviews also 90 days
        await db.documents.create_index("upload_date", expireAfterSeconds=RETENTION_DAYS * 24 * 60 * 60)
        # Sessions 90 days
        await db.sessions.create_index("created_at", expireAfterSeconds=RETENTION_DAYS * 24 * 60 * 60)
        # Analyses 90 days
        await db.analyses.create_index("created_at", expireAfterSeconds=RETENTION_DAYS * 24 * 60 * 60)
        print(f"Retention policy: TTL indexes enforced ({RETENTION_DAYS}-day retention).")
    except Exception as e:
        print(f"Error setting TTL indexes: {e}")

@app.on_event("startup")
async def startup_db_client():
    await ensure_ttl_indexes()

# --- Models ---
class SessionCreate(BaseModel):
    task_type: str = "INITIAL_CONTRACT_REVIEW"

class ChatRequest(BaseModel):
    session_id: str
    message: str

class AnalysisRequest(BaseModel):
    file_id: str
    task_type: str
    guardrails_file_id: Optional[str] = None

class DocumentType(str):
    CONTRACT = "contract"
    PROPOSAL = "proposal"

class SetActiveRequest(BaseModel):
    file_id: str
    document_type: str  # "contract" or "proposal"

class SaveContractReviewRequest(BaseModel):
    session_id: str
    project_name: Optional[str] = None
    messages: Optional[List[Dict]] = []
    summary_data: Optional[Dict] = None
    negotiation_summary: Optional[List[Dict]] = None
    scope_data: Optional[Dict] = None
    analysis_result: Optional[Dict] = None

# --- Routes ---

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "abs-agent-backend"}

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...), document_type: str = "contract", session_id: str = None):
    """
    Uploads a file, saves to GridFS, extracts text, and saves metadata.
    document_type: "contract" or "proposal" - determined by upload control source
    session_id: Links document to a specific session/contract review
    """
    try:
        # Validate document_type
        if document_type not in ["contract", "proposal"]:
            document_type = "contract"  # Default to contract
            
        # 1. Read file content
        content = await file.read()
        filename = file.filename
        file_size = len(content)
        content_type = file.content_type

        # 2. Save to GridFS
        file_id = await fs_bucket.upload_from_stream(filename, content, metadata={"content_type": content_type})

        # 3. Extract Text
        text = ""
        file_stream = io.BytesIO(content)
        
        if filename.lower().endswith(".pdf"):
            text = extract_text_from_pdf(file_stream)
        elif filename.lower().endswith(".docx"):
            text = extract_text_from_docx(file_stream)
        else:
            text = "Unsupported file type for text extraction."

        # 4. Mark previous active document of same type AND same session as "previous"
        query = {"document_type": document_type, "is_active": True}
        if session_id:
            query["session_id"] = session_id
        await db.documents.update_many(query, {"$set": {"is_active": False}})

        # 5. Save Metadata to 'documents' collection with document type and active status
        file_doc = {
            "_id": file_id,
            "filename": filename,
            "upload_date": datetime.utcnow(),
            "size": file_size,
            "content_type": content_type,
            "extracted_text": text,
            "extracted_text_preview": text[:500] if text else "",
            "document_type": document_type,  # "contract" or "proposal"
            "is_active": True,  # Most recent upload of this type becomes active
            "session_id": session_id  # Link to session
        }
        await db.documents.insert_one(file_doc)

        return JSONResponse(status_code=200, content={
            "file_id": str(file_id),
            "filename": filename,
            "document_type": document_type,
            "is_active": True,
            "upload_date": datetime.utcnow().isoformat(),
            "text_preview": text[:200] + "..."
        })

    except Exception as e:
        print(f"Upload Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/sessions")
async def create_session(data: SessionCreate):
    """Creates a new chat session."""
    session_doc = {
        "created_at": datetime.utcnow(),
        "task_type": data.task_type,
        "messages": [], # List of {role, content, timestamp}
        "context_file_ids": []
    }
    result = await db.sessions.insert_one(session_doc)
    return {"session_id": str(result.inserted_id), "task_type": data.task_type}

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    """Retrieves session history."""
    if not ObjectId.is_valid(session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")
    
    session = await db.sessions.find_one({"_id": ObjectId(session_id)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return serialize_doc(session)

@app.get("/api/sessions")
async def list_sessions():
    """List all sessions."""
    cursor = db.sessions.find().sort("created_at", -1).limit(20)
    sessions = await cursor.to_list(length=20)
    return [serialize_doc(s) for s in sessions]

@app.post("/api/sessions/{session_id}/attach")
async def attach_file_to_session(session_id: str, body: Dict = Body(...)):
    """Link a file to a session context."""
    file_id = body.get("file_id")
    if not file_id:
         raise HTTPException(status_code=400, detail="file_id required")
         
    await db.sessions.update_one(
        {"_id": ObjectId(session_id)},
        {"$addToSet": {"context_file_ids": file_id}}
    )
    return {"status": "attached"}

@app.post("/api/documents/set-active")
async def set_active_document(request: SetActiveRequest):
    """Set a document as the active document for its type."""
    if request.document_type not in ["contract", "proposal"]:
        raise HTTPException(status_code=400, detail="document_type must be 'contract' or 'proposal'")
    
    # Check if document exists
    doc = await db.documents.find_one({"_id": ObjectId(request.file_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Deactivate all documents of this type
    await db.documents.update_many(
        {"document_type": request.document_type},
        {"$set": {"is_active": False}}
    )
    
    # Set the specified document as active
    await db.documents.update_one(
        {"_id": ObjectId(request.file_id)},
        {"$set": {"is_active": True, "document_type": request.document_type}}
    )
    
    return {"status": "success", "file_id": request.file_id, "document_type": request.document_type, "is_active": True}

@app.get("/api/documents/active")
async def get_active_documents():
    """Get the currently active contract and proposal documents."""
    active_contract = await db.documents.find_one({"document_type": "contract", "is_active": True})
    active_proposal = await db.documents.find_one({"document_type": "proposal", "is_active": True})
    
    result = {
        "contract": None,
        "proposal": None
    }
    
    if active_contract:
        result["contract"] = {
            "file_id": str(active_contract["_id"]),
            "filename": active_contract.get("filename"),
            "upload_date": active_contract.get("upload_date").isoformat() if active_contract.get("upload_date") else None,
            "extracted_text": active_contract.get("extracted_text", "")
        }
    
    if active_proposal:
        result["proposal"] = {
            "file_id": str(active_proposal["_id"]),
            "filename": active_proposal.get("filename"),
            "upload_date": active_proposal.get("upload_date").isoformat() if active_proposal.get("upload_date") else None,
            "extracted_text": active_proposal.get("extracted_text", "")
        }
    
    return result

@app.delete("/api/documents/{file_id}")
async def delete_document(file_id: str):
    """Explicitly delete a document."""
    if not ObjectId.is_valid(file_id):
        raise HTTPException(status_code=400, detail="Invalid file ID")
    
    # Delete from documents collection
    result = await db.documents.delete_one({"_id": ObjectId(file_id)})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Document not found")
    
    # Also try to delete from GridFS
    try:
        await fs_bucket.delete(ObjectId(file_id))
    except Exception:
        pass  # GridFS file may not exist
    
    return {"status": "deleted", "file_id": file_id}

@app.post("/api/analyze")
async def run_analysis(request: AnalysisRequest):
    """Run a specific analysis task on a file.
    
    LLM Context Feeding Rules:
    - Summary + Terms: Uses Active Contract
    - Scope Review: Uses Active Proposal (baseline) + Active Contract (for comparison)
    - Proposal Comparison: Uses Active Proposal + Active Contract (if both exist)
    """
    # 1. Get the specified file (for backwards compatibility)
    doc = await db.documents.find_one({"_id": ObjectId(request.file_id)})
    if not doc:
        raise HTTPException(status_code=404, detail="File not found")
    
    # 2. Get active documents for context-aware analysis
    active_contract = await db.documents.find_one({"document_type": "contract", "is_active": True})
    active_proposal = await db.documents.find_one({"document_type": "proposal", "is_active": True})
    
    # 3. Determine which text to use based on task type
    text = ""
    proposal_text = ""
    contract_text = ""
    
    # Build context based on task type
    if request.task_type in ["INITIAL_CONTRACT_REVIEW", "SCHEDULE_ANALYSIS", "PM_CONTRACT_REVIEW_SUMMARY", 
                              "PROCORE_MAPPING", "ACCOUNT_MANAGER_SUMMARY_EMAIL", "NEGOTIATION_SUGGESTED_REPLY",
                              "POST_EXECUTION_SUMMARY"]:
        # These tasks primarily use Contract
        if active_contract:
            contract_text = active_contract.get("extracted_text", "")
            text = contract_text
        else:
            # Fallback to the uploaded file
            text = doc.get("extracted_text", "")
    
    elif request.task_type == "SCOPE_REVIEW":
        # Scope Review: Proposal is AUTHORITATIVE BASELINE, Contract is for comparison
        if active_proposal:
            proposal_text = active_proposal.get("extracted_text", "")
        if active_contract:
            contract_text = active_contract.get("extracted_text", "")
        
        # Proposal-first format for scope review
        if proposal_text and contract_text:
            text = f"=== PROPOSAL DOCUMENT (AUTHORITATIVE BASELINE) ===\n{proposal_text}\n\n=== CONTRACT DOCUMENT (FOR COMPARISON) ===\n{contract_text}"
        elif proposal_text:
            text = f"=== PROPOSAL DOCUMENT (AUTHORITATIVE BASELINE) ===\n{proposal_text}\n\n=== CONTRACT DOCUMENT ===\nContract not yet uploaded. Scope comparison pending."
        elif contract_text:
            text = f"=== PROPOSAL DOCUMENT ===\nProposal required for scope review. Please upload a proposal document.\n\n=== CONTRACT DOCUMENT ===\n{contract_text}"
        else:
            text = doc.get("extracted_text", "")
            
    elif request.task_type == "PROPOSAL_COMPARISON_AND_EXHIBIT":
        # This task needs both Contract and Proposal
        if active_contract:
            contract_text = active_contract.get("extracted_text", "")
        if active_proposal:
            proposal_text = active_proposal.get("extracted_text", "")
        
        # Combine for analysis
        if contract_text and proposal_text:
            text = f"=== CONTRACT DOCUMENT ===\n{contract_text}\n\n=== PROPOSAL DOCUMENT ===\n{proposal_text}"
        elif proposal_text:
            text = f"=== PROPOSAL DOCUMENT (Contract pending) ===\n{proposal_text}"
        elif contract_text:
            text = f"=== CONTRACT DOCUMENT (Proposal pending) ===\n{contract_text}"
        else:
            text = doc.get("extracted_text", "")
    else:
        # Default: use the uploaded file
        text = doc.get("extracted_text", "")
    
    if not text:
        raise HTTPException(status_code=400, detail="No text extracted from this file")

    # 4. Get Guardrails Text (if provided)
    guardrails_text = ""
    if request.guardrails_file_id:
        gr_doc = await db.documents.find_one({"_id": ObjectId(request.guardrails_file_id)})
        if gr_doc:
            guardrails_text = gr_doc.get("extracted_text", "")
        
    # 5. Run LLM Analysis with Pre-Extraction
    try:
        # Pass separate contract and proposal texts for pre-extraction
        result = await analyze_contract_text(
            text=text, 
            task_type=request.task_type, 
            guardrails_text=guardrails_text,
            contract_text=contract_text if contract_text else None,
            proposal_text=proposal_text if proposal_text else None
        )
        
        # Add document context info to result
        result["document_context"] = {
            "active_contract": active_contract.get("filename") if active_contract else None,
            "active_proposal": active_proposal.get("filename") if active_proposal else None,
            "analyzed_file": doc.get("filename")
        }
        
        # --- SCOPE REVIEW: Map result to scope_data ---
        if request.task_type == "SCOPE_REVIEW":
            structured_data = result.get("structured_data", {})
            # Ensure scope_data is available for frontend
            if "scope_data" not in result.get("structured_data", {}):
                result["structured_data"]["scope_data"] = {
                    "scope_review_mode": structured_data.get("scope_review_mode", "proposal_only" if active_proposal and not active_contract else "proposal_and_contract"),
                    "proposal_filename": active_proposal.get("filename") if active_proposal else None,
                    "contract_filename": active_contract.get("filename") if active_contract else None,
                    "scopes_identified": structured_data.get("scopes_identified", []),
                    "scope_review_status": structured_data.get("scope_review_status", "Pending – Contract Required for Comparison")
                }
        
        # --- PDF SCHEDULE EXTRACTION LOGIC ---
        schedule_file_info = {}
        structured_data = result.get("structured_data", {})
        
        # Check both INITIAL_CONTRACT_REVIEW (extracted_schedule) and SCHEDULE_ANALYSIS (schedule_rows/text)
        schedule_text = ""
        project_name = "Project"
        
        # 1. From INITIAL_CONTRACT_REVIEW
        extracted_schedule = structured_data.get("extracted_schedule")
        if extracted_schedule:
            schedule_text = extracted_schedule.get("schedule_text", "")
            project_name = extracted_schedule.get("project_name", "Project")
            
        # 2. From SCHEDULE_ANALYSIS (Synthesize a text report if not explicit text)
        schedule_analysis_data = structured_data.get("schedule_analysis_data")
        if schedule_analysis_data:
            project_name = schedule_analysis_data.get("project_name", "Project")
            # Create a nice text representation for the PDF
            schedule_text = f"Project: {project_name}\n\n"
            schedule_text += f"Contract Start: {schedule_analysis_data.get('contract_start_date')}\n"
            schedule_text += f"Contract Completion: {schedule_analysis_data.get('contract_completion_date')}\n\n"
            
            if schedule_analysis_data.get("abs_scopes"):
                schedule_text += "--- ABS Scopes ---\n"
                for scope in schedule_analysis_data.get("abs_scopes"):
                    schedule_text += f"\nScope: {scope.get('scope_name')}\n"
                    schedule_text += f"  Start: {scope.get('start_date')}\n"
                    schedule_text += f"  Finish: {scope.get('completion_date')}\n"
                    schedule_text += f"  Basis: {scope.get('basis')}\n"

        if schedule_text and "Schedule not found" not in schedule_text:
            if project_name == "Unknown Project":
                project_name = "Contract"
            
            # Generate PDF
            pdf_bytes = create_pdf_from_text(schedule_text, title=f"Schedule: {project_name}")
            
            if pdf_bytes:
                print(f"Generated PDF size: {len(pdf_bytes)} bytes")
                
                # Filename
                pdf_filename = f"{project_name} contract schedule.pdf".replace("/", "-").replace("\\", "-")
                
                # Save to GridFS
                pdf_file_id = await fs_bucket.upload_from_stream(
                    pdf_filename, 
                    io.BytesIO(pdf_bytes), 
                    metadata={"content_type": "application/pdf"}
                )
                
                schedule_file_info = {
                    "file_id": str(pdf_file_id),
                    "filename": pdf_filename
                }
                
                # Append to result so frontend knows
                result["schedule_pdf"] = schedule_file_info
            else:
                print("PDF Generation failed (empty bytes)")

        # 6. Save Result
        analysis_doc = {
            "file_id": request.file_id,
            "task_type": request.task_type,
            "created_at": datetime.utcnow(),
            "result": result,
            "active_contract_id": str(active_contract["_id"]) if active_contract else None,
            "active_proposal_id": str(active_proposal["_id"]) if active_proposal else None
        }
        await db.analyses.insert_one(analysis_doc)
        
        return result 
    except Exception as e:
        error_msg = str(e)
        status_code = 500
        if "Quota Exceeded" in error_msg:
            status_code = 402 # Payment Required
        
        raise HTTPException(status_code=status_code, detail=error_msg)

@app.get("/api/files/{file_id}/download")
async def download_file(file_id: str):
    """Download a file from GridFS."""
    try:
        if not ObjectId.is_valid(file_id):
            raise HTTPException(status_code=400, detail="Invalid file ID")
            
        grid_out = await fs_bucket.open_download_stream(ObjectId(file_id))
        print(f"Downloading file: {grid_out.filename}, Length: {grid_out.length}")
        
        if grid_out.length == 0:
             # Try to generate content on the fly if it's 0 bytes? 
             # No, better to return error so user knows.
             print("WARNING: File length is 0")
             # Return error for now
             # raise HTTPException(status_code=500, detail="File is empty")

        return StreamingResponse(
            grid_out, 
            media_type=grid_out.metadata.get("content_type", "application/octet-stream"),
            headers={"Content-Disposition": f"attachment; filename={grid_out.filename}"}
        )
    except Exception as e:
        if "No file found" in str(e):
             raise HTTPException(status_code=404, detail="File not found")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_route(request: ChatRequest):
    """Chat with the agent within a session context."""
    # 1. Fetch Session
    if not ObjectId.is_valid(request.session_id):
        raise HTTPException(status_code=400, detail="Invalid session ID")
        
    session = await db.sessions.find_one({"_id": ObjectId(request.session_id)})
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    # 2. Gather Context (Files)
    context_text = ""
    file_ids = session.get("context_file_ids", [])
    if file_ids:
        # Use bulk query to avoid N+1
        object_ids = []
        for fid in file_ids:
             try:
                 object_ids.append(ObjectId(fid))
             except:
                 continue # Skip invalid ids
        
        docs = await db.documents.find({'_id': {'$in': object_ids}}).to_list(length=None)
        for doc in docs:
            context_text += f"\n--- File: {doc.get('filename')} ---\n{doc.get('extracted_text', '')[:50000]}..." # Limit context per file
            
    # 3. Append User Message to DB
    user_msg = {"role": "user", "content": request.message, "timestamp": datetime.utcnow()}
    await db.sessions.update_one(
        {"_id": ObjectId(request.session_id)},
        {"$push": {"messages": user_msg}}
    )
    
    # 4. Call LLM
    recent_history = session.get("messages", [])[-10:] 
    
    try:
        assistant_response_text = await chat_with_context(
            message=request.message,
            history=recent_history,
            context=context_text,
            task_type=session.get("task_type", "GENERAL")
        )
        
        # 5. Save Assistant Message
        bot_msg = {"role": "assistant", "content": assistant_response_text, "timestamp": datetime.utcnow()}
        await db.sessions.update_one(
            {"_id": ObjectId(request.session_id)},
            {"$push": {"messages": bot_msg}}
        )
        
        return {"response": assistant_response_text}
        
    except Exception as e:
        print(f"Chat Error: {e}")
        raise HTTPException(status_code=500, detail="AI processing failed")

# ═══════════════════════════════════════════════════════════════════════════════
# CONTRACT REVIEWS - HISTORY & PERSISTENCE (90-day retention)
# ═══════════════════════════════════════════════════════════════════════════════

@app.post("/api/contract-reviews")
async def save_contract_review(request: SaveContractReviewRequest):
    """
    Save a contract review with all tab data for history.
    Retained for 90 days.
    """
    try:
        # Get session data
        session = None
        if request.session_id and ObjectId.is_valid(request.session_id):
            session = await db.sessions.find_one({"_id": ObjectId(request.session_id)})
        
        # Get documents linked to this session
        contracts = []
        proposals = []
        if request.session_id:
            cursor = db.documents.find({"session_id": request.session_id})
            async for doc in cursor:
                doc_info = {
                    "file_id": str(doc["_id"]),
                    "filename": doc.get("filename"),
                    "document_type": doc.get("document_type"),
                    "is_active": doc.get("is_active"),
                    "upload_date": doc.get("upload_date").isoformat() if doc.get("upload_date") else None
                }
                if doc.get("document_type") == "contract":
                    contracts.append(doc_info)
                else:
                    proposals.append(doc_info)
        
        # Determine project name
        project_name = request.project_name
        if not project_name and request.summary_data:
            project_name = request.summary_data.get("project_name", "Untitled Review")
        if not project_name:
            project_name = f"Contract Review - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}"
        
        # Create contract review document
        review_doc = {
            "session_id": request.session_id,
            "project_name": project_name,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "expires_at": datetime.utcnow() + timedelta(days=RETENTION_DAYS),
            "contracts": contracts,
            "proposals": proposals,
            "messages": request.messages or (session.get("messages", []) if session else []),
            "summary_data": request.summary_data,
            "negotiation_summary": request.negotiation_summary,
            "scope_data": request.scope_data,
            "analysis_result": request.analysis_result,
            "task_type": session.get("task_type") if session else "INITIAL_CONTRACT_REVIEW"
        }
        
        # Check if review already exists for this session
        existing = await db.contract_reviews.find_one({"session_id": request.session_id})
        if existing:
            # Update existing review
            await db.contract_reviews.update_one(
                {"_id": existing["_id"]},
                {"$set": {
                    "updated_at": datetime.utcnow(),
                    "project_name": project_name,
                    "contracts": contracts,
                    "proposals": proposals,
                    "messages": review_doc["messages"],
                    "summary_data": request.summary_data,
                    "negotiation_summary": request.negotiation_summary,
                    "scope_data": request.scope_data,
                    "analysis_result": request.analysis_result
                }}
            )
            return {"status": "updated", "review_id": str(existing["_id"]), "project_name": project_name}
        else:
            # Insert new review
            result = await db.contract_reviews.insert_one(review_doc)
            return {"status": "created", "review_id": str(result.inserted_id), "project_name": project_name}
        
    except Exception as e:
        print(f"Save Contract Review Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contract-reviews")
async def list_contract_reviews(limit: int = 50, skip: int = 0):
    """
    List all contract reviews (history).
    Returns summary info for listing, not full data.
    """
    try:
        cursor = db.contract_reviews.find().sort("updated_at", -1).skip(skip).limit(limit)
        reviews = []
        async for doc in cursor:
            # Calculate days remaining
            expires_at = doc.get("expires_at")
            days_remaining = None
            if expires_at:
                delta = expires_at - datetime.utcnow()
                days_remaining = max(0, delta.days)
            
            reviews.append({
                "review_id": str(doc["_id"]),
                "session_id": doc.get("session_id"),
                "project_name": doc.get("project_name", "Untitled"),
                "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
                "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
                "days_remaining": days_remaining,
                "task_type": doc.get("task_type"),
                "contract_count": len(doc.get("contracts", [])),
                "proposal_count": len(doc.get("proposals", [])),
                "has_summary": doc.get("summary_data") is not None,
                "has_terms": doc.get("negotiation_summary") is not None and len(doc.get("negotiation_summary", [])) > 0,
                "has_scope": doc.get("scope_data") is not None
            })
        
        # Get total count
        total = await db.contract_reviews.count_documents({})
        
        return {
            "reviews": reviews,
            "total": total,
            "limit": limit,
            "skip": skip,
            "retention_days": RETENTION_DAYS
        }
        
    except Exception as e:
        print(f"List Contract Reviews Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/contract-reviews/{review_id}")
async def get_contract_review(review_id: str):
    """
    Get full contract review data including all tabs.
    """
    try:
        if not ObjectId.is_valid(review_id):
            raise HTTPException(status_code=400, detail="Invalid review ID")
        
        review = await db.contract_reviews.find_one({"_id": ObjectId(review_id)})
        if not review:
            raise HTTPException(status_code=404, detail="Contract review not found")
        
        # Calculate days remaining
        expires_at = review.get("expires_at")
        days_remaining = None
        if expires_at:
            delta = expires_at - datetime.utcnow()
            days_remaining = max(0, delta.days)
        
        return {
            "review_id": str(review["_id"]),
            "session_id": review.get("session_id"),
            "project_name": review.get("project_name"),
            "created_at": review.get("created_at").isoformat() if review.get("created_at") else None,
            "updated_at": review.get("updated_at").isoformat() if review.get("updated_at") else None,
            "days_remaining": days_remaining,
            "expires_at": expires_at.isoformat() if expires_at else None,
            "task_type": review.get("task_type"),
            "contracts": review.get("contracts", []),
            "proposals": review.get("proposals", []),
            "messages": review.get("messages", []),
            "summary_data": review.get("summary_data"),
            "negotiation_summary": review.get("negotiation_summary"),
            "scope_data": review.get("scope_data"),
            "analysis_result": review.get("analysis_result")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Get Contract Review Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/contract-reviews/{review_id}")
async def delete_contract_review(review_id: str):
    """Delete a contract review from history."""
    try:
        if not ObjectId.is_valid(review_id):
            raise HTTPException(status_code=400, detail="Invalid review ID")
        
        result = await db.contract_reviews.delete_one({"_id": ObjectId(review_id)})
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Contract review not found")
        
        return {"status": "deleted", "review_id": review_id}
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Delete Contract Review Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/documents")
async def list_documents(session_id: str = None):
    """List documents, optionally filtered by session."""
    query = {}
    if session_id:
        query["session_id"] = session_id
    
    cursor = db.documents.find(query).sort("upload_date", -1)
    docs = await cursor.to_list(length=100)
    return [
        {
            "file_id": str(doc["_id"]),
            "filename": doc.get("filename"),
            "document_type": doc.get("document_type", "contract"),
            "is_active": doc.get("is_active", False),
            "upload_date": doc.get("upload_date").isoformat() if doc.get("upload_date") else None,
            "size": doc.get("size"),
            "text_preview": doc.get("extracted_text_preview", "")[:100],
            "session_id": doc.get("session_id")
        }
        for doc in docs
    ]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
