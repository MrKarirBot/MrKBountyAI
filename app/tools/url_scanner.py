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
            headers={
                "User-Agent": "MrKBountyAI-SecurityCopilot/1.0"
            },
        )

        headers = {
            key.lower(): value
            for key, value in response.headers.items()
        }

        result = []
        result.append("🔍 URL Security Analysis")
        result.append("")
        result.append(f"Target: {target_url}")
        result.append(f"Final URL: {response.url}")
        result.append(f"Status Code: {response.status_code}")
        result.append(f"HTTPS: {'✅ Ya' if response.url.startswith('https://') else '❌ Tidak'}")
        result.append(f"Server: {headers.get('server', 'Tidak terlihat')}")
        result.append("")

        result.append("🛡 Security Headers")
        for header in SECURITY_HEADERS:
            value = headers.get(header)

            if value:
                result.append(f"✅ {header}: ada")
            else:
                result.append(f"❌ {header}: tidak ada")

        result.append("")
        result.append("🍪 Cookie Security")

        cookies = response.cookies

        if not cookies:
            result.append("ℹ️ Tidak ada cookie dari response utama.")
        else:
            for cookie in cookies:
                secure = "✅ Secure" if cookie.secure else "❌ Secure missing"
                httponly = "ℹ️ HttpOnly tidak bisa dipastikan dari requests"
                result.append(f"- {cookie.name}: {secure}, {httponly}")

        result.append("")
        result.append("📌 Catatan")
        result.append("- Ini analisis pasif berdasarkan response header.")
        result.append("- Gunakan hanya pada target yang kamu miliki izin.")
        result.append("- Header yang hilang bukan selalu bug, tapi sinyal untuk ditinjau.")

        return "\n".join(result)

    except requests.exceptions.Timeout:
        return "⚠️ Request timeout. Target terlalu lama merespons."

    except requests.exceptions.SSLError:
        return "⚠️ SSL error. Sertifikat HTTPS bermasalah atau tidak valid."

    except requests.exceptions.RequestException as error:
        return f"⚠️ Gagal menganalisis URL.\n\nDetail: {error}"
