# Workshop Packet Review

This packet is the first review surface. It shows the proposed run sheet, the evidence behind accepted facts, and the warnings a coordinator should resolve before using the plan.

## Review Snapshot

- Accepted facts: 15
- Flagged facts or checks: 2
- Rejected unsupported claims: 0
- Validation state: passed_with_warnings

## Evidence To Decision Walkthrough

- Source evidence: `community_workshop_flyer.pdf` page 1, line 1 says "Community Workshop Packet: Saturday Repair And Make Day".
- Extracted decision: workshop title = **Saturday Repair And Make Day**.
- Validation result: **accepted** because the value has source evidence.
- Final output: the title appears in the run sheet below and in `run_sheet.json` as backing technical evidence.

## Proposed Run Sheet

- Workshop: **Saturday Repair And Make Day**
- Date: **2026-05-16**
- Time window: **09:30-12:00**
- Location: **Maple Community Room A** (flagged)
- Facilitator/contact: **Avery Stone, neighborhood education volunteer**

### Sessions

- **Tool safety check**: 09:30-10:00 on 2026-05-16 (accepted)
- **Small fix stations**: 10:00-12:00 on 2026-05-16 (accepted)

### Materials And Setup

**Materials**
- extension cords (accepted)
- safety glasses (accepted)
- blank labels (accepted)
- spare screws (accepted)
- masking tape (accepted)

**Setup needs**
- Arrange three work tables by 09:00 (accepted)

**Participant reminders**
- Bring one small household item and label loose parts (accepted)
- participants should label their items before the small fix stations (accepted)

**Accessibility notes**
- Step-free entrance via Oak Street door (accepted)

**Open details**
- final count of soldering mats is not confirmed. (flagged) - Source marks this detail as incomplete.


## Warnings And Review Questions

- `missing_details[0]`: Source marks this detail as incomplete.
- `location`: Source documents mention more than one room for the same workshop.

### Human Review Questions

- Confirm whether the workshop uses Maple Community Room A or B.
- Resolve incomplete detail: final count of soldering mats is not confirmed.

### Source Conflicts

- Source documents mention more than one room for the same workshop.
  - `Maple Community Room A` from `community_workshop_flyer.pdf` page 1, line 4
  - `Maple Community Room B` from `facilitator_notes.docx` paragraph 3

## Technical Backing Files

- `run_sheet.json` contains the structured output for technical review.
- `validation_report.json` contains schema and deterministic-rule results.
- `retrieval_provenance.json` shows which spans were retrieved for each evidence query.
