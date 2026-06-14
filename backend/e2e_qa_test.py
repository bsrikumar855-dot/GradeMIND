"""
GradeMIND E2E QA Validation Script
Tests all 12 modules against the live backend at http://localhost:8000
"""
import requests
import json
import sys
import time
from pathlib import Path

BASE = "http://localhost:8000"
RESULTS = {}
PASS = 0
FAIL = 0
BUGS = []

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        RESULTS[name] = {"status": "PASS", "detail": detail}
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        RESULTS[name] = {"status": "FAIL", "detail": detail}
        BUGS.append({"test": name, "detail": detail})
        print(f"  ❌ {name} — {detail}")

print("=" * 70)
print("  GradeMIND E2E QA Validation")
print("=" * 70)

# ─── 1. HEALTH CHECK ───
print("\n[1/12] Health Check")
try:
    r = requests.get(f"{BASE}/")
    test("Health endpoint responds", r.status_code == 200, f"status={r.status_code}")
except Exception as e:
    test("Health endpoint responds", False, str(e))

# ─── 2. AUTHENTICATION ───
print("\n[2/12] Authentication")
# Register Teacher
try:
    r = requests.post(f"{BASE}/auth/register", json={
        "email": "e2e_teacher@grademind.edu",
        "password": "SecurePass123!",
        "name": "E2E Teacher",
        "role": "TEACHER"
    })
    test("Teacher registration", r.status_code in [201, 200, 400], f"status={r.status_code}, body={r.text[:200]}")
except Exception as e:
    test("Teacher registration", False, str(e))

# Login Teacher
TEACHER_TOKEN = None
TEACHER_REFRESH = None
try:
    r = requests.post(f"{BASE}/auth/login", json={
        "email": "e2e_teacher@grademind.edu",
        "password": "SecurePass123!"
    })
    d = r.json()
    TEACHER_TOKEN = d.get("data", {}).get("access_token")
    TEACHER_REFRESH = d.get("data", {}).get("refresh_token")
    test("Teacher login", r.status_code == 200 and TEACHER_TOKEN is not None, f"status={r.status_code}, hasToken={bool(TEACHER_TOKEN)}")
except Exception as e:
    test("Teacher login", False, str(e))

# /auth/me
try:
    r = requests.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
    d = r.json()
    test("/auth/me returns profile", r.status_code == 200 and "email" in str(d), f"status={r.status_code}, body={json.dumps(d)[:200]}")
except Exception as e:
    test("/auth/me returns profile", False, str(e))

# Token refresh
try:
    r = requests.post(f"{BASE}/auth/refresh", json={"refresh_token": TEACHER_REFRESH})
    d = r.json()
    new_token = d.get("data", {}).get("access_token")
    if new_token:
        TEACHER_TOKEN = new_token
    test("Token refresh", r.status_code == 200 and new_token is not None, f"status={r.status_code}")
except Exception as e:
    test("Token refresh", False, str(e))

# Register Student
try:
    r = requests.post(f"{BASE}/auth/register", json={
        "email": "e2e_student@grademind.edu",
        "password": "StudentPass123!",
        "name": "E2E Student",
        "role": "STUDENT"
    })
    test("Student registration", r.status_code in [201, 200, 400], f"status={r.status_code}")
except Exception as e:
    test("Student registration", False, str(e))

# Login Student
STUDENT_TOKEN = None
try:
    r = requests.post(f"{BASE}/auth/login", json={
        "email": "e2e_student@grademind.edu",
        "password": "StudentPass123!"
    })
    d = r.json()
    STUDENT_TOKEN = d.get("data", {}).get("access_token")
    test("Student login", r.status_code == 200 and STUDENT_TOKEN is not None, f"status={r.status_code}")
except Exception as e:
    test("Student login", False, str(e))

