from __future__ import annotations

import json
from pathlib import Path
from fastapi.testclient import TestClient

from main import app
from models.schemas import WordTimestamp
from services.delivery_metrics import analyze_delivery_signals
from services.cv_parser import extract_profile_heuristic, render_pdf_pages_to_png_base64
from data.cv_presets import CV_PRESETS


def test_delivery_metrics_accuracy() -> None:
    words = [
        WordTimestamp(word="So,", start=0.0, end=0.4),
        WordTimestamp(word="um,", start=0.5, end=0.8, is_filler=True),
        WordTimestamp(word="for", start=0.9, end=1.1),
        WordTimestamp(word="the", start=1.2, end=1.3),
        WordTimestamp(word="analytics", start=1.4, end=1.9),
        WordTimestamp(word="platform,", start=2.0, end=2.5),
        WordTimestamp(word="I", start=5.6, end=5.8),
        WordTimestamp(word="think", start=5.9, end=6.2),
        WordTimestamp(word="maybe", start=6.3, end=6.6),
        WordTimestamp(word="we", start=6.7, end=6.9),
        WordTimestamp(word="used", start=7.0, end=7.3),
        WordTimestamp(word="uh", start=7.4, end=7.7, is_filler=True),
        WordTimestamp(word="PostgreSQL", start=7.8, end=8.5),
        WordTimestamp(word="and", start=8.6, end=8.8),
        WordTimestamp(word="basically", start=8.9, end=9.4, is_filler=True),
        WordTimestamp(word="a", start=9.5, end=9.6),
        WordTimestamp(word="queue.", start=9.7, end=10.1),
    ]
    transcript = " ".join(w.word for w in words)
    metrics = analyze_delivery_signals(
        transcript_verbatim=transcript,
        duration_seconds=10.1,
        word_timestamps=words,
        stt_provider="gemini:gemini-3.5-transcribe",
    )
    assert metrics.longest_pause_sec == 3.1
    assert metrics.pause_label == "Noticeable"
    assert len(metrics.awkward_pauses) == 1
    assert metrics.filler_count == 3
    assert any("i think maybe" in h.lower() for h in metrics.hedging_phrases)
    assert "[pause 3.1s]" in metrics.annotated_transcript
    print("✓ Delivery telemetry test passed")


