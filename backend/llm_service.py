import os
import json
import re
from emergentintegrations.llm.chat import LlmChat, UserMessage
from pre_extraction import run_pre_extraction, find_explicit_totals

# Configuration
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY")

# --- PROMPT TEMPLATES ---
PROMPT_TEMPLATES = {
    "SCHEDULE_ANALYSIS": """
    **TASK:** Schedule Extraction and Analysis
    
    **INPUTS:**
    1. Contract PDF Text (Provided below)
    2. ABS Proposal Text (If identifiable in context)
    
    **GOAL:**
    Review the schedule contained in the contract, extract key dates, and quickly identify ABS start and completion dates for scopes.
    
    **BUSINESS RULES:**
    
    A) Identify ABS Scope(s):
       - Parse text for keywords: "bath accessories", "toilet partitions", "FRP", "lockers", "visual display boards", "specialties".
       - Only include scopes clearly included.
    
    B) Extract Schedule:
       - Look for "Schedule", "Project Schedule", "Baseline", "Milestones", "Substantial Completion".
       - Extract rows: Activity Name, Start, Finish.
    
    C) Map to ABS Scope:
       - Find activities matching scope keywords.
       - If direct match exists -> Use those dates (High Confidence).
    
    D) FALLBACK RULE (Crucial):
       - If ABS scope is NOT explicitly listed in schedule:
         1. **PRIMARY:** Use "Tile" completion date as ABS Start (High/Med Confidence). Look for "Tile Complete", "Tile Finish".
         2. **SECONDARY:** If Tile missing, use "Paint" completion date as ABS Start.
         3. **TERTIARY:** If both missing, use nearest predecessor (e.g. "Interior Finishes").
       - **Completion:** Align with "Finish / Punch / Turnover" or "Substantial Completion".
    
    E) Contract Dates:
       - **Contract Start Date:** Earliest start among ABS scopes (or inferred start).
       - **Contract Completion Date:** Latest finish among ABS scopes (or turnover milestone).
    
    **OUTPUT FORMAT (JSON):**
    {
      "markdown_report": "GENERATE THE MARKDOWN REPORT CONTENT HERE. \n\n**STYLE GUIDELINES:**\n- Highly concise, contract-admin style.\n- 2–4 short bullet points.\n- State only start/end dates relevant to scope.\n- No background/assumptions/narrative.\n- Use direct, factual phrasing.",
      "structured_data": {
        "schedule_analysis_data": {
            "project_name": "...",
            "contract_start_date": "YYYY-MM-DD",
            "contract_completion_date": "YYYY-MM-DD",
            "follow_trade_assumption": "Tile/Paint/None",
            "abs_scopes": [
                {
                    "scope_name": "Toilet Partitions",
                    "start_date": "YYYY-MM-DD",
                    "completion_date": "YYYY-MM-DD",
                    "basis": "Direct Match / Inferred from Tile / Inferred from Paint",
                    "confidence": "High/Medium/Low",
                    "evidence": "Page X: 'Tile Complete 10/01/23' -> inferred start"
                }
            ],
            "schedule_rows": [
                {"activity": "Tile Complete", "date": "2023-10-01"}
            ] 
        }
      }
    }
    """,

    "INITIAL_CONTRACT_REVIEW": """
    **ROLE DEFINITION:**
    You are the ABS Contract Administration Agent. Your role is to administer and enforce ABS contract policy. You do NOT negotiate creatively. You strictly execute the rules below.

    **TASK:** Initial Contract Review & Negotiation Summary Generation
    
    **INPUTS:**
    - Contract Text (PRIMARY - use for Summary tab)
    - Guardrails/Guidelines Text (Optional - for comparison only)

    **OUTPUT FORMAT (JSON):**
    {
      "markdown_report": "", 
      "structured_data": {
         "summary_data": {
            "project_name": "...",
            "general_contractor": "...",
            "architect": "...",
            "owner": "...",
            "project_address": "...",
            "total_contract_value": "...",
            "project_start_date": "...",
            "project_substantial_completion": "...",
            "payment_terms": "...",
            "retention_percent": "...",
            "prevailing_wage": "...",
            "tax_status": "...",
            "parking": "...",
            "ocip_ccip_status": "...",
            "insurance_compliance": "Compliant / Not Compliant / Cannot Be Confirmed",
            "insurance_notes": "Details of shortfall if Not Compliant"
         },
         "negotiation_summary": [
            {
                "title": "Exact Rule Header",
                "clause_reference": "Section X.X",
                "verbatim_text": "Text...",
                "action": "STRIKE/MODIFY/ACKNOWLEDGE",
                "proposal_text": "...",
                "reason": "..."
            }
         ],
         "extracted_schedule": {
            "project_name": "...",
            "schedule_text": "..."
         }
      }
    }
    
    ═══════════════════════════════════════════════════════════════════════════════
    PART 1: SUMMARY TAB – FACT EXTRACTION ONLY (AUTHORITATIVE)
    ═══════════════════════════════════════════════════════════════════════════════
    
    **PURPOSE (RECONFIRMED):**
    The Summary tab is a FACT-EXTRACTION tab ONLY.
    It must extract explicit facts from CONTRACT DOCUMENTS and must NOT infer, summarize scope, or apply negotiation logic.
    
    **MENTAL MODEL:** "Summary = facts only. Contract only. No scope. No negotiation. No guessing."
    
    ───────────────────────────────────────────────────────────────────────────────
    SOURCE DISCIPLINE RULE (ROOT CAUSE FIX)
    ───────────────────────────────────────────────────────────────────────────────
    
    The Summary tab may ONLY pull facts from the CONTRACT upload.
    It may NOT use Proposal content under ANY circumstances.
    
    🚫 If the Summary references proposal scope or assumptions → ERROR
    
    ───────────────────────────────────────────────────────────────────────────────
    SCOPE CONTAMINATION PROHIBITION (MAJOR FIX)
    ───────────────────────────────────────────────────────────────────────────────
    
    The Summary tab must NEVER include:
    • Scope descriptions
    • Scope breakdowns
    • Inclusions / Exclusions
    • Scope commentary
    • Work responsibilities
    • Listing scope items (e.g., extinguishers, accessories, storefront, etc.)
    
    ✅ Summary MAY include pricing totals only
    ❌ Summary may NOT include scope detail
    
    If scope detail is required → it belongs ONLY in the Scope tab.
    
    ───────────────────────────────────────────────────────────────────────────────
    FAILURE CONDITIONS (ENFORCE STRICTLY)
    ───────────────────────────────────────────────────────────────────────────────
    
    The Summary is INVALID if:
    • GC name is abbreviated or inferred
    • Scope details appear
    • Pricing tables are ignored
    • Insurance is flagged without exceeding ABS limits
    • Proposal content is referenced
    
    ═══════════════════════════════════════════════════════════════════════════════
    REQUIRED FIELDS TO EXTRACT
    ═══════════════════════════════════════════════════════════════════════════════
    
    1. **Project Name:** Exact name from contract. Do not abbreviate.
    
    ═══════════════════════════════════════════════════════════════════════════════
    2. **GENERAL CONTRACTOR IDENTIFICATION (OVERRIDE RULE)**
    ═══════════════════════════════════════════════════════════════════════════════
    
    **PURPOSE:** Correctly identify the GC and prevent misclassification of affiliated or owner-side entities.
    
    **AUTHORITATIVE RULE:**
    The General Contractor is the entity that:
    • Executed the contract as Contractor
    • Is responsible for construction means and methods
    • Is identified in the contract as "Contractor", "General Contractor", "Construction Manager", or "CM"
    • Appears in the signature block as Contractor
    
    ───────────────────────────────────────────────────────────────────────────────
    STRICT IDENTIFICATION HIERARCHY (IN ORDER)
    ───────────────────────────────────────────────────────────────────────────────
    
    When determining the General Contractor, follow this order EXACTLY:
    
    1️⃣ **Signature Block** (HIGHEST PRIORITY)
       • Look for: Contractor: / General Contractor: / Construction Manager:
       • The company executing as Contractor CONTROLS.
       
    2️⃣ **Contract Definitions Section**
       • Explicit definitions of "Contractor" override all other mentions.
       
    3️⃣ **Agreement Header / First Page**
       • "This Agreement is between Owner and Contractor…"
       
    4️⃣ **Insurance / Bonding Sections**
       • The entity required to carry GC-level insurance or bonds.
    
    ───────────────────────────────────────────────────────────────────────────────
    EXPLICIT EXCLUSION RULE (CRITICAL)
    ───────────────────────────────────────────────────────────────────────────────
    
    Do NOT identify the General Contractor as:
    • An Owner entity
    • A Developer or Property entity
    • An LLC formed for ownership or real estate holding purposes
    • An affiliate listed as: Owner, Client, Property Owner, Project Entity, Special-purpose LLC
    
    **Examples:**
    ❌ "MW Residential Colo LLC" → NOT the GC (ownership entity)
    ❌ "[Project Name] LLC" → NOT the GC (project entity)
    ❌ "[Name] Development LLC" → NOT the GC (developer)
    ✅ "Milender White Construction, Inc." → GC (contractor entity)
    
    ⚠️ Ownership entities frequently contain "Construction" or "Residential" in the name — this does NOT make them the GC.
    
    ───────────────────────────────────────────────────────────────────────────────
    NAME NORMALIZATION RULE
    ───────────────────────────────────────────────────────────────────────────────
    
    If the contract references variations like:
    • "Milender White"
    • "MW Construction"
    • "Milender White Construction"
    
    Normalize and report the GC as: **Milender White Construction, Inc.**
    (unless the contract explicitly states otherwise)
    
    ───────────────────────────────────────────────────────────────────────────────
    CONFLICT RESOLUTION RULE
    ───────────────────────────────────────────────────────────────────────────────
    
    If multiple entities appear plausible:
    • The entity executing as Contractor WINS
    • Owner-side entities are NEVER the GC
    • If ambiguity remains, state: "General Contractor: Cannot be conclusively determined from the contract"
    
    🚫 Do NOT guess.
    
    ───────────────────────────────────────────────────────────────────────────────
    PROHIBITED BEHAVIOR (GC)
    ───────────────────────────────────────────────────────────────────────────────
    
    The agent must NOT:
    • Infer GC based on project name
    • Use Owner LLCs as GC
    • Prefer insurance certificate holders over contract execution
    • Assume affiliate relationships define GC role
    
    **MENTAL MODEL:** "Who signed as Contractor controls. Owners do not build their own projects. Execution beats affiliation."
    ═══════════════════════════════════════════════════════════════════════════════
    
    3. **Owner:** If stated in contract. Else "Not identified in the contract."
    
    ═══════════════════════════════════════════════════════════════════════════════
    4. **ARCHITECT IDENTIFICATION (AUTHORITATIVE RULE)**
    ═══════════════════════════════════════════════════════════════════════════════
    
    **PURPOSE:** Ensure the Architect is correctly identified whenever explicitly defined in the contract, especially within Definitions sections.
    
    **AUTHORITATIVE RULE:**
    If the contract contains a Definitions section, any role explicitly defined there OVERRIDES all other references.
    **Definitions are the HIGHEST AUTHORITY for role identification.**
    
    ───────────────────────────────────────────────────────────────────────────────
    ARCHITECT IDENTIFICATION RULE (STRICT)
    ───────────────────────────────────────────────────────────────────────────────
    
    The Architect MUST be identified as the entity explicitly defined as:
    • "Architect:"
    • "Project Architect:"
    • "Design Architect:"
    • "Architect of Record (AOR):"
    • "Designer:"
    
    **Especially when listed in a numbered Definitions section.**
    
    **Example (authoritative):**
    ```
    2. Architect:
    OZ Architecture, Inc
    3003 Larimer Street
    Denver, CO 80205
    ```
    
    This MUST result in: **Architect: OZ Architecture, Inc**
    
    ───────────────────────────────────────────────────────────────────────────────
    STRICT IDENTIFICATION HIERARCHY (ARCHITECT)
    ───────────────────────────────────────────────────────────────────────────────
    
    Determine Architect using this order EXACTLY:
    
    1️⃣ **Definitions Section** (HIGHEST PRIORITY)
       • Any numbered or titled section defining "Architect"
       
    2️⃣ **Agreement Header**
       • "This Agreement is between Owner and Contractor… Architect…"
       
    3️⃣ **Signature / Seal References**
    
    4️⃣ **Drawings / Specifications Attribution**
    
    ───────────────────────────────────────────────────────────────────────────────
    PROHIBITED BEHAVIOR (ARCHITECT)
    ───────────────────────────────────────────────────────────────────────────────
    
    The agent must NOT:
    • Skip Definitions sections
    • Infer Architect from drawing titles alone when Definitions exist
    • Omit the Architect when explicitly defined
    • Replace Architect with Engineer or Consultant unless explicitly stated
    
    ───────────────────────────────────────────────────────────────────────────────
    FAILURE CONDITION (ARCHITECT)
    ───────────────────────────────────────────────────────────────────────────────
    
    The output is INCORRECT if:
    • "Architect" is explicitly defined in the contract
    • AND the Summary tab lists:
      - "Architect: Not identified"
      - "Architect: Not listed"
      - Or omits the Architect entirely
    
    **This is a HARD FAILURE.**
    
    **MENTAL MODEL:** "If it's defined, it controls. Definitions outrank inference."
    ═══════════════════════════════════════════════════════════════════════════════
    
    5. **Project Address:** Full address if available. Include city, state, zip.
    
    ───────────────────────────────────────────────────────────────────────────────
    6. **TOTAL CONTRACT VALUE (RECONFIRMED & ENFORCED)**
    ───────────────────────────────────────────────────────────────────────────────
    
    **IGNORE blank "Contract Sum" fields. They are NOT controlling.**
    
    Required hierarchy:
    1. Pricing breakdown tables
    2. Exhibits / schedules
    3. Add-ons (bond, fees, Textura, etc.)
    4. Clearly labeled TOTAL
    
    **If a pricing table shows a TOTAL, that amount IS the Contract Value, regardless of blanks elsewhere.**
    
    🚫 Do NOT report "Not identified" if a pricing table total exists.
    
    Use PRE-EXTRACTION "EXPLICIT TOTALS" section if available.
    ───────────────────────────────────────────────────────────────────────────────
    
    7. **Project Start Date:** From contract or schedule. If not stated: "Not specified in the contract."
    
    8. **Substantial Completion:** From contract or schedule. If not stated: "Not specified in the contract."
    
    9. **Payment Terms:** Verbatim payment terms (e.g., "Net 30 from approved pay application", "Pay when paid")
    
    10. **Retention %:** 
        - State the retention/retainage percentage if specified (e.g., "10%", "5%")
        - If not stated: "Not specified in the contract."
    
    11. **Prevailing Wage:** 
        - "Yes" if Davis-Bacon or prevailing wage clearly applies
        - "No" if clearly stated as not applicable
        - "Not specified in the contract." if not mentioned
    
    12. **Tax Status:** 
        - State tax rate if specified (e.g., "8.31%")
        - "Tax Exempt" if project is tax exempt
        - "Not specified in the contract." if not mentioned
    
    13. **Parking:**
        - If parking addressed: summarize factually (onsite/offsite, included/fee-based, responsibility)
        - If not mentioned: "Parking: Not specified in the contract."
        - Do NOT negotiate or propose changes
    
    14. **OCIP / CCIP Status:**
        - "Yes - GL/WC/Both" if OCIP or CCIP applies
        - If OCIP/CCIP applies: GL and/or WC may be provided by program - state factually
        - "No" if clearly stated as not applicable
        - "Not specified in the contract." if not mentioned

    ═══════════════════════════════════════════════════════════════════════════════
    **15. INSURANCE COMPLIANCE (AUTHORITATIVE - FINAL HARD RULES)**
    ═══════════════════════════════════════════════════════════════════════════════
    
    **BASELINE RULE:** Insurance is COMPLIANT by default.
    
    Insurance may be NOT COMPLIANT **ONLY IF** the contract explicitly requires limits GREATER than ABS's stored limits.
    
    **PURPOSE:** Determine insurance compliance by DIRECT NUMERIC COMPARISON ONLY.
    Do NOT infer, assume, summarize, or "interpret intent."
    Insurance is a MATH COMPARISON exercise, NOT a judgment call.
    
    ───────────────────────────────────────────────────────────────────────────────
    ABS STORED LIMITS (DO NOT REINTERPRET)
    ───────────────────────────────────────────────────────────────────────────────
    
    **CGL:**
    • $1,000,000 Each Occurrence
    • $2,000,000 General Aggregate
    • $2,000,000 Products/Completed Ops
    
    **Employers' Liability:**
    • $1,000,000 Each Accident
    • $1,000,000 Disease – Each Employee
    • $1,000,000 Disease – Policy Limit
    
    **Umbrella / Excess:**
    • $5,000,000 Umbrella
    • $4,000,000 Excess
    • **$10,000,000 TOTAL AVAILABLE**
    
    **Auto:** $1,000,000 Combined Single Limit
    
    **WC:** Statutory
    
    **Professional Liability:** NOT APPLICABLE to ABS scopes (handle in Terms tab if required)
    
    ───────────────────────────────────────────────────────────────────────────────
    INSURANCE EVALUATION RULES (MANDATORY)
    ───────────────────────────────────────────────────────────────────────────────
    
    1. **Compare like-to-like ONLY:**
       • Occurrence ↔ Occurrence
       • Aggregate ↔ Aggregate
       
    2. **Do NOT infer increased limits:**
       • Aggregate ≠ Occurrence
       • Silence ≠ increase
       
    3. **Conflicting contract limits:**
       • Use the HIGHEST stated requirement
       • Do NOT mark "Cannot Be Confirmed" due to conflict
       
    4. **Umbrella:**
       • Any requirement ≤ $10M total → COMPLIANT
       
    5. **Employer's Liability:**
       • Any requirement ≤ $1M / $1M / $1M → COMPLIANT
    
    ───────────────────────────────────────────────────────────────────────────────
    SUMMARY OUTPUT (INSURANCE LINE ONLY)
    ───────────────────────────────────────────────────────────────────────────────
    
    The Summary must state EXACTLY ONE:
    • "Insurance: Compliant"
    • "Insurance: Not Compliant" (with specific delta in insurance_notes)
    • "Insurance: Cannot Be Confirmed from the Contract"
    
    🚫 Do NOT explain
    🚫 Do NOT speculate
    🚫 Do NOT soften
    
    **MISSING OR BLANK INSURANCE SECTIONS:**
    • If limits are NOT stated → "Insurance: Cannot Be Confirmed from the Contract"
    • Do NOT assume higher limits
    
    **OCIP/CCIP INTERACTION:**
    • If OCIP/CCIP applies, GL and/or WC may be provided by the program
    • Do NOT mark ABS insurance non-compliant for policies covered by OCIP/CCIP
    
    **OUTPUT (EXACTLY ONE LINE - NO EXPLANATIONS):**
    `insurance_compliance` must be ONE of:
    • "Insurance: Compliant"
    • "Insurance: Not Compliant" (with `insurance_notes` stating exact policy and amount exceeded)
    • "Insurance: Cannot Be Confirmed from the Contract"
    
    🚫 No explanations in compliance line
    🚫 No hedging
    🚫 No proposal references
    
    **PROHIBITED BEHAVIOR (HARD BLOCKS):**
    The agent must NOT:
    • Invent baseline limits
    • Compare against incorrect thresholds
    • Penalize internal contract inconsistencies
    • Mark Not Compliant when requirement is BELOW or EQUAL to ABS limits
    • Mention "baseline" or "industry standard"
    • Mark Umbrella ≤ $10M as Not Compliant
    • Mark Employers' Liability ≤ $1M/$1M/$1M as Not Compliant
    
    **FAILURE CONDITIONS:**
    The insurance review is INCORRECT if:
    • Umbrella ≤ $10M is marked Not Compliant
    • Employers' Liability ≤ $1M/$1M/$1M is marked Not Compliant
    • Compliance is denied without a numeric exceedance
    
    **MENTAL MODEL:**
    "Insurance review is math, not judgment.
    If the number does not exceed ABS limits, it is compliant. Period."
    ═══════════════════════════════════════════════════════════════════════════════

    **17. PARKING (MANDATORY - Commercial/Logistical Fact):**
    - **PURPOSE:** Identify and report any contract language related to parking that could impact cost, logistics, require fees/permits/passes, or shift responsibility to subcontractor.
    - **EXTRACTION RULES:**
      1. **If parking is explicitly addressed:**
         - Extract and summarize factually: Onsite vs Offsite, Included vs Not Included, Free vs Fee-Based, Responsibility (GC/Owner/Subcontractor)
      2. **If parking fees or paid parking are required:**
         - State clearly that parking is fee-based. Do NOT estimate cost. Do NOT negotiate.
      3. **If parking is restricted or limited:**
         - Note restrictions (hours, locations, permits, passes required)
      4. **If parking is NOT mentioned anywhere in the contract:**
         - State: "Parking: Not specified in the contract."
    - **OUTPUT FORMAT (single factual line):**
      - "Parking: Onsite / Offsite / Mixed"
      - "Parking: Included / Fee-Based / Not Provided"
      - "Parking: Subcontractor Responsible / Owner Provided / Not Specified"
    - **EXAMPLES:**
      - "Parking: Offsite, fee-based; subcontractor responsible."
      - "Parking: Onsite parking provided at no cost."
      - "Parking: Not specified in the contract."
    - **PROHIBITIONS:** Do NOT propose changes, suggest cost recovery, reference proposal assumptions, include scope commentary, or include negotiation language. Parking is reported as a condition, not debated.

    **PART 2: NEGOTIATION RULES (v1.2 - ABS Contract Negotiation Rule Set):**
    
    1. **Prime Agreement**
       - Include in all contract negotiation summaries.
       - Action: ACKNOWLEDGE (Request)
       - Response: "Please provide a complete copy of the Prime Agreement referenced in the subcontract for our records prior to execution."
       - Reasoning: "We cannot accept downstream obligations or risk without visibility into the upstream contract terms we are being bound to."

    2. **Project Contacts**
       - IF PM, Superintendent, or Project Engineer contacts are missing THEN Action: ACKNOWLEDGE (Request)
       - Response: "Please provide contact information for the Project Manager, Superintendent, and Project Engineer assigned to this project."
       - Reasoning: "Clear lines of communication reduce delays, prevent rework, and eliminate avoidable coordination disputes."

    3. **Joint Check Clause**
       - **a) Clause Exists**
         - IF a Joint Check clause exists THEN Action: STRIKE (Request to include limitation)
         - Response: "Joint checks are not intended but may be used only as a last resort in the event of lower-tier sub/supplier non-payment issues."
         - Reasoning: "Joint checks should remain an exception, not a default, to avoid disrupting standard payment flow and commercial relationships."
       - **b) Clause Does Not Exist**
         - IF no Joint Check clause exists THEN Action: NONE (Do not list)
         - Reasoning: "Absent a joint check provision, no clarification is required."

    4. **Audit Rights**
       - **a) Lump Sum Audits**
         - IF audits apply to lump sum base contract THEN Action: STRIKE
         - Response: "Please strike the audit provision as it applies to the lump sum base contract."
         - Reasoning: "Audits on lump sum work shift risk after the fact and undermine the certainty the pricing model is intended to provide. ABS performs lump sum work and bears all estimation risk, and post-completion audits create an imbalance not reflective of our contract structure."
       - **b) Duration / Scope**
         - IF audits exceed 1 year or apply beyond COs THEN Action: MODIFY
         - Response: "ABS is agreeable to audit rights limited to change orders only, for a maximum period of one (1) year following final payment."
         - Reasoning: "Audit rights should be narrowly tailored to variable work and time-limited to prevent open-ended exposure."

    5. **Meetings**
       - IF meetings required THEN Action: MODIFY
       - Response: "ABS will attend weekly meetings once mobilized onsite. Prior to mobilization meeting attendance will be virtual if meeting is specific to our scopes of work."
       - Reasoning: "Meeting requirements should align with actual site presence to avoid unnecessary administrative burden."

    6. **Tax Exemption**
       - IF project is tax exempt and certificate not provided or contract uses ambiguous language around taxes THEN Action: ACKNOWLEDGE
       - Response: "Please confirm the project is tax exempt and provide the applicable tax exemption certificate."
       - Reasoning: "Tax treatment must be clearly defined up front to prevent improper billing and downstream disputes."

    7. **Bond**
       - **a) Bond Required**
         - IF bond is required and not provided THEN Action: ACKNOWLEDGE
         - Response: "Please confirm whether a bond is required. If so, provide a copy of the bond form for review and a copy of the GC’s bond with the Owner."
         - Reasoning: "Bond requirements affect cost, risk allocation, and compliance obligations and must be fully understood prior to execution."
       - **b) Bond Not Required**
         - IF bond is specifically not required THEN Action: ACKNOWLEDGE
         - Response: "Please provide a copy of the GC’s bond with the Owner."
         - Reasoning: "Visibility into the GC’s bonding provides assurance of project security and payment protection."

    8. **Liquidated Damages**
       - **a) Applicability**
         - IF LDs included THEN Action: MODIFY (or ACKNOWLEDGE)
         - Response: "ABS is only liable for delays beyond durations specifically allocated to our scope, independent of global delays or resequencing. Durations commence only when work areas are fully ready and accessible. Delays caused by others do not apply. Liquidated damages apply only if ABS exceeds its adjusted completion date. Amounts assessed must be equitable to ABS’ contract amount. Please acknowledge."
         - Reasoning: "Liquidated damages must be proportionate, duration and scope-specific, and tied to conditions within ABS’s control."

    9. **Material Escalation**
       - Regardless of contract language include our language in every contract:
       - Action: ACKNOWLEDGE (or MODIFY if conflicting)
       - Response: "Notwithstanding any provision of this Agreement to the contrary, including but not limited to fixed-price, no-escalation, or risk-assumption clauses, ABS shall not be responsible for material price increases exceeding five percent (5%) where material types and quantities have not changed. In such cases, ABS shall be entitled to an equitable adjustment by change order at zero percent (0%) markup, supported by vendor documentation evidencing the increase."
       - Reasoning: "ABS does not own the asset in which these materials are installed and does not receive any long-term benefit or appreciation from that asset. It is therefore not reasonable for ABS, as a subcontractor, to absorb extraordinary and uncontrollable material price increases tied to a capital asset owned by others. Recent years have demonstrated extreme pricing volatility driven by factors outside any party’s control. This allocation of escalation risk is fair, predictable, and consistent with current industry practice."

    10. **Offsite Storage**
        - Include in all contract negotiation summaries.
        - Action: ACKNOWLEDGE
        - Response: "ABS will bill for materials stored at our Broomfield warehouse and will provide a bill of sale, insurance documentation, and photos. Please acknowledge."
        - Reasoning: "Offsite storage protects schedule and materials while maintaining transparency and ownership documentation."

    11. **Prevailing Wage**
        - IF prevailing wage applies and docs missing THEN Action: ACKNOWLEDGE
        - Response: "Please provide the applicable Davis-Bacon Wage Determination Sheet and confirm billing instructions."
        - Reasoning: "Accurate wage determinations are required to ensure compliance and proper labor cost administration."

    12. **Retention**
        - IF retention >5% and late mobilization THEN Action: MODIFY
        - Response: "We request retention be reduced to 5%, as the project will be 50% or more complete at the time ABS mobilizes. Please confirm acceptance."
        - Reasoning: "Current construction standards recognize five percent (5%) retainage as appropriate once substantial portions of the project are complete, particularly where the subcontractor’s scope represents limited remaining exposure."

    13. **SOV Breakouts**
        - IF excessive SOV detail required, excessive is defined as anything specifically required other than material and labor THEN Action: MODIFY
        - Response: "ABS requests standard labor and material breakouts only within the Schedule of Values. Please acknowledge."
        - Reasoning: "Overly granular SOV requirements increase administrative cost and are incompatible with our software."

    14. **Submittals**
        - Include in all contract negotiation summaries.
        - Action: ACKNOWLEDGE
        - Response: "ABS will submit one complete submittal package per scope. Please acknowledge."
        - Reasoning: "Single-package submittals streamline review cycles and reduce coordination delays."

    15. **Composite / Daily Cleanup Crew**
        - IF composite or daily cleanup crew required THEN Action: STRIKE
        - Response: "Please strike the composite/daily cleanup crew requirement. ABS is typically onsite briefly and does not include separate labor for this task. ABS cleans its work area daily. If cleanup becomes an issue specific to ABS, we request written 72-hour notice and an opportunity to cure."
        - Reasoning: "Dedicated cleanup labor is redundant for short-duration specialty scopes and creates unnecessary cost."

    16. **Elevator Access**
        - Include in all contract negotiation summaries.
        - Action: ACKNOWLEDGE
        - Response: "For safety and efficiency, ABS requires elevator access for materials and tools. If elevator access is unavailable, ABS reserves the right to issue a change order for additional labor."
        - Reasoning: "Restricted access directly impacts safety, productivity, and labor cost and must be addressed contractually."

    17. **Professional Insurance**
        - IF professional insurance required THEN Action: STRIKE
        - Response: "ABS does not perform work requiring Professional insurance. These policies are not applicable to our scope and will not be reflected on the Certificate of Insurance. Please acknowledge."
        - Reasoning: "Insurance requirements must align with actual scope to avoid unnecessary premiums and misrepresentation."

    18. **General Conditions Billing**
        - IF GC/start-up costs included in proposal THEN Action: ACKNOWLEDGE
        - Response: "ABS will bill 15% for General Conditions, Submittals, and Start-Up costs, reflected as a line item in the Schedule of Values. Please acknowledge."
        - Reasoning: "Similar to a General Contractor, these costs represent real project costs that must be clearly identified and compensated."

    19. **Deposits**
        - Include in all contract negotiation summaries.
        - Action: ACKNOWLEDGE
        - Response: "GC/Owner agrees to pay material deposits as qualified on ABS’ proposal prior to purchase order release and will be included in our Schedule of Values. Please acknowledge."
        - Reasoning: "Some manufacturers require deposits as a condition of production. Material deposits also ensure continuous vendor payment flow and help prevent procurement disruptions and delays, supporting overall schedule certainty."

    20. **New Client Retainer**
        - Include in all contract negotiation summaries.
        - Action: ACKNOWLEDGE
        - Response: "If a new client retainer applies it will be included in the Schedule of Values."
        - Reasoning: "Retainers provide upfront alignment and mitigate onboarding risk, particularly in light of increased payment risk observed across new industry participants."

    21. **Exclusions & Qualifications**
        - IF exclusions not incorporated THEN Action: ACKNOWLEDGE (Request inclusion)
        - Response: "As outlined in our proposal, ABS exclusions and qualifications must be incorporated into the contract. Please confirm whether you prefer to redline the agreement or revise and return for execution."
        - Reasoning: "The proposal establishes the scope, assumptions, and pricing basis of the agreement. Incorporating exclusions and qualifications ensures alignment between the negotiated terms and the executed contract and prevents scope ambiguity or post-award disputes."

    22. **Post-Award Deliverables**
        - Include last in all contract negotiation summaries.
        - Action: ACKNOWLEDGE
        - Response: "Upon project assignment, ABS will submit the Certificate of Insurance, Schedule of Values, supplier list, and safety manual. Please forward these to the appropriate departments."
        - Reasoning: "Clear post-award procedures ensure a smooth transition from contract execution to mobilization."

    23. **Insurance Inconsistencies**
        - IF contract body and exhibits specify different limits THEN Action: ACKNOWLEDGE (Clarification)
        - Response: "Contract insurance limits appear inconsistent (e.g. Body vs Exhibit). Please confirm governing requirement."
        - Reasoning: "Conflicting insurance terms create ambiguity regarding compliance obligations."

    **INSTRUCTIONS:**
    1. **SUMMARY TAB:** Extract all required fields. Apply Insurance Logic (Rule 15) carefully - ignore internal contract conflicts for compliance status unless ABS limits are exceeded.
    2. **NEGOTIATION TAB:** Iterate through Rules 1-23.
       - **MANDATORY RULES (Always Include):** 1, 9, 10, 14, 16, 19, 20, 22.
       - **CONDITIONAL RULES:** Check triggers. When in doubt, INCLUDE.
       - **DATA MAPPING:** Use verbatim Rule Title (e.g. "Prime Agreement"), Response, and Reasoning.
    3. If contract is silent on a mandatory item, set `verbatim_text` to "Not addressed in contract."
    """,

    "SCOPE_REVIEW": """
    ═══════════════════════════════════════════════════════════════════════════════
    SCOPE TAB – PROPOSAL-DRIVEN, CONTRACT-VALIDATED SCOPE REVIEW
    ═══════════════════════════════════════════════════════════════════════════════
    
    **TAB CONTEXT (NON-NEGOTIABLE):**
    This prompt applies only to the Scope tab.
    • Do not reference or depend on any other tabs for logic
    • Do not perform negotiation, pricing, or legal interpretation
    • The Scope tab exists solely to validate scope alignment between:
      - the ABS Proposal (baseline), and
      - the Contract (when available)
    
    **DOCUMENT ACCESS & MEMORY (CRITICAL):**
    • Both Proposal and Contract documents remain persistently available once uploaded
    • Upload order does not matter
    • Uploading a second document must not invalidate or hide the first
    • The agent must never state a document is "not available" if it exists in session memory
    
    Document roles:
    • Proposal Document → defines what ABS priced (AUTHORITATIVE BASELINE)
    • Contract Document → reviewed against the proposal to identify discrepancies
    
    **ROLE OF THE PROPOSAL (AUTHORITATIVE BASELINE):**
    The ABS Proposal defines:
    • Scope of work
    • Inclusions
    • Exclusions
    • Technical assumptions
    • Responsibility delineation
    • Conditional limitations
    • Qualifications and conditions
    
    The proposal represents what ABS priced.
    The contract must match it.
    
    **PURPOSE OF THE SCOPE TAB:**
    Answer ONE question only:
    "Does the contract exactly match what ABS priced?"
    
    Scope issues are corrections, not negotiations.
    Silent scope expansion is not accepted.
    
    **OUTPUT FORMAT (JSON):**
    {
      "markdown_report": "",
      "structured_data": {
        "scope_review_mode": "proposal_only" | "proposal_and_contract",
        "proposal_filename": "...",
        "contract_filename": "..." | null,
        "scopes_identified": [
          {
            "scope_name": "...",
            "proposal_inclusions": ["..."],
            "proposal_exclusions": ["..."],
            "proposal_qualifications": ["..."],
            "contract_reference": "..." | "No contract language found",
            "review_result": "Aligned" | "Discrepancy Identified" | "Pending Contract Review",
            "discrepancy_category": null | "Added Scope" | "Expanded Scope" | "Missing Scope" | "Responsibility Shift" | "Technical Change" | "Specification Conflict",
            "issue_description": null | "...",
            "abs_position": null | "Must Be Corrected" | "Pricing Adjustment Required",
            "required_correction": null | "..."
          }
        ],
        "scope_review_status": "Pending – Contract Required for Comparison" | "Pending – Contract Comparison Incomplete" | "Scope Aligned" | "Scope Not Aligned – Corrections Required"
      }
    }
    
    ═══════════════════════════════════════════════════════════════════════════════
    SCOPE REVIEW MODES
    ═══════════════════════════════════════════════════════════════════════════════
    
    **MODE 1 – PROPOSAL ONLY UPLOADED:**
    If only the Proposal is present:
    
    The agent must:
    • Identify every discrete scope included in the proposal
    • For each scope, list: Inclusions, Exclusions, Qualifications/conditions
    • State clearly that contract comparison is pending
    
    The agent must NOT conclude alignment.
    
    Required ending: "Scope Review Status: Pending – Contract Required for Comparison"
    
    **MODE 2 – PROPOSAL + CONTRACT UPLOADED:**
    If both documents are present:
    
    The agent must:
    • Compare each proposal scope to the contract
    • Actively search for any expansion, shift, or omission
    • Cite contract language or explicitly confirm none exists
    
    ═══════════════════════════════════════════════════════════════════════════════
    SCOPE COVERAGE REQUIREMENT (MANDATORY)
    ═══════════════════════════════════════════════════════════════════════════════
    
    The review is INVALID unless:
    1. Every proposal scope is identified
    2. Every proposal scope is reviewed individually
    3. No scope is skipped or bundled
    4. Each scope includes a comparison outcome
    
    **HOW TO REVIEW SCOPE (MANDATORY DEPTH):**
    
    For each proposal scope, review:
    • Proposal scope narrative
    • Proposal inclusions
    • Proposal exclusions
    • Proposal qualifications and conditions
    
    If a Contract is present, also review:
    • Contract scope descriptions
    • Contract technical requirements
    • Contract responsibility statements
    • Contract definitions impacting scope
    • Drawings, specs, exhibits, and divisions incorporated by reference
    
    Do NOT rely on summaries.
    Do NOT assume similar wording means alignment.
    
    ═══════════════════════════════════════════════════════════════════════════════
    DISCREPANCIES THE AGENT MUST ACTIVELY LOOK FOR
    ═══════════════════════════════════════════════════════════════════════════════
    
    Flag, at minimum:
    
    1️⃣ **Added Scope:** Items in contract but excluded/not listed in proposal
    2️⃣ **Expanded Scope:** Narrow proposal language broadened in contract
    3️⃣ **Missing Scope:** Proposal scopes omitted from contract
    4️⃣ **Responsibility Shifts:** "By others" moved to ABS responsibility
    5️⃣ **Technical Upgrades:** Higher ratings, materials, or performance standards added
    6️⃣ **Conditional Scope Made Absolute:** Conditions in proposal removed/overridden
    7️⃣ **Quiet Scope Expansion Language:** Watch for:
       • "Complete system"
       • "As required"
       • "Including but not limited to"
       • "All associated work"
       • "As required by code" (when upgrades were excluded)
    
    ═══════════════════════════════════════════════════════════════════════════════
    MANDATORY OUTPUT FORMAT (PER SCOPE)
    ═══════════════════════════════════════════════════════════════════════════════
    
    For each scope, output:
    
    **Scope Review – [Scope Name]**
    
    Proposal Reference (Verbatim): [Exact quoted proposal language]
    
    Contract Reference (Verbatim): [Exact quoted contract language]
    —or— "No contract language expands or alters this scope."
    
    Review Result: Aligned | Discrepancy Identified
    
    If discrepancy exists:
    - Category: Added Scope | Expanded Scope | Missing Scope | Responsibility Shift | Technical Change | Specification Conflict
    - Issue Description: [Plain-language explanation]
    - ABS Position: Must Be Corrected | Pricing Adjustment Required
    - Required Contract Correction: [Exact description of how contract must be revised]
    
    ═══════════════════════════════════════════════════════════════════════════════
    ALIGNMENT ENFORCEMENT RULE (HARD STOP)
    ═══════════════════════════════════════════════════════════════════════════════
    
    The agent may NOT conclude "Scope Aligned" unless:
    • Every proposal scope includes:
      - Proposal citation, AND
      - Contract citation or explicit confirmation no expansion exists
    • No discrepancies remain unresolved
    
    Listing proposal scopes alone is NOT a comparison.
    
    If contract exists but was not reviewed per scope:
    "Scope Review Status: Pending – Contract Comparison Incomplete"
    
    ═══════════════════════════════════════════════════════════════════════════════
    STRICT PROHIBITIONS
    ═══════════════════════════════════════════════════════════════════════════════
    
    The agent must NOT:
    • Use contract language as the baseline
    • Assume scope alignment
    • State "generally aligned"
    • Summarize scope instead of comparing
    • Perform negotiation or pricing
    • Reference other tabs or proposal pricing
    
    **DEFAULT RULE:**
    If uncertain whether a scope difference is material: 👉 FLAG IT.
    ABS does not accept silent scope expansion.
    
    ═══════════════════════════════════════════════════════════════════════════════
    REQUIRED FINAL STATEMENT
    ═══════════════════════════════════════════════════════════════════════════════
    
    The Scope tab must end with ONE and ONLY ONE of:
    • "Scope Review Status: Pending – Contract Required for Comparison"
    • "Scope Review Status: Pending – Contract Comparison Incomplete"
    • "Scope Review Status: Scope Aligned"
    • "Scope Review Status: Scope Not Aligned – Corrections Required"
    
    **MENTAL MODEL:**
    "The proposal defines what was priced.
    Every scope must be defended.
    Silence equals risk.
    If it wasn't priced, it isn't included."

    ═══════════════════════════════════════════════════════════════════════════════
    VALIDATION, ENFORCEMENT & ALIGNMENT GATE (ADDENDUM)
    ═══════════════════════════════════════════════════════════════════════════════
    
    **PURPOSE:** This enforcement layer clarifies when and how alignment may be concluded,
    enforces the Alignment Validation Checklist, and prevents proposal-only summaries
    from being misclassified as scope alignment.
    
    ───────────────────────────────────────────────────────────────────────────────
    DOCUMENT AVAILABILITY CLARIFICATION (NO CONTRADICTION RULE)
    ───────────────────────────────────────────────────────────────────────────────
    
    • The Proposal upload is REQUIRED for the Scope tab to operate.
    • The Contract upload is optional, BUT:
      - If present, it MUST be used
      - If present, comparison is MANDATORY
      - The agent may NOT ignore or defer a Contract that exists in session memory
    
    The agent must NEVER state:
    • "Contract not available"
    • "Contract not reviewed"
    
    ...if a Contract document exists in the session.
    
    ───────────────────────────────────────────────────────────────────────────────
    ALIGNMENT DECISION GATE (NON-OVERRIDABLE)
    ───────────────────────────────────────────────────────────────────────────────
    
    The agent may conclude:
    "Scope Review Status: Scope Aligned"
    
    **ONLY IF ALL** of the following are true:
    
    ✅ 1. A Proposal document is present
    ✅ 2. Every discrete proposal scope has been identified
    ✅ 3. Every proposal scope has been reviewed individually
    ✅ 4. For EACH proposal scope:
         • Proposal language is quoted verbatim, AND
         • Either:
           - Contract language is quoted verbatim, OR
           - The agent explicitly states: "No contract language expands or alters this scope."
    ✅ 5. No discrepancies remain unresolved
    
    🚫 If ANY condition above is NOT met, "Scope Aligned" is PROHIBITED.
    
    ───────────────────────────────────────────────────────────────────────────────
    ALIGNMENT VALIDATION CHECKLIST (MANDATORY INTERNAL CHECK)
    ───────────────────────────────────────────────────────────────────────────────
    
    Before producing the final Scope Review Status, the agent must internally satisfy:
    
    □ Proposal document present?
    □ All proposal scopes identified?
    □ Each scope reviewed individually (not bundled)?
    □ Each scope has proposal citation?
    □ Each scope has contract citation OR explicit "no expansion" statement?
    □ Zero unresolved discrepancies?
    
    **If checklist FAILS:**
    The agent MUST select one of:
    • "Pending – Contract Required for Comparison"
    • "Pending – Contract Comparison Incomplete"
    • "Scope Not Aligned – Corrections Required"
    
    🚫 Checklist failure may NOT be overridden by confidence or assumption.
    
    ───────────────────────────────────────────────────────────────────────────────
    PROPOSAL-ONLY OUTPUT SAFEGUARD
    ───────────────────────────────────────────────────────────────────────────────
    
    If the output:
    • Lists proposal scopes, inclusions, exclusions, or conditions
    • BUT does NOT explicitly compare each scope to the contract
    
    Then the agent MUST end with:
    "Scope Review Status: Pending – Contract Required for Comparison"
    
    🚫 A proposal summary alone can NEVER justify alignment.
    
    ───────────────────────────────────────────────────────────────────────────────
    DISCREPANCY SILENCE RULE
    ───────────────────────────────────────────────────────────────────────────────
    
    **Silence is NOT clearance.**
    
    If a scope has:
    • No contract citation, AND
    • No explicit confirmation that contract language does not expand it
    
    Then that scope is considered NOT REVIEWED, and alignment is PROHIBITED.
    
    ───────────────────────────────────────────────────────────────────────────────
    FINAL OUTPUT CONSISTENCY RULE
    ───────────────────────────────────────────────────────────────────────────────
    
    The final Scope Review Status MUST be consistent with the body of the output.
    
    **The following combinations are INVALID and PROHIBITED:**
    ❌ "Scope Aligned" + no contract citations
    ❌ "Scope Aligned" + discrepancies listed
    ❌ "Full Comparison" + proposal-only analysis
    
    ───────────────────────────────────────────────────────────────────────────────
    MENTAL MODEL REINFORCEMENT
    ───────────────────────────────────────────────────────────────────────────────
    
    "Alignment must be proven per scope.
    Proposal defines the baseline.
    Contract silence is risk.
    Checklist failure means no alignment."
    """,
}

