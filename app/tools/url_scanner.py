import requests
from urllib.parse import urlparse

SECURITY_HEADERS = [
    "content-security-policy",
    "strict-transport-security",
    "x-frame-options",
    "x-content-type-options",
    "referrer-policy",
    "permissions-policy",
]


def normalize_url(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def analyze_url_security(url: str) -> str:
    target_url = normalize_url(url)
    parsed = urlparse(target_url)

    if not parsed.netloc:
        return "⚠️ URL tidak valid."

    try:
        response = requests.get(
            target_url,
            timeout=10,
            allow_redirects=True,
            headers={"User-Agent": "MrKBountyAI-SecurityCopilot/1.0"},
        )

        headers = {k.lower(): v for k, v in response.headers.items()}

        result = [
            "🔍 URL Security Analysis",
            "",
            f"Target: {target_url}",
            f"Final URL: {response.url}",
            f"Status Code: {response.status_code}",
            f"HTTPS: {'✅ Ya' if response.url.startswith('https://') else '❌ Tidak'}",
            f"Server: {headers.get('server', 'Tidak terlihat')}",
            "",
            "🛡 Security Headers",
        ]

        for header in SECURITY_HEADERS:
            if headers.get(header):
                result.append(f"✅ {header}: ada")
            else:
                result.append(f"❌ {header}: tidak ada")

        result.extend([
            "",
            "🍪 Cookie Security",
        ])

        if not response.cookies:
            result.append("ℹ️ Tidak ada cookie dari response utama.")
        else:
            for cookie in response.cookies:
                secure = "✅ Secure" if cookie.secure else "❌ Secure missing"
                result.append(f"- {cookie.name}: {secure}")

        result.extend([
            "",
            "📌 Catatan",
            "- Ini analisis pasif berdasarkan response header.",
            "- Gunakan hanya pada target yang kamu punya izin.",
            "- Header hilang bukan bukti bug, tapi sinyal untuk ditinjau.",
        ])

        return "\n".join(result)

    except requests.exceptions.Timeout:
        return "⚠️ Request timeout. Target terlalu lama merespons."
    except requests.exceptions.SSLError:
        return "⚠️ SSL error. Sertifikat HTTPS bermasalah."
    except requests.exceptions.RequestException as error:
        return f"⚠️ Gagal menganalisis URL.\n\nDetail: {error}"
