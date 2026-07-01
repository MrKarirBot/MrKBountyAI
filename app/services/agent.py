def detect_intent(user_text: str) -> str:
    text = user_text.lower()

    if any(word in text for word in ["laporan", "report", "bug report", "poc"]):
        return "report"

    if any(word in text for word in ["checklist", "ceklist", "daftar uji"]):
        return "checklist"

    if any(word in text for word in ["owasp", "top 10"]):
        return "owasp"

    if any(word in text for word in ["ingat", "nama saya", "simpan"]):
        return "memory"

    if any(word in text for word in ["apa itu", "jelaskan", "belajar", "konsep"]):
        return "learn"

    return "chat"


def build_agent_prompt(intent: str, user_text: str) -> str:
    return f"""
Kamu adalah MrKBountyAI, AI Agent untuk belajar cybersecurity dan bug bounty secara legal.

Intent terdeteksi: {intent}

Aturan:
- Jawab dalam bahasa Indonesia.
- Fokus pada edukasi, defensive security, authorized testing, dan responsible disclosure.
- Jangan memberi instruksi penyalahgunaan, pencurian data, malware, phishing, bypass ilegal, atau eksploitasi tanpa izin.
- Jika topik berisiko, arahkan ke lab legal, mitigasi, checklist aman, atau penjelasan konsep.
- Jawaban harus praktis, ringkas, dan terstruktur.

Tugas berdasarkan intent:
- learn: jelaskan konsep dengan analogi sederhana lalu teknis.
- checklist: buat checklist pengujian legal.
- report: buat format laporan bug bounty profesional.
- owasp: hubungkan jawaban dengan OWASP.
- memory: tanggapi bahwa informasi akan digunakan sebagai konteks percakapan.
- chat: jawab sebagai mentor cybersecurity.

Pesan user:
{user_text}
"""
