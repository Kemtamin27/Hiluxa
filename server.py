# ══════════════════════════════════════════════════════════════════════════
#  HILUXA ASTROLOJİ BACKEND  —  server.py
#
#  index.html dosyasındaki BACKEND_URL ('http://localhost:3000') ile
#  BİREBİR uyumlu iki uç noktayı sağlar:
#
#    POST /api/chart   → Swiss Ephemeris tabanlı milimetrik doğum haritası
#    POST /api/yorum    → Gerçek yapay zeka (Claude) tabanlı astrolojik yorum
#
#  index.html dosyasında TEK BİR SATIR bile değiştirmeye gerek yoktur;
#  frontend zaten bu iki uca istek atacak şekilde yazılmış.
# ══════════════════════════════════════════════════════════════════════════

import os
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from dotenv import load_dotenv

from ephemeris_engine import compute_full_chart, CITY_COORDS
from ai_client import get_ai_yorum, AIClientError

load_dotenv()

app = Flask(__name__)
CORS(app)  # Geliştirmede tüm originlere izin verir; PRODUCTION'da README'deki
           # "CORS'u Sıkılaştırma" bölümüne bakınız.

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("hiluxa")

MAX_PROMPT_CHARS = 20000  # kötüye kullanım / aşırı token maliyetine karşı üst sınır


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "HILUXA Astroloji Backend"})
@app.route("/")
def serve_index():
    return send_from_directory(".", "index.html")

@app.route("/api/chart", methods=["POST"])
def api_chart():
    """
    Beklenen istek gövdesi (frontend'in gönderdiği ile birebir aynı):
        { "year": 1995, "month": 6, "day": 15, "hour": "14:30", "city": "Istanbul" }

    Dönen yanıt, index.html -> calculateChart() fonksiyonunun 'data.planets'
    dalını tetikleyecek şekilde tasarlanmıştır:
        {
          "planets": {"Güneş": 83.91, "Ay": 296.69, ...},   // ham derece
          "houses":  {"Güneş": 9, "Ay": 4, ...},             // 1-12 Placidus evi
          "degrees": {...aynı planets...},
          "houseCusps": {"1": 191.67, ..., "12": 166.75},
          "meta": {...hassasiyet ve teknik bilgiler...}
        }
    """
    try:
        body = request.get_json(force=True, silent=False) or {}
        year = int(body["year"])
        month = int(body["month"])
        day = int(body["day"])
        hour_str = str(body.get("hour", "12:00"))
        city = body.get("city", "Istanbul")

        if not (1 <= month <= 12) or not (1 <= day <= 31) or not (1900 <= year <= 2100):
            return jsonify({"error": "Geçersiz tarih parametreleri."}), 400

        lat = body.get("lat")
        lon = body.get("lon")
        if lat is not None and lon is not None:
            lat, lon = float(lat), float(lon)
        else:
            lat = lon = None  # resolve_city üzerinden şehir adına göre bulunacak

        chart = compute_full_chart(year, month, day, hour_str, city, lat=lat, lon=lon)

        response = {
            "planets": chart["planets"],
            "degrees": chart["planets"],
            "houses": chart["houses"],
            "houseCusps": chart["houseCusps"],
            "signs": chart["signs"],
            "degreesInSign": {k: v["text"] for k, v in chart["degrees_in_sign"].items()},
            "ascendant": chart["ascendant"],
            "mc": chart["mc"],
            "vertex": chart["vertex"],
            "retrograde": chart["retrograde"],
            "meta": chart["meta"],
        }
        return jsonify(response)

    except KeyError as e:
        return jsonify({"error": f"Eksik alan: {e}"}), 400
    except Exception as e:
        log.exception("chart hesaplama hatası")
        return jsonify({"error": f"Hesaplama hatası: {e}"}), 500


@app.route("/api/yorum", methods=["POST"])
def api_yorum():
    """
    Beklenen istek gövdesi:
        { "prompt": "..." }   // frontend'in ürettiği tam astrolojik prompt

    Dönen yanıt:
        { "yorum": "...AI tarafından üretilmiş tam metin..." }

    Bu uç, gelen prompt'u DOĞRUDAN Anthropic Claude API'sine iletir ve
    modelin ürettiği yorumu aynen frontend'e döndürür. Frontend zaten
    bu uç başarısız olursa yerel (ozetAnalizUret) motoruna düşecek
    şekilde yazıldığı için, burada oluşabilecek bir hata sistemi
    ÇÖKERTMEZ — sadece frontend'in yedek moduna geçmesini sağlar.
    """
    try:
        body = request.get_json(force=True, silent=False) or {}
        prompt = body.get("prompt", "")
        if not prompt or not isinstance(prompt, str):
            return jsonify({"error": "Prompt boş veya geçersiz."}), 400
        if len(prompt) > MAX_PROMPT_CHARS:
            prompt = prompt[:MAX_PROMPT_CHARS]

        yorum = get_ai_yorum(prompt)
        return jsonify({"yorum": yorum})

    except AIClientError as e:
        log.warning("AI istemci hatası: %s", e)
        return jsonify({"error": str(e)}), 502
    except Exception as e:
        log.exception("yorum uretme hatası")
        return jsonify({"error": f"Sunucu hatası: {e}"}), 500


@app.route("/api/cities", methods=["GET"])
def api_cities():
    """Frontend ile senkron kalması için şehir listesini de backend'den
    servis edebilmek isteyenler için yardımcı uç (opsiyonel kullanım)."""
    return jsonify({"cities": {k: {"lat": v[0], "lon": v[1]} for k, v in CITY_COORDS.items()}})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 3000))
    debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    log.info("HILUXA backend başlıyor → http://localhost:%s", port)
    app.run(host="0.0.0.0", port=port, debug=debug)
