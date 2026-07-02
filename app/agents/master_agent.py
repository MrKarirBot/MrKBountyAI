def detect_agent(user_text: str) -> str:
    text = user_text.lower()

    if any(word in text for word in [
        "report", "laporan", "bug report", "poc", "proof of concept"
    ]):
        return "report_agent"

    if any(word in text for word in [
        "checklist", "ceklist", "daftar uji", "langkah uji"
    ]):
        return "checklist_agent"

    if any(word in text for word in [
        "owasp", "top 10", "broken access control", "injection", "xss", "ssrf", "idor"
    ]):
        return "owasp_agent"

    if any(word in text for word in [
        "ingat", "nama saya", "simpan", "memory", "memori"
    ]):
        return "memory_agent"

    return "mentor_agent"


def build_master_prompt(agent_name: str, user_text: str, knowledge_context: str) -> str:
    return f"""
Kamu adalah Master Agent dari MrKBountyAI.

Tugasmu:
- Mengarahkan pertanyaan user ke agent spesialis.
- Menjaga jawaban tetap legal, edukatif, dan aman.
- Fokus pada cybersecurity, bug bounty, OWASP, defensive security, dan responsible disclosure.

Agent terpilih:
{agent_name}

Knowledge Base:
{knowledge_context}

Pesan user:
{user_text}

Aturan utama:
- Jawab dalam bahasa Indonesia.
- Jangan membantu tindakan ilegal, pencurian data, bypass akses tanpa izin, malware, phishing, atau penyalahgunaan.
- Jika pertanyaan berisiko, arahkan ke lab legal, mitigasi, atau konsep defensif.
"""