async def analyze_contract_text(
    text: str, 
    task_type: str, 
    guardrails_text: str = "",
    contract_text: str = None,
    proposal_text: str = None
) -> dict:
    """
    Analyzes contract text using the specific task type prompt.
    Runs pre-extraction keyword harvest before LLM processing.
    
    Args:
        text: Main document text to analyze
        task_type: Type of analysis to perform
        guardrails_text: Optional guardrails/guidelines text
        contract_text: Active contract text (for context-aware analysis)
        proposal_text: Active proposal text (for context-aware analysis)
    
    Returns:
        Dict with 'markdown_report' and 'structured_data'.
    """
    if not EMERGENT_LLM_KEY:
        raise Exception("EMERGENT_LLM_KEY not set")

    # Select template or default
    template = PROMPT_TEMPLATES.get(task_type, PROMPT_TEMPLATES["INITIAL_CONTRACT_REVIEW"])

    # ═══════════════════════════════════════════════════════════════════════════
    # PRE-EXTRACTION: GLOBAL KEYWORD HARVEST
    # Run before any LLM processing for Contract review, Proposal comparison, etc.
    # ═══════════════════════════════════════════════════════════════════════════
    
    # Determine what documents to scan based on what's available
    pre_extraction_contract = contract_text if contract_text else (text if "CONTRACT" in text.upper()[:5000] else None)
    pre_extraction_proposal = proposal_text if proposal_text else None
    
    # If text contains both contract and proposal sections, try to split
    if "=== CONTRACT DOCUMENT ===" in text and "=== PROPOSAL DOCUMENT ===" in text:
        parts = text.split("=== PROPOSAL DOCUMENT ===")
        pre_extraction_contract = parts[0].replace("=== CONTRACT DOCUMENT ===", "").strip()
        pre_extraction_proposal = parts[1].strip() if len(parts) > 1 else None
    elif not pre_extraction_contract:
        # Default: treat entire text as contract if no explicit proposal
        pre_extraction_contract = text
    
    # Run pre-extraction
    pre_extraction_output = run_pre_extraction(
        contract_text=pre_extraction_contract,
        proposal_text=pre_extraction_proposal
    )
    
    # Find explicit totals (special handling - don't stop at blanks)
    explicit_totals = []
    if pre_extraction_contract:
        explicit_totals = find_explicit_totals(pre_extraction_contract)
    if pre_extraction_proposal:
        explicit_totals.extend(find_explicit_totals(pre_extraction_proposal))
    
    # Format explicit totals for prompt
    totals_section = ""
    if explicit_totals:
        totals_section = "\n═══ EXPLICIT TOTALS FOUND ═══\n"
        for t in explicit_totals[:5]:
            totals_section += f"  Line {t['line_number']}: {t['amount']} - {t['line_text'][:80]}\n"
        totals_section += "═" * 50 + "\n"
    
    # ═══════════════════════════════════════════════════════════════════════════
    # BUILD PROMPT WITH PRE-EXTRACTION OUTPUT FIRST
    # ═══════════════════════════════════════════════════════════════════════════

    prompt = f"""
    You are the ABS Contract Admin Agent.
    
    {pre_extraction_output}
    {totals_section}
    
    ═══════════════════════════════════════════════════════════════════════════════
    TASK INSTRUCTIONS
    ═══════════════════════════════════════════════════════════════════════════════
    
    {template}
    
    ═══════════════════════════════════════════════════════════════════════════════
    FULL DOCUMENT TEXT
    ═══════════════════════════════════════════════════════════════════════════════
    
    **INPUT DOCUMENT TEXT:**
    {text[:100000]} 
    
    **GUARDRAILS / GUIDELINES (Use for comparison if present):**
    {guardrails_text[:20000]}
    
    ═══════════════════════════════════════════════════════════════════════════════
    OUTPUT INSTRUCTIONS
    ═══════════════════════════════════════════════════════════════════════════════
    
    - Use the PRE-EXTRACTION data above to quickly locate key values (totals, dates, parties, etc.)
    - If EXPLICIT TOTALS are listed, use those values rather than blank fields ($ __________)
    - Strictly follow the JSON output format defined in the task instructions.
    - Do not include markdown code blocks (```json) inside the JSON string itself.
    - Be professional, concise, and ABS-oriented.
    """
    
    try:
        # Use LlmChat wrapper
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id="analysis_session", 
            system_message="You are a helpful, professional contract analysis assistant for Associated Building Specialties (ABS)."
        )
        
        # Use GPT-4o directly for stability
        try:
            chat.with_model("openai", "gpt-4o")
            user_msg = UserMessage(text=prompt)
            response_text = await chat.send_message(user_msg)
        except Exception as e_model:
            print(f"GPT-4o failed ({e_model}), falling back to GPT-4o-mini")
            try:
                chat.with_model("openai", "gpt-4o-mini")
                user_msg = UserMessage(text=prompt)
                response_text = await chat.send_message(user_msg)
            except Exception as e_fallback:
                if "Budget has been exceeded" in str(e_fallback):
                    raise Exception("Emergent API Quota Exceeded. Please top up your balance.")
                raise e_fallback
        
        # Robust JSON extraction
        try:
            # Find the first '{' and the last '}'
            match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if match:
                json_str = match.group(0)
                return json.loads(json_str)
            else:
                # Try simple cleaning if regex failed (unlikely for valid JSON)
                cleaned_json = response_text.replace("```json", "").replace("```", "").strip()
                return json.loads(cleaned_json)
                
        except Exception as e:
            print(f"JSON Parse Error. Raw Text:\n{response_text}")
            # Fallback: return raw text in markdown_report
            return {
                "markdown_report": response_text,
                "structured_data": {"error": "Failed to parse structured data"}
            }
        
    except Exception as e:
        print(f"LLM Analysis Error: {e}")
        raise e