def test_ats_cv_parser_across_real_cvs() -> None:
    # Verify Stripe Data Analyst CV extraction & target opportunity auto-detection
    p_stripe = extract_profile_heuristic(CV_PRESETS["stripe_data_analyst"]["raw_text"])
    assert p_stripe.candidate_name == "Mbesa Lephoto"
    assert "82.4%" in p_stripe.years_experience
    assert "14 distinctions" in p_stripe.years_experience
    assert p_stripe.extraction_method == "Text extracted", p_stripe.extraction_method
    assert p_stripe.detected_target_company == "Stripe", p_stripe.detected_target_company
    assert "Data Analyst" in p_stripe.detected_target_role, p_stripe.detected_target_role
    assert p_stripe.seniority_track == "intern_grad", p_stripe.seniority_track
    proj_names = [p.name for p in p_stripe.projects]
    assert any("Enterprise Metrics Semantic Layer" in n for n in proj_names), proj_names
    assert any("VoiceGuard" in n for n in proj_names), proj_names
    assert any("VeriFace AI" in n for n in proj_names), proj_names
    assert any("Lightning Webstore" in n for n in proj_names), proj_names
    assert any("Lowkey AI" in n for n in proj_names), proj_names

    # Verify Amazon SA SDE CV extraction (with inline headers & opportunity detection)
    p_amz = extract_profile_heuristic(CV_PRESETS["amazon_sde_sa"]["raw_text"])
    assert p_amz.candidate_name == "Thuto Lephoto"
    assert p_amz.detected_target_company == "Amazon", p_amz.detected_target_company
    assert "Software Development Engineer" in p_amz.detected_target_role, p_amz.detected_target_role
    assert len(p_amz.projects) >= 4
    assert len(p_amz.work_experience) >= 3

    # Verify opportunity auto-detection on other South African/global reference CVs
    expected_cv_targets = {
        "bbd_grad_swe": ("BBD", "Graduate Software Engineer"),
        "boxfusion_grad_swe": ("Boxfusion", "Graduate Software Engineer"),
        "deloitte_infinityx": ("Deloitte InfinityX", "Technology Consulting Graduate (InfinityX)"),
        "visa_vca_consulting": ("Visa", "Visa Consulting & Analytics (VCA) Intern"),
        "bluespec_ai_intern": ("Bluespec Holdings", "AI Developer Intern"),
        "cape_union_mart_bi": ("Cape Union Mart", "Business Intelligence (BI) Intern"),
        "amazon_dco_tech": ("Amazon", "Data Center Operations (DCO) Tech Intern"),
    }
    for pid, (exp_comp, exp_role) in expected_cv_targets.items():
        prof = extract_profile_heuristic(CV_PRESETS[pid]["raw_text"])
        assert prof.extraction_method == "Text extracted", prof.extraction_method
        assert prof.detected_target_company == exp_comp, f"{pid}: expected comp {exp_comp}, got {prof.detected_target_company}"
        assert exp_role.split()[0].lower() in prof.detected_target_role.lower(), f"{pid}: got role {prof.detected_target_role}"
        assert len(prof.projects) >= 2, f"{pid} extracted {len(prof.projects)} projects"
        assert len(prof.primary_skills) >= 4, f"{pid} extracted {prof.primary_skills}"

    # Verify universal CV parser when NO company is specified (Vac Work Cybersecurity CV)
    generic_cv = """Sipho Ndlovu
sipho@example.co.za | Pretoria, Gauteng

PROFESSIONAL SUMMARY
BSc Computer Science student applying for winter Vacation Work in defensive security operations, SIEM alert triage, and manual OWASP web vulnerability testing.

SKILLS
Python, Linux, OWASP, SIEM, Wireshark, TCP/IP, SQL

PROJECTS
Packet & Auth Anomaly Monitor | Python, Linux
- Built a sliding-window SSH brute-force parser detecting anomalous lateral movement across auth logs.
"""
    p_gen = extract_profile_heuristic(generic_cv)
    assert p_gen.candidate_name == "Sipho Ndlovu", p_gen.candidate_name
    assert p_gen.detected_target_company == "", p_gen.detected_target_company
    assert p_gen.seniority_track == "vac_work", p_gen.seniority_track
    assert "Cybersecurity" in p_gen.detected_target_role or "Vacation Work" in p_gen.detected_target_role, p_gen.detected_target_role
    assert p_gen.extraction_method == "Text extracted"

    # Verify PDF page rendering for Computer Vision
    sample_pdf = Path(r"C:\Users\tleph\.gemini\antigravity\scratch\Mbesa_Lephoto_BMW_YES4Youth_CV.pdf")
    if sample_pdf.exists():
        imgs = render_pdf_pages_to_png_base64(sample_pdf.read_bytes(), max_pages=2)
        assert len(imgs) >= 1 and len(imgs[0]) > 5000

    print("✓ Universal ATS + Computer Vision CV parser & target auto-detection tests passed")