# ─── 3. EXAM CREATION ───
print("\n[3/12] Exam Creation")
EXAM_ID = None
try:
    r = requests.post(f"{BASE}/exams", json={
        "title": "E2E Science Final",
        "subject": "Science",
        "total_marks": 100,
        "instructions": "Answer all questions",
        "answer_key": "Q1: photosynthesis, Q2: mitosis"
    }, headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
    d = r.json()
    EXAM_ID = d.get("id")
    test("Create exam", r.status_code == 200 and EXAM_ID is not None, f"status={r.status_code}, id={EXAM_ID}")
except Exception as e:
    test("Create exam", False, str(e))

# List exams
try:
    r = requests.get(f"{BASE}/exams", headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
    d = r.json()
    # Check if response is wrapped (ExamListResponse has .exams) or raw array
    exams = d.get("exams", d) if isinstance(d, dict) else d
    test("List exams", r.status_code == 200, f"status={r.status_code}, count={len(exams) if isinstance(exams, list) else 'N/A'}")
except Exception as e:
    test("List exams", False, str(e))

# Get exam by ID
try:
    r = requests.get(f"{BASE}/exams/{EXAM_ID}", headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
    d = r.json()
    test("Get exam by ID", r.status_code == 200 and d.get("title") is not None, f"status={r.status_code}, title={d.get('title')}")
except Exception as e:
    test("Get exam by ID", False, str(e))

# Update exam
try:
    r = requests.put(f"{BASE}/exams/{EXAM_ID}", json={
        "title": "E2E Science Final (Updated)",
        "subject": "Science",
        "total_marks": 100
    }, headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
    d = r.json()
    test("Update exam", r.status_code == 200 and "Updated" in d.get("title", ""), f"status={r.status_code}, title={d.get('title')}")
except Exception as e:
    test("Update exam", False, str(e))

# ─── 4. SUBMISSION UPLOAD ───
print("\n[4/12] Submission Upload")
SUBMISSION_ID = None
try:
    # Create a simple test image file
    test_file_path = Path("storage/test_answer_sheet.png")
    test_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create a minimal PNG file (1x1 white pixel)
    import struct, zlib
    def create_png():
        sig = b'\x89PNG\r\n\x1a\n'
        ihdr_data = struct.pack('>IIBBBBB', 1, 1, 8, 2, 0, 0, 0)
        ihdr_crc = zlib.crc32(b'IHDR' + ihdr_data)
        ihdr = struct.pack('>I', 13) + b'IHDR' + ihdr_data + struct.pack('>I', ihdr_crc & 0xffffffff)
        raw = b'\x00\x00\x00\x00'
        idat_data = zlib.compress(raw)
        idat_crc = zlib.crc32(b'IDAT' + idat_data)
        idat = struct.pack('>I', len(idat_data)) + b'IDAT' + idat_data + struct.pack('>I', idat_crc & 0xffffffff)
        iend_crc = zlib.crc32(b'IEND')
        iend = struct.pack('>I', 0) + b'IEND' + struct.pack('>I', iend_crc & 0xffffffff)
        return sig + ihdr + idat + iend
    
    png_data = create_png()
    test_file_path.write_bytes(png_data)
    
    with open(test_file_path, "rb") as f:
        r = requests.post(f"{BASE}/submissions/upload",
            data={
                "exam_id": EXAM_ID,
                "student_name": "E2E Student",
                "student_roll_number": "E2E001"
            },
            files={"file": ("test_answer.png", f, "image/png")},
            headers={"Authorization": f"Bearer {TEACHER_TOKEN}"}
        )
    d = r.json()
    SUBMISSION_ID = d.get("id")
    test("Upload submission", r.status_code == 201 and SUBMISSION_ID is not None, f"status={r.status_code}, id={SUBMISSION_ID}")
except Exception as e:
    test("Upload submission", False, str(e))

# ─── 5. OCR PROCESSING (via status polling) ───
print("\n[5/12] OCR Processing / Status Polling")
if SUBMISSION_ID:
    try:
        r = requests.get(f"{BASE}/submissions/{SUBMISSION_ID}/status",
            headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
        d = r.json()
        test("Submission status endpoint", r.status_code == 200 and "status" in d,
             f"status={r.status_code}, sub_status={d.get('status')}, ocr={d.get('ocr_status')}")
    except Exception as e:
        test("Submission status endpoint", False, str(e))
else:
    test("Submission status endpoint", False, "No submission ID")

# ─── 6. AI EVALUATION (poll for completion) ───
print("\n[6/12] AI Evaluation / Status Polling")
if SUBMISSION_ID:
    max_polls = 15
    final_status = None
    for i in range(max_polls):
        try:
            r = requests.get(f"{BASE}/submissions/{SUBMISSION_ID}/status",
                headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
            d = r.json()
            final_status = d.get("status", "UNKNOWN")
            if final_status in ["COMPLETED", "FAILED"]:
                break
            time.sleep(2)
        except:
            time.sleep(2)
    test("Pipeline reaches terminal state", final_status in ["COMPLETED", "FAILED"],
         f"final_status={final_status} after {min(i+1, max_polls)} polls")
    if final_status == "COMPLETED":
        test("Pipeline COMPLETED successfully", True, f"status={final_status}")
    elif final_status == "FAILED":
        # Still a valid terminal state — get error
        try:
            r2 = requests.get(f"{BASE}/submissions/{SUBMISSION_ID}",
                headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
            d2 = r2.json()
            test("Pipeline FAILED (check error)", False,
                 f"error={d2.get('error_message', 'unknown')[:200]}")
        except:
            test("Pipeline FAILED (check error)", False, "Could not retrieve error")
else:
    test("Pipeline status check", False, "No submission ID")

# ─── 7. DASHBOARD METRICS ───
print("\n[7/12] Dashboard Metrics")
try:
    r = requests.get(f"{BASE}/dashboard/overview",
        headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
    d = r.json()
    test("Dashboard overview", r.status_code == 200 and "total_exams" in d,
         f"status={r.status_code}, exams={d.get('total_exams')}, subs={d.get('total_submissions')}")
except Exception as e:
    test("Dashboard overview", False, str(e))

# Dashboard exam analytics
if EXAM_ID:
    try:
        r = requests.get(f"{BASE}/dashboard/exams/{EXAM_ID}",
            headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
        d = r.json()
        test("Exam analytics", r.status_code == 200,
             f"status={r.status_code}, body={json.dumps(d)[:200]}")
    except Exception as e:
        test("Exam analytics", False, str(e))

# Dashboard monitoring
try:
    r = requests.get(f"{BASE}/dashboard/monitoring",
        headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
    d = r.json()
    test("Pipeline monitoring", r.status_code == 200 and "aggregate_analytics" in d,
         f"status={r.status_code}")
except Exception as e:
    test("Pipeline monitoring", False, str(e))

# ─── 8. REPORT GENERATION ───
print("\n[8/12] Report Generation")
if SUBMISSION_ID:
    try:
        r = requests.get(f"{BASE}/submissions/{SUBMISSION_ID}/report",
            headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
        # 200 = report exists, 400 = not generated yet
        test("Report endpoint responds", r.status_code in [200, 400, 404],
             f"status={r.status_code}, detail={r.text[:200]}")
    except Exception as e:
        test("Report endpoint responds", False, str(e))

# ─── 9. PDF DOWNLOADS ───
print("\n[9/12] PDF Downloads")
if SUBMISSION_ID:
    try:
        r = requests.get(f"{BASE}/submissions/{SUBMISSION_ID}/pdf",
            headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
        test("PDF download endpoint responds", r.status_code in [200, 400, 404],
             f"status={r.status_code}, content_type={r.headers.get('content-type', 'N/A')}")
    except Exception as e:
        test("PDF download endpoint responds", False, str(e))
    
    # Dashboard PDF endpoint
    try:
        r = requests.get(f"{BASE}/dashboard/submissions/{SUBMISSION_ID}/pdf",
            headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
        test("Dashboard PDF endpoint responds", r.status_code in [200, 400, 404],
             f"status={r.status_code}")
    except Exception as e:
        test("Dashboard PDF endpoint responds", False, str(e))

# ─── 10. STUDENT PORTAL ───
print("\n[10/12] Student Portal")
try:
    r = requests.get(f"{BASE}/student/results",
        headers={"Authorization": f"Bearer {STUDENT_TOKEN}"})
    d = r.json()
    test("Student results overview", r.status_code == 200 and "student_id" in d,
         f"status={r.status_code}, exams={d.get('total_exams')}, avg={d.get('average_score')}")
except Exception as e:
    test("Student results overview", False, str(e))

# ─── 11. RESULT PUBLISHING ───
print("\n[11/12] Result Publishing")
if EXAM_ID:
    try:
        r = requests.post(f"{BASE}/results/publish/{EXAM_ID}",
            headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
        d = r.json()
        test("Publish results", r.status_code == 200 and d.get("results_published") == True,
             f"status={r.status_code}, published={d.get('results_published')}")
    except Exception as e:
        test("Publish results", False, str(e))
    
    try:
        r = requests.post(f"{BASE}/results/unpublish/{EXAM_ID}",
            headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
        d = r.json()
        test("Unpublish results", r.status_code == 200 and d.get("results_published") == False,
             f"status={r.status_code}, published={d.get('results_published')}")
    except Exception as e:
        test("Unpublish results", False, str(e))

    # RBAC: Student tries to publish (should fail)
    try:
        r = requests.post(f"{BASE}/results/publish/{EXAM_ID}",
            headers={"Authorization": f"Bearer {STUDENT_TOKEN}"})
        test("RBAC: Student cannot publish", r.status_code == 403,
             f"status={r.status_code} (expected 403)")
    except Exception as e:
        test("RBAC: Student cannot publish", False, str(e))

# ─── 12. RBAC ───
print("\n[12/12] RBAC Enforcement")
# Student cannot create exam
try:
    r = requests.post(f"{BASE}/exams", json={
        "title": "Unauthorized", "subject": "Hack", "total_marks": 1
    }, headers={"Authorization": f"Bearer {STUDENT_TOKEN}"})
    test("RBAC: Student cannot create exam", r.status_code == 403,
         f"status={r.status_code} (expected 403)")
except Exception as e:
    test("RBAC: Student cannot create exam", False, str(e))

# Student cannot access dashboard
try:
    r = requests.get(f"{BASE}/dashboard/overview",
        headers={"Authorization": f"Bearer {STUDENT_TOKEN}"})
    test("RBAC: Student cannot access dashboard", r.status_code == 403,
         f"status={r.status_code} (expected 403)")
except Exception as e:
    test("RBAC: Student cannot access dashboard", False, str(e))

# Student cannot delete exam
try:
    r = requests.delete(f"{BASE}/exams/{EXAM_ID}",
        headers={"Authorization": f"Bearer {STUDENT_TOKEN}"})
    test("RBAC: Student cannot delete exam", r.status_code == 403,
         f"status={r.status_code} (expected 403)")
except Exception as e:
    test("RBAC: Student cannot delete exam", False, str(e))

# Unauthenticated access
try:
    r = requests.get(f"{BASE}/exams")
    test("RBAC: Unauthenticated blocked from /exams", r.status_code == 401,
         f"status={r.status_code} (expected 401)")
except Exception as e:
    test("RBAC: Unauthenticated blocked from /exams", False, str(e))

try:
    r = requests.get(f"{BASE}/dashboard/overview")
    test("RBAC: Unauthenticated blocked from /dashboard", r.status_code == 401,
         f"status={r.status_code} (expected 401)")
except Exception as e:
    test("RBAC: Unauthenticated blocked from /dashboard", False, str(e))

# Logout
try:
    r = requests.post(f"{BASE}/auth/logout", json={"refresh_token": TEACHER_REFRESH},
        headers={"Authorization": f"Bearer {TEACHER_TOKEN}"})
    test("Logout", r.status_code == 200, f"status={r.status_code}")
except Exception as e:
    test("Logout", False, str(e))

# ─── SUMMARY ───
print("\n" + "=" * 70)
print(f"  RESULTS: {PASS} passed / {FAIL} failed / {PASS + FAIL} total")
print(f"  SCORE: {round(PASS / (PASS + FAIL) * 100, 1)}%")
print("=" * 70)

if BUGS:
    print("\n  🐛 BUGS FOUND:")
    for b in BUGS:
        print(f"    • {b['test']}: {b['detail']}")

print("\n  📊 Writing results to e2e_results.json...")
with open("e2e_results.json", "w") as f:
    json.dump({
        "passed": PASS,
        "failed": FAIL,
        "total": PASS + FAIL,
        "score_pct": round(PASS / max(PASS + FAIL, 1) * 100, 1),
        "bugs": BUGS,
        "results": RESULTS
    }, f, indent=2)

print("  Done.\n")