async def chat_with_context(message: str, history: list, context: str, task_type: str) -> str:
    # ... (same as before) ...
    """
    Chat with the agent including document context.
    """
    if not EMERGENT_LLM_KEY:
        raise Exception("EMERGENT_LLM_KEY not set")

    system_prompt = f"""
    You are the ABS Contract Admin Agent.
    Current Task Context: {task_type}
    
    You have access to the following contract documents text (truncated if too long):
    {context}
    
    Answer the user's question based on this context. 
    Be precise, cite section numbers if available, and warn if information is missing.
    Do not give legal advice; provide business/contract administration guidance.
    """

    # Apply strict schedule style if in that context
    if task_type == "SCHEDULE_ANALYSIS":
        system_prompt += """
    
    **STYLE GUIDELINES:**
    Answer in a highly concise, contract-admin style.
    • Limit the response to 2–4 short bullet points.
    • State only start and end dates relevant to the specific scope.
    • Do not include background explanation, schedule logic, assumptions, or coordination guidance.
    • If dates are inferred from the master schedule, state them plainly without qualifiers.
    • Avoid narrative sentences—use direct, factual phrasing only.
    • No additional commentary.
        """
    
    try:
        # Reconstruct history for LlmChat
        initial_messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ["user", "assistant"] and content:
                initial_messages.append({"role": role, "content": content})
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id="chat_session", # Not used for persistence here
            system_message=system_prompt,
            initial_messages=initial_messages
        )
        
        # Use GPT-4o directly for stability
        try:
            chat.with_model("openai", "gpt-4o")
            user_msg = UserMessage(text=message)
            response_text = await chat.send_message(user_msg)
        except Exception:
            # Silent fallback for chat
            chat.with_model("openai", "gpt-4o-mini")
            user_msg = UserMessage(text=message)
            response_text = await chat.send_message(user_msg)
        
        return response_text
        
    except Exception as e:
        print(f"LLM Chat Error: {e}")
        raise e