def test_south_african_and_global_research_and_live_gemini() -> None:
    with TestClient(app) as client:
        h = client.get("/api/health").json()
        assert h["llm"]["provider"] == "gemini", f"Expected gemini provider, got {h}"
        assert h["stt"]["provider"] == "gemini_audio", f"Expected gemini_audio STT, got {h}"

        # Check expanded South African + global company research mappings
        expectations = [
            ("Gendac", "Vacation Work (Vac Work) Student", "sa_software_grad_consultancy", "vac_work"),
            ("iStore", "Backend Engineer", "sa_enterprise_retail_bank_fintech", "junior"),
            ("Electrum", "Graduate Software Engineer", "sa_software_grad_consultancy", "intern_grad"),
            ("KION Group", "Software Development Engineer Intern", "industrial_automation_supply_chain", "intern_grad"),
            ("Dematic", "Embedded Systems / IoT & Automation Engineer", "industrial_automation_supply_chain", "junior"),
            ("Orange Cyberdefense", "Cybersecurity Analyst / Penetration Tester", "cybersecurity_offense_defense", "junior"),
            ("Performanta", "SOC Security Analyst", "cybersecurity_offense_defense", "junior"),
            ("ShopriteX", "Data Engineer", "sa_enterprise_retail_bank_fintech", "junior"),
            ("Derivco", "Graduate Software Engineer", "sa_software_grad_consultancy", "intern_grad"),
            ("Allan Gray", "Graduate Software Engineer", "sa_software_grad_consultancy", "intern_grad"),
            ("Vodacom", "Technical Project Manager", "sa_enterprise_retail_bank_fintech", "junior"),
            ("MTN", "Product Manager", "sa_enterprise_retail_bank_fintech", "junior"),
            ("BBD", "Graduate Software Engineer", "sa_software_grad_consultancy", "intern_grad"),
            ("Boxfusion", "Software Engineering Graduate", "sa_software_grad_consultancy", "intern_grad"),
            ("Deloitte", "Technology Consulting Graduate", "consulting_vca_bi_case", "intern_grad"),
            ("Visa", "VCA Intern", "consulting_vca_bi_case", "intern_grad"),
            ("Amazon", "Data Center Operations (DCO) Tech Intern", "lp_bar_raiser", "intern_grad"),
            ("Stripe", "Data Analyst Intern", "pragmatic_fintech_api", "intern_grad"),
        ]
        for company, role, expected_arch, expected_track in expectations:
            resp = client.post(
                "/api/research/company",
                json={"company_name": company, "target_role": role},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["archetype_id"] == expected_arch, f"{company}: expected {expected_arch}, got {data['archetype_id']}"
            assert data["seniority_track"] == expected_track, f"{company}/{role}: expected track {expected_track}, got {data['seniority_track']}"
            assert len(data["researched_job_description"]) > 120, f"{company}/{role}: missing researched_job_description"
            assert len(data["explore_pillars"]) == 3, f"{company}/{role}: missing explore_pillars"
            for ep in data["explore_pillars"]:
                assert ep["description"].count("(") == ep["description"].count(")"), f"Unbalanced parens in pillar: {ep['description']}"
                assert not ep["description"].endswith(" ."), f"Trailing space before period: {ep['description']}"
            assert len(data["company_grading_rubric"]) >= 2, f"{company}: missing company_grading_rubric"
            assert data["expected_answer_structure"], f"{company}: missing expected_answer_structure"
            assert len(data["coding_and_leetcode_patterns"]) >= 1, f"{company}: missing coding_and_leetcode_patterns"
            serialized = json.dumps(data, ensure_ascii=False)
            assert "\u2014" not in serialized, f"Em dash found in research for {company}"
            assert "\u2013" not in serialized, f"En dash found in research for {company}"

        # Test live Gemini session creation & company-calibrated answer evaluation (Electrum Vac Work)
        electrum_research = client.post(
            "/api/research/company",
            json={"company_name": "Electrum", "target_role": "Vacation Work (Vac Work) Student"},
        ).json()
        cv_doc = client.post("/api/cv/preset/bbd_grad_swe").json()
        assert cv_doc["candidate_profile"]["extraction_method"] == "Text extracted"
        sess_resp = client.post(
            "/api/sessions",
            json={
                "cv_document_id": cv_doc["id"],
                "company_name": "Electrum",
                "target_role": "Vacation Work (Vac Work) Student",
                "job_description": electrum_research["researched_job_description"],
                "question_count": 6,
            },
        )
        assert sess_resp.status_code == 200
        session = sess_resp.json()
        assert len(session["questions"]) == 6
        sess_json = json.dumps(session, ensure_ascii=False)
        assert "\u2014" not in sess_json, "Em dash found in generated session"
        assert "\u2013" not in sess_json, "En dash found in generated session"

        q_eval = session["questions"][1]
        ev_resp = client.post(
            f"/api/sessions/{session['id']}/questions/{q_eval['id']}/evaluate",
            data={
                "fallback_transcript": (
                    "First, to make sure I understand the constraint, I would restate the edge cases like empty lists "
                    "and duplicate transaction keys. My brute-force baseline uses a nested O(N squared) loop, and to "
                    "optimize it I can use a hash map so lookups run in O(1) average time and O(N) total time, versus "
                    "sorting and two pointers at O(N log N) time with O(1) extra space. In my Library Management System "
                    "project in Java, I used interfaces and encapsulation cleanly to separate data storage."
                ),
                "duration_seconds": "34.0",
            },
        )
        assert ev_resp.status_code == 200
        attempt = ev_resp.json()
        ev_json = json.dumps(attempt, ensure_ascii=False)
        assert "\u2014" not in ev_json, "Em dash found in evaluation response"
        assert "\u2013" not in ev_json, "En dash found in evaluation response"
        print(
            "✓ Live Gemini API test passed! Evaluated for Electrum Vac Work by:",
            attempt["evaluation"]["llm_model"],
            "| Overall score:",
            attempt["evaluation"]["scores"]["overall"],
        )

        # Clean up test session
        client.delete(f"/api/sessions/{session['id']}")


if __name__ == "__main__":
    test_delivery_metrics_accuracy()
    test_ats_cv_parser_across_real_cvs()
    test_south_african_and_global_research_and_live_gemini()
    print("ALL UPGRADE TESTS PASSED!")
