# ══════════════════════════════════════════════════════════════════════════
#  HILUXA — ai_client.py
#  index.html'den gelen astrolojik prompt'ları GERÇEK bir büyük dil modeline
#  (Anthropic Claude) ileten ince istemci katmanı.
#
#  Neden ayrı bir dosya?
#   - server.py'nin HTTP/route mantığından bağımsız, tek sorumluluk taşıyan
#     bir modül olarak; ileride OpenAI/Gemini gibi başka bir sağlayıcıya
#     geçmek istenirse SADECE bu dosya değiştirilir, server.py'ye dokunulmaz.
# ══════════════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════════════
#  HILUXA — ai_client.py
#  index.html'den gelen astrolojik prompt'ları GERÇEK bir büyük dil modeline
#  ileten ince istemci katmanı. İKİ sağlayıcıyı da destekler:
#
#    AI_PROVIDER=gemini     → Google Gemini API   (ücretsiz katman mevcut)
#    AI_PROVIDER=anthropic  → Anthropic Claude API (ücretli, kredi kartı gerekir)
#
#  Hangi sağlayıcının kullanılacağı SADECE .env dosyasındaki AI_PROVIDER
#  değişkeni ile belirlenir; server.py'ye HİÇBİR dokunuş gerekmez.
# ══════════════════════════════════════════════════════════════════════════

import os
import requests

AI_PROVIDER = os.environ.get("AI_PROVIDER", "gemini").strip().lower()

SYSTEM_PROMPT = (
    "Sen HILUXA uygulamasının profesyonel astroloji motorusun. "
    "Sana verilen doğum haritası verileri (gezegen, burç, ev, derece) "
    "İsviçre Efemerisi (Swiss Ephemeris) ile hesaplanmış GERÇEK ve KESİN "
    "verilerdir; bu verileri asla değiştirme, yeniden yorumlama veya "
    "kendi tahminlerinle çelişecek şekilde başka bir burç/ev/derece "
    "uydurma. Sadece sana verilen gezegen-burç-ev eşleşmeleri üzerinden "
    "derinlemesine, tutarlı, profesyonel ve akıcı Türkçe astrolojik "
    "yorum üret. Yanıtların her zaman istenen formatta, eksiksiz ve "
    "istenen uzunlukta olmalıdır."
)


class AIClientError(Exception):
    """API anahtarı eksik, ağ hatası veya sağlayıcı tarafı hata durumlarında
    fırlatılır. server.py bu hatayı yakalayıp uygun HTTP koduna çevirir."""
    pass


# ── GOOGLE GEMINI (varsayılan — ücretsiz katman) ───────────────────────────
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_MAX_TOKENS = int(os.environ.get("AI_MAX_TOKENS", "4096"))
DEFAULT_TEMPERATURE = float(os.environ.get("AI_TEMPERATURE", "0.85"))


def _call_gemini(prompt: str, max_tokens: int, temperature: float) -> str:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise AIClientError(
            "GEMINI_API_KEY tanımlı değil. .env dosyanıza "
            "GEMINI_API_KEY=AIza... satırını ekleyin. "
            "Ücretsiz anahtar: https://aistudio.google.com/apikey"
        )

    url = GEMINI_API_URL.format(model=DEFAULT_GEMINI_MODEL)
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
        },
    }
    headers = {"Content-Type": "application/json", "x-goog-api-key": api_key}

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=90)
    except requests.RequestException as e:
        raise AIClientError(f"Gemini API'ye bağlanılamadı: {e}")

    if resp.status_code != 200:
        try:
            err_detail = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            err_detail = resp.text
        raise AIClientError(f"Gemini API hatası ({resp.status_code}): {err_detail}")

    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        block_reason = data.get("promptFeedback", {}).get("blockReason")
        if block_reason:
            raise AIClientError(f"Gemini içeriği güvenlik filtresine takıldı: {block_reason}")
        raise AIClientError("Gemini boş yanıt döndürdü.")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(p.get("text", "") for p in parts).strip()
    if not text:
        raise AIClientError("Gemini boş metin döndürdü.")
    return text


# ── ANTHROPIC CLAUDE (opsiyonel — AI_PROVIDER=anthropic ile aktif) ─────────
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_VERSION = "2023-06-01"
DEFAULT_ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")


def _call_anthropic(prompt: str, max_tokens: int, temperature: float) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise AIClientError(
            "ANTHROPIC_API_KEY tanımlı değil. .env dosyanıza "
            "ANTHROPIC_API_KEY=sk-ant-... satırını ekleyin."
        )

    payload = {
        "model": DEFAULT_ANTHROPIC_MODEL,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    try:
        resp = requests.post(ANTHROPIC_API_URL, json=payload, headers=headers, timeout=90)
    except requests.RequestException as e:
        raise AIClientError(f"Anthropic API'ye bağlanılamadı: {e}")

    if resp.status_code != 200:
        try:
            err_detail = resp.json().get("error", {}).get("message", resp.text)
        except Exception:
            err_detail = resp.text
        raise AIClientError(f"Anthropic API hatası ({resp.status_code}): {err_detail}")

    data = resp.json()
    parts = data.get("content", [])
    text_chunks = [p.get("text", "") for p in parts if p.get("type") == "text"]
    full_text = "\n".join(t for t in text_chunks if t).strip()
    if not full_text:
        raise AIClientError("Anthropic boş yanıt döndürdü.")
    return full_text


def get_ai_yorum(prompt: str, max_tokens: int = None, temperature: float = None) -> str:
    """AI_PROVIDER ortam değişkenine göre doğru sağlayıcıya yönlendirir."""
    mt = max_tokens or DEFAULT_MAX_TOKENS
    temp = DEFAULT_TEMPERATURE if temperature is None else temperature

    if AI_PROVIDER == "anthropic":
        return _call_anthropic(prompt, mt, temp)
    if AI_PROVIDER == "gemini":
        return _call_gemini(prompt, mt, temp)
    raise AIClientError(
        f"Bilinmeyen AI_PROVIDER='{AI_PROVIDER}'. 'gemini' veya 'anthropic' olmalı."
    )

