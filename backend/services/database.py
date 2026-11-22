from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Any, Iterator

from config import settings


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(settings.database_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cv_documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                file_size_bytes INTEGER NOT NULL,
                page_count INTEGER NOT NULL,
                raw_text TEXT NOT NULL,
                candidate_profile_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS company_research_cache (
                company_key TEXT PRIMARY KEY,
                company_name TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS interview_sessions (
                id TEXT PRIMARY KEY,
                cv_document_id TEXT,
                company_name TEXT NOT NULL,
                target_role TEXT NOT NULL,
                round_focus TEXT NOT NULL DEFAULT 'full_loop',
                job_description TEXT NOT NULL,
                jd_signals_json TEXT NOT NULL,
                company_research_json TEXT NOT NULL,
                candidate_profile_json TEXT NOT NULL,
                explore_pillars_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'in_progress',
                current_question_index INTEGER NOT NULL DEFAULT 0,
                overall_score INTEGER,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS session_questions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                order_index INTEGER NOT NULL,
                short_title TEXT NOT NULL,
                category TEXT NOT NULL,
                question_text TEXT NOT NULL,
                source_attribution TEXT NOT NULL,
                guidance_cues_json TEXT NOT NULL,
                evaluation_focus_json TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'up_next',
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS question_attempts (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                question_id TEXT NOT NULL,
                attempt_number INTEGER NOT NULL DEFAULT 1,
                duration_seconds REAL NOT NULL DEFAULT 0,
                stt_provider TEXT NOT NULL DEFAULT 'browser_live',
                transcript_verbatim TEXT NOT NULL,
                transcript_clean TEXT NOT NULL,
                word_timestamps_json TEXT NOT NULL,
                delivery_metrics_json TEXT NOT NULL,
                evaluation_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE,
                FOREIGN KEY (question_id) REFERENCES session_questions(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS study_items (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                question_id TEXT,
                company_name TEXT NOT NULL DEFAULT '',
                target_role TEXT NOT NULL DEFAULT '',
                topic TEXT NOT NULL,
                subtitle TEXT NOT NULL DEFAULT '',
                why TEXT NOT NULL,
                search_query_or_resource TEXT NOT NULL,
                resource_url TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
            );
            """
        )


def save_cv_document(
    filename: str,
    file_type: str,
    file_size_bytes: int,
    page_count: int,
    raw_text: str,
    candidate_profile: dict[str, Any],
) -> dict[str, Any]:
    doc_id = str(uuid.uuid4())
    now = utc_now()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO cv_documents (
                id, filename, file_type, file_size_bytes, page_count,
                raw_text, candidate_profile_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id,
                filename,
                file_type,
                file_size_bytes,
                page_count,
                raw_text,
                json.dumps(candidate_profile),
                now,
            ),
        )
    return {
        "id": doc_id,
        "filename": filename,
        "file_type": file_type,
        "file_size_bytes": file_size_bytes,
        "page_count": page_count,
        "raw_text": raw_text,
        "candidate_profile": candidate_profile,
        "created_at": now,
    }


def get_cv_document(doc_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM cv_documents WHERE id = ?", (doc_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "filename": row["filename"],
            "file_type": row["file_type"],
            "file_size_bytes": row["file_size_bytes"],
            "page_count": row["page_count"],
            "raw_text": row["raw_text"],
            "candidate_profile": json.loads(row["candidate_profile_json"]),
            "created_at": row["created_at"],
        }


def delete_cv_document(doc_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM cv_documents WHERE id = ?", (doc_id,))
        return cur.rowcount > 0


def get_cached_company_research(company_key: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT payload_json FROM company_research_cache WHERE company_key = ?",
            (company_key,),
        ).fetchone()
        if not row:
            return None
        return json.loads(row["payload_json"])


def save_cached_company_research(company_key: str, company_name: str, payload: dict[str, Any]) -> None:
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO company_research_cache (company_key, company_name, payload_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(company_key) DO UPDATE SET
                company_name = excluded.company_name,
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            (company_key, company_name, json.dumps(payload), utc_now()),
        )


def create_session_record(
    cv_document_id: str | None,
    company_name: str,
    target_role: str,
    round_focus: str,
    job_description: str,
    jd_signals: list[str],
    company_research: dict[str, Any],
    candidate_profile: dict[str, Any],
    explore_pillars: list[dict[str, Any]],
    questions: list[dict[str, Any]],
) -> dict[str, Any]:
    session_id = str(uuid.uuid4())
    now = utc_now()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO interview_sessions (
                id, cv_document_id, company_name, target_role, round_focus,
                job_description, jd_signals_json, company_research_json,
                candidate_profile_json, explore_pillars_json, status,
                current_question_index, overall_score, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                cv_document_id,
                company_name,
                target_role,
                round_focus,
                job_description,
                json.dumps(jd_signals),
                json.dumps(company_research),
                json.dumps(candidate_profile),
                json.dumps(explore_pillars),
                "in_progress",
                0,
                None,
                now,
                now,
            ),
        )
        for idx, q in enumerate(questions):
            q_id = str(uuid.uuid4())
            q_status = "in_progress" if idx == 0 else "up_next"
            conn.execute(
                """
                INSERT INTO session_questions (
                    id, session_id, order_index, short_title, category,
                    question_text, source_attribution, guidance_cues_json,
                    evaluation_focus_json, status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    q_id,
                    session_id,
                    idx,
                    q["short_title"],
                    q["category"],
                    q["question_text"],
                    q["source_attribution"],
                    json.dumps(q.get("guidance_cues", [])),
                    json.dumps(q.get("evaluation_focus", [])),
                    q_status,
                    now,
                ),
            )
    result = get_session_record(session_id)
    assert result is not None
    return result


def get_session_record(session_id: str) -> dict[str, Any] | None:
    with get_conn() as conn:
        s_row = conn.execute("SELECT * FROM interview_sessions WHERE id = ?", (session_id,)).fetchone()
        if not s_row:
            return None
        q_rows = conn.execute(
            "SELECT * FROM session_questions WHERE session_id = ? ORDER BY order_index ASC",
            (session_id,),
        ).fetchall()

        questions: list[dict[str, Any]] = []
        for qr in q_rows:
            a_row = conn.execute(
                """
                SELECT * FROM question_attempts
                WHERE question_id = ?
                ORDER BY attempt_number DESC
                LIMIT 1
                """,
                (qr["id"],),
            ).fetchone()
            latest_attempt = None
            if a_row:
                latest_attempt = {
                    "id": a_row["id"],
                    "attempt_number": a_row["attempt_number"],
                    "duration_seconds": a_row["duration_seconds"],
                    "stt_provider": a_row["stt_provider"],
                    "transcript_verbatim": a_row["transcript_verbatim"],
                    "transcript_clean": a_row["transcript_clean"],
                    "word_timestamps": json.loads(a_row["word_timestamps_json"]),
                    "delivery_metrics": json.loads(a_row["delivery_metrics_json"]),
                    "evaluation": json.loads(a_row["evaluation_json"]),
                    "created_at": a_row["created_at"],
                }
            questions.append(
                {
                    "id": qr["id"],
                    "order_index": qr["order_index"],
                    "short_title": qr["short_title"],
                    "category": qr["category"],
                    "question_text": qr["question_text"],
                    "source_attribution": qr["source_attribution"],
                    "guidance_cues": json.loads(qr["guidance_cues_json"]),
                    "evaluation_focus": json.loads(qr["evaluation_focus_json"]),
                    "status": qr["status"],
                    "latest_attempt": latest_attempt,
                }
            )

        return {
            "id": s_row["id"],
            "cv_document_id": s_row["cv_document_id"],
            "company_name": s_row["company_name"],
            "target_role": s_row["target_role"],
            "round_focus": s_row["round_focus"],
            "job_description": s_row["job_description"],
            "jd_signals": json.loads(s_row["jd_signals_json"]),
            "company_research": json.loads(s_row["company_research_json"]),
            "candidate_profile": json.loads(s_row["candidate_profile_json"]),
            "explore_pillars": json.loads(s_row["explore_pillars_json"]),
            "status": s_row["status"],
            "current_question_index": s_row["current_question_index"],
            "overall_score": s_row["overall_score"],
            "questions": questions,
            "created_at": s_row["created_at"],
            "updated_at": s_row["updated_at"],
        }


def list_session_records() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT id FROM interview_sessions ORDER BY updated_at DESC"
        ).fetchall()
    sessions: list[dict[str, Any]] = []
    for r in rows:
        rec = get_session_record(r["id"])
        if rec:
            sessions.append(rec)
    return sessions


def delete_session_record(session_id: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM interview_sessions WHERE id = ?", (session_id,))
        return cur.rowcount > 0


def save_question_attempt(
    session_id: str,
    question_id: str,
    duration_seconds: float,
    stt_provider: str,
    transcript_verbatim: str,
    transcript_clean: str,
    word_timestamps: list[dict[str, Any]],
    delivery_metrics: dict[str, Any],
    evaluation: dict[str, Any],
    company_name: str,
    target_role: str,
) -> dict[str, Any]:
    attempt_id = str(uuid.uuid4())
    now = utc_now()
    with get_conn() as conn:
        count_row = conn.execute(
            "SELECT COALESCE(MAX(attempt_number), 0) AS max_n FROM question_attempts WHERE question_id = ?",
            (question_id,),
        ).fetchone()
        attempt_number = int(count_row["max_n"]) + 1

        conn.execute(
            """
            INSERT INTO question_attempts (
                id, session_id, question_id, attempt_number, duration_seconds,
                stt_provider, transcript_verbatim, transcript_clean,
                word_timestamps_json, delivery_metrics_json, evaluation_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                attempt_id,
                session_id,
                question_id,
                attempt_number,
                duration_seconds,
                stt_provider,
                transcript_verbatim,
                transcript_clean,
                json.dumps(word_timestamps),
                json.dumps(delivery_metrics),
                json.dumps(evaluation),
                now,
            ),
        )

        # Mark current question completed and advance next question if applicable
        conn.execute(
            "UPDATE session_questions SET status = 'completed' WHERE id = ?",
            (question_id,),
        )

        q_rows = conn.execute(
            "SELECT id, order_index, status FROM session_questions WHERE session_id = ? ORDER BY order_index ASC",
            (session_id,),
        ).fetchall()

        next_idx = len(q_rows) - 1
        all_done = True
        for qr in q_rows:
            if qr["status"] != "completed":
                all_done = False
                next_idx = qr["order_index"]
                conn.execute(
                    "UPDATE session_questions SET status = 'in_progress' WHERE id = ?",
                    (qr["id"],),
                )
                break

        # Compute session average overall score from latest attempt per question
        scores: list[int] = []
        for qr in q_rows:
            latest = conn.execute(
                """
                SELECT evaluation_json FROM question_attempts
                WHERE question_id = ? ORDER BY attempt_number DESC LIMIT 1
                """,
                (qr["id"],),
            ).fetchone()
            if latest:
                ev = json.loads(latest["evaluation_json"])
                sc = ev.get("scores", {}).get("overall")
                if isinstance(sc, (int, float)):
                    scores.append(int(round(sc)))

        avg_overall = int(round(sum(scores) / len(scores))) if scores else None
        new_status = "completed" if all_done else "in_progress"

        conn.execute(
            """
            UPDATE interview_sessions
            SET current_question_index = ?, overall_score = ?, status = ?, updated_at = ?
            WHERE id = ?
            """,
            (next_idx, avg_overall, new_status, now, session_id),
        )

        # Save study material items (deduplicated per session + topic)
        for item in evaluation.get("study_material", []):
            topic = item.get("topic", "").strip()
            if not topic:
                continue
            existing = conn.execute(
                "SELECT id FROM study_items WHERE session_id = ? AND lower(topic) = lower(?)",
                (session_id, topic),
            ).fetchone()
            if not existing:
                conn.execute(
                    """
                    INSERT INTO study_items (
                        id, session_id, question_id, company_name, target_role,
                        topic, subtitle, why, search_query_or_resource, resource_url,
                        completed, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
                    """,
                    (
                        str(uuid.uuid4()),
                        session_id,
                        question_id,
                        company_name,
                        target_role,
                        topic,
                        item.get("subtitle", ""),
                        item.get("why", ""),
                        item.get("search_query_or_resource", topic),
                        item.get("resource_url", ""),
                        now,
                    ),
                )

    return {
        "id": attempt_id,
        "attempt_number": attempt_number,
        "duration_seconds": duration_seconds,
        "stt_provider": stt_provider,
        "transcript_verbatim": transcript_verbatim,
        "transcript_clean": transcript_clean,
        "word_timestamps": word_timestamps,
        "delivery_metrics": delivery_metrics,
        "evaluation": evaluation,
        "created_at": now,
    }


def list_study_items() -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM study_items ORDER BY completed ASC, created_at DESC"
        ).fetchall()
    return [
        {
            "id": r["id"],
            "session_id": r["session_id"],
            "company_name": r["company_name"],
            "target_role": r["target_role"],
            "topic": r["topic"],
            "subtitle": r["subtitle"],
            "why": r["why"],
            "search_query_or_resource": r["search_query_or_resource"],
            "resource_url": r["resource_url"],
            "completed": bool(r["completed"]),
            "created_at": r["created_at"],
        }
        for r in rows
    ]


def toggle_study_item(item_id: str, completed: bool) -> dict[str, Any] | None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE study_items SET completed = ? WHERE id = ?",
            (1 if completed else 0, item_id),
        )
        r = conn.execute("SELECT * FROM study_items WHERE id = ?", (item_id,)).fetchone()
        if not r:
            return None
        return {
            "id": r["id"],
            "session_id": r["session_id"],
            "company_name": r["company_name"],
            "target_role": r["target_role"],
            "topic": r["topic"],
            "subtitle": r["subtitle"],
            "why": r["why"],
            "search_query_or_resource": r["search_query_or_resource"],
            "resource_url": r["resource_url"],
            "completed": bool(r["completed"]),
            "created_at": r["created_at"],
        }


def get_overview_stats() -> dict[str, Any]:
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    with get_conn() as conn:
        total_sessions = conn.execute("SELECT COUNT(*) AS c FROM interview_sessions").fetchone()["c"]
        week_sessions = conn.execute(
            "SELECT COUNT(*) AS c FROM interview_sessions WHERE created_at >= ?",
            (week_ago,),
        ).fetchone()["c"]
        attempt_rows = conn.execute("SELECT evaluation_json FROM question_attempts").fetchall()

        comm_list: list[int] = []
        tech_list: list[int] = []
        struct_list: list[int] = []
        conf_list: list[int] = []
        overall_list: list[int] = []

        for r in attempt_rows:
            ev = json.loads(r["evaluation_json"])
            sc = ev.get("scores", {})
            if "communication" in sc:
                comm_list.append(int(sc["communication"]))
            if "technical_depth" in sc:
                tech_list.append(int(sc["technical_depth"]))
            if "structure" in sc:
                struct_list.append(int(sc["structure"]))
            if "confidence" in sc:
                conf_list.append(int(sc["confidence"]))
            if "overall" in sc:
                overall_list.append(int(sc["overall"]))

        def avg(vals: list[int]) -> int:
            return int(round(sum(vals) / len(vals))) if vals else 0

        recent_rows = conn.execute(
            """
            SELECT id, company_name, target_role, status, overall_score, created_at, updated_at
            FROM interview_sessions
            ORDER BY updated_at DESC
            LIMIT 6
            """
        ).fetchall()

        recent_sessions = []
        for sr in recent_rows:
            q_total = conn.execute(
                "SELECT COUNT(*) AS c FROM session_questions WHERE session_id = ?", (sr["id"],)
            ).fetchone()["c"]
            q_done = conn.execute(
                "SELECT COUNT(*) AS c FROM session_questions WHERE session_id = ? AND status = 'completed'",
                (sr["id"],),
            ).fetchone()["c"]
            recent_sessions.append(
                {
                    "id": sr["id"],
                    "company_name": sr["company_name"],
                    "target_role": sr["target_role"],
                    "status": sr["status"],
                    "overall_score": sr["overall_score"],
                    "completed_questions": q_done,
                    "total_questions": q_total,
                    "created_at": sr["created_at"],
                    "updated_at": sr["updated_at"],
                }
            )

    return {
        "sessions_this_week": week_sessions,
        "weekly_goal": 3,
        "total_sessions": total_sessions,
        "total_answers_evaluated": len(attempt_rows),
        "average_overall": avg(overall_list) if overall_list else None,
        "average_scores": {
            "communication": avg(comm_list),
            "technical_depth": avg(tech_list),
            "structure": avg(struct_list),
            "confidence": avg(conf_list),
        },
        "recent_sessions": recent_sessions,
    }
