from app.agents.master_agent import detect_agent
from app.agents.mentor_agent import build_mentor_prompt
from app.agents.owasp_agent import build_owasp_prompt
from app.agents.report_agent import build_report_prompt
from app.agents.checklist_agent import build_checklist_prompt
from app.agents.memory_agent import build_memory_prompt


def select_agent_team(user_text: str):
    main_agent = detect_agent(user_text)

    team = ["mentor_agent"]

    if main_agent not in team:
        team.append(main_agent)

    text = user_text.lower()

    if any(word in text for word in ["analisis", "analysis", "kerentanan", "vulnerability", "bug"]):
        for agent in ["owasp_agent", "checklist_agent"]:
            if agent not in team:
                team.append(agent)

    if any(word in text for word in ["report", "laporan", "bug report", "poc"]):
        if "report_agent" not in team:
            team.append("report_agent")

    if any(word in text for word in ["ingat", "memory", "memori", "nama saya"]):
        if "memory_agent" not in team:
            team.append("memory_agent")

    return team


def build_agent_section(agent_name: str, user_text: str, knowledge_context: str) -> str:
    if agent_name == "owasp_agent":
        return build_owasp_prompt(user_text, knowledge_context)

    if agent_name == "report_agent":
        return build_report_prompt(user_text, knowledge_context)

    if agent_name == "checklist_agent":
        return build_checklist_prompt(user_text, knowledge_context)

    if agent_name == "memory_agent":
        return build_memory_prompt(user_text, knowledge_context)

    return build_mentor_prompt(user_text, knowledge_context)


def build_autonomous_prompt(user_text: str, knowledge_context: str) -> str:
    team = select_agent_team(user_text)

    agent_sections = []

    for agent_name in team:
        agent_sections.append(
            f"""
================ {agent_name.upper()} ================

{build_agent_section(agent_name, user_text, knowledge_context)}
"""
        )

    agents_combined = "\n\n".join(agent_sections)

    return f"""
Kamu adalah Autonomous Security Agent dari MrKBountyAI.

Tugas:
- Pilih dan gabungkan insight dari beberapa agent spesialis.
- Berikan jawaban final yang terstruktur, praktis, dan aman.
- Gunakan Knowledge Base dan Vector RAG sebagai konteks utama.
- Fokus pada edukasi, defensive security, authorized testing, dan responsible disclosure.

Agent yang aktif:
{", ".join(team)}

Knowledge Context:
{knowledge_context}

Hasil arahan agent spesialis:
{agents_combined}

Pertanyaan User:
{user_text}

Aturan keamanan:
- Jawab dalam bahasa Indonesia.
- Jangan membantu pencurian data, bypass akses ilegal, malware, phishing, atau eksploitasi tanpa izin.
- Jangan memberikan instruksi menyerang target nyata tanpa izin.
- Jika topik berisiko, arahkan ke lab legal, mitigasi, konsep aman, dan checklist etis.

Format jawaban final:
# Autonomous Security Analysis

## 1. Ringkasan

## 2. Konsep Utama

## 3. Kaitan dengan OWASP

## 4. Checklist Pengujian Aman

## 5. Dampak Potensial

## 6. Rekomendasi Mitigasi

## 7. Catatan Responsible Disclosure
"""
