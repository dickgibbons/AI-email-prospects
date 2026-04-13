# Outreach Sheet Schema (n8n + Drive)

Single source of truth for the **Contacts** sheet. Drive path and selection rules are below.

## Sheet: Contacts (or "Outreach")

| Column | Purpose | Example |
|--------|--------|--------|
| **Name** | Prospect name | Chris McCabe |
| **Title** | Role | CIO |
| **Company** | Account name (used for Drive folder) | Brown Brothers Harriman |
| **LinkedIn URL** | Profile link | https://linkedin.com/in/... |
| **Target vs Existing** | `Target` \| `Existing client` | Target |
| **Intro Call Topic** | Broad topic for first meeting | AI in SDLC, model governance |
| **EPAM Footprint** | Optional: work at this company | Working with Jim T. on analytics |
| **Internal Contact** | Optional: name you can reference (with permission) | Jim Tessemer |
| **Notes** | Trigger events, mutual connections, etc. | GP Jan 2025, AI Committee |
| **Status** | `New` \| `In sequence` \| `Stopped` \| `Not interested` \| `Meeting booked` \| `Done` | New |
| **Max Touches** | Optional; blank = use role-based default (C-level 4, VP/MD 6, else 5) | 5 |
| **Last Touch Sent** | 1–7 (which touch was last generated) | 1 |
| **Next Touch Due** | Date of next touch (YYYY-MM-DD) | 2025-03-01 |
| **Doc Link** | Optional; link to last created Doc (for reminders) | https://docs.google.com/... |
| **Last Processed** | Date we last ran for this row | 2025-02-25 |

Only rows with **Status** `New` or `In sequence` are eligible. **Stopped**, **Not interested**, **Meeting booked**, **Done** are ignored.

## Drive structure

- **Root:** `EPAM`
  - **EPAM Client Outreach**
    - **Client** (existing clients)
    - **Target Prospect** (targets)
      - **Messages**
        - **[Company Name]** (one folder per account)
          - Company background Doc (e.g. `Company background – BBH` or `BBH – Background`)
          - **Dick Gibbons**
            - One Doc per email: `[Prospect Name] – Touch N`

**Target vs Existing** maps to branch:
- `Existing client` → use **Client** branch.
- `Target` (or blank) → use **Target Prospect** branch.

Path for a prospect doc:
`EPAM / EPAM Client Outreach / Client or Target Prospect / Messages / [Company] / Dick Gibbons / [Prospect Name] – Touch N`

## Daily selection rules (max 20, spread)

1. Eligible: **Status** in (`New`, `In sequence`) and **Next Touch Due** ≤ today (or blank if Status = `New`).
2. Cap **3 per company** per run.
3. Sort by **Next Touch Due** (oldest first), then by **Company**.
4. Greedy pick across companies until **20** selected or none left.

## Sequence length by role (defaults)

- **C-level** (CIO, CTO, CEO, Chief, CDO, CRO): **4** touches.
- **VP / MD / Director / Head of:** **6** touches.
- **Else:** **5** touches.

Override: set **Max Touches** in the row.

## Cadence (days between touches)

Example: Touch 1 → +3 → Touch 2 → +4 → Touch 3 → +5 → Touch 4 → … (configurable in workflow).

## Reminder email

- **To:** richard_gibbons@epam.com  
- **From:** dickgibbons@gmail.com (use Gmail account that runs n8n or SMTP from that address)  
- **Content:** List of prospects with **Next Touch Due** = today (Name, Company, Touch N, Doc Link if present).
