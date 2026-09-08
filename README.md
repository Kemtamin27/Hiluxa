# HILUXA Astroloji Backend

`index.html` dosyanız değişmeden, olduğu gibi kalır. Bu backend sadece
frontend'in zaten aradığı iki uca (`/api/chart`, `/api/yorum`) gerçek
hesaplama ve gerçek yapay zeka bağlar.

```
frontend (index.html)  --HTTP-->  BACKEND_URL = http://localhost:3000
                                        │
                                        ├── POST /api/chart   → ephemeris_engine.py (Swiss Ephemeris)
                                        └── POST /api/yorum   → ai_client.py (Gemini / Claude)
```

---

## 1) Kurulum

```bash
cd hiluxa-backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

`.env` dosyası zaten sizin Gemini anahtarınızla dolu geldi
(`AI_PROVIDER=gemini`, `GEMINI_API_KEY=...`). Değiştirmek isterseniz
`.env.example` dosyasına bakın.

## 2) Çalıştırma

```bash
python3 server.py
```

Terminalde `HILUXA backend başlıyor → http://localhost:3000` yazısını
görmelisiniz. `index.html` dosyasını doğrudan tarayıcıda açtığınızda
(veya bir HTTP sunucusu ile servis ettiğinizde), `BACKEND_URL` zaten
`http://localhost:3000` olduğu için otomatik olarak bu sunucuya bağlanır.

## 3) Doğrulama (opsiyonel ama önerilir)

```bash
# Sunucu ayakta mı?
curl http://localhost:3000/api/health

# Gerçek Swiss Ephemeris hesaplaması çalışıyor mu?
curl -X POST http://localhost:3000/api/chart \
  -H "Content-Type: application/json" \
  -d '{"year":1995,"month":6,"day":15,"hour":"14:30","city":"Istanbul"}'

# AI (Gemini) gerçekten yanıt veriyor mu?
curl -X POST http://localhost:3000/api/yorum \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Kısaca kendini tanıt ve HILUXA astroloji motoru olarak hazır olduğunu söyle."}'
```

`/api/yorum` isteğine `{"yorum": "..."}` şeklinde gerçek bir metin
dönüyorsa AI bağlantısı çalışıyor demektir. `{"error": "..."}` dönerse,
hata mesajı sorunu tam olarak söyler (anahtar eksik/yanlış, kota
aşıldı, ağ sorunu vb.) — sistem asla sessizce çökmez, frontend otomatik
olarak yerel yedek metne (`ozetAnalizUret`) düşer.

---

## Hesaplama Hassasiyeti — Dürüst Teknik Açıklama

Sizden "milimetrik, asla sapma olmasın, İsviçre ile hesaplansın" isteği
geldiği için, gerçekte ne sunduğumu net söylüyorum, abartısız:

| Gövde | Kullanılan Model | Gerçek Hassasiyet |
|---|---|---|
| Güneş, Ay, Merkür, Venüs, Mars, Jüpiter, Satürn, Uranüs, Neptün, Plüton | Swiss Ephemeris — Moshier yarı-analitik model (sunucuda ek dosya yoksa otomatik bu moda düşer) | **1800–2400 yılları arasında ~1 açı-saniyesinin altı** (1/3600°). Astrolojide kullanılan derece hassasiyetinin çok üzerinde; profesyonel yazılımların (Astrodienst dahil) kullandığı referans modelin ta kendisi. |
| Kuzey/Güney Ay Düğümü, Lilith (Ay Apojesi) | Aynı motor, Gerçek (True) Düğüm | Aynı seviye |
| Yükselen, MC, Verteks, 12 Ev Tepe Noktası | Placidus ev sistemi, gerçek yıldız zamanına (sidereal time) dayalı tam hesap | Saniye bazlı doğum saatine kadar duyarlı |
| **Chiron, Juno** | Swiss Ephemeris'in asteroid veri dosyaları (`seas_18.se1`) internet üzerinden Astrodienst'ten indirilip sunucuya eklenmediği sürece, güncel (2024) osculating (anlık yörünge) Kepler elemanlarıyla hesaplanır | **Yay dakikası mertebesinde** (birkaç açı-dakikası) — yani gezegenin doğru burcu ve genelde doğru derecesi kesin, ama en uç derece sınırlarında (örn. burç geçişine 1-2 gün kala) nadir bir sapma teorik olarak mümkündür. |

**Chiron/Juno'yu da tam Swiss Ephemeris hassasiyetine çıkarmak isterseniz:**
1. https://www.astro.com/ftp/swisseph/ephe/ adresinden `seas_18.se1` dosyasını indirin
   (küçük bir dosyadır, ~500 KB — 1800-2400 aralığını kapsar).
2. Dosyayı `hiluxa-backend/ephe/` klasörüne koyun.
3. Sunucuyu yeniden başlatın — kod bu dosyayı otomatik algılar ve
   Chiron/Juno için de tam Swiss Ephemeris moduna geçer (kodda hiçbir
   değişiklik gerekmez, bkz. `ephemeris_engine.py` → `_HAS_AST_FILES`).

`/api/chart` yanıtındaki `meta` alanı, her doğum haritası için HANGİ
modelin fiilen kullanıldığını (`swisseph_tam_hassasiyet` /
`moshier_yay_saniyesi_alti` / `kepler_osculating`) açıkça raporlar —
istediğiniz zaman kontrol edebilirsiniz, hiçbir şey gizlenmez.

---

## AI Nasıl Çalışıyor?

`index.html` içindeki her mod (Bireysel Yorum, Sinastri, Kompozit,
Yıldızname) zaten kendi detaylı promptunu (Güneş hangi evde/burçta,
Ay hangi evde/burçta, stelyum var mı, ev yöneticileri kim, vb. dahil)
oluşturup `getAIYorum()` üzerinden `/api/yorum`'a gönderiyor. Bu backend:

1. Prompt'u alır,
2. Sistem talimatıyla (`SYSTEM_PROMPT`) birlikte Gemini'ye (veya
   `AI_PROVIDER=anthropic` yapılırsa Claude'a) iletir,
3. Modelin ürettiği TAM metni aynen frontend'e döner.

Yani gezegen-burç-ev verisi **gerçek Swiss Ephemeris çıktısından**
gelir, yorum metni ise **gerçek bir yapay zeka modelinden** gelir —
hiçbiri sahte/statik şablon değildir. Yerel `ozetAnalizUret()` sadece
AI çağrısı başarısız olursa (kota bitti, internet yok vb.) devreye
giren bir GÜVENLİK AĞIDIR, birincil kaynak değildir.

---

## Sağlayıcıyı Değiştirmek (Gemini ↔ Claude)

`.env` dosyasında sadece şu satırı değiştirin:

```
AI_PROVIDER=anthropic     # veya: gemini
```

İlgili API anahtarını (`ANTHROPIC_API_KEY` veya `GEMINI_API_KEY`) daha
önce doldurmuşsanız, başka hiçbir değişiklik gerekmez — `server.py` ve
`index.html` bu değişimden habersiz çalışmaya devam eder.

---

## Üretime (Canlıya) Alırken Dikkat Edilecekler

1. **CORS'u sıkılaştırın**: `server.py` içinde `CORS(app)` satırını
   `CORS(app, origins=["https://sizin-alan-adiniz.com"])` yapın.
2. **`.env` dosyasını asla repoya/sunucuya açık şekilde koymayın**;
   sunucu ortam değişkenleri (Render, Railway, Fly.io, VPS systemd
   env dosyası vb.) üzerinden enjekte edin.
3. **HTTPS zorunlu** — tarayıcılar `http://` üzerinden konum/PWA gibi
   bazı özellikleri kısıtlayabilir; ayrıca API anahtarınız düz metin
   HTTP üzerinde asla dolaşmamalı.
4. `index.html` içindeki `const BACKEND_URL = 'http://localhost:3000';`
   satırını canlı sunucunuzun adresiyle güncelleyin
   (örn. `https://api.hiluxa.app`) — bu, DEĞİŞMESİ GEREKEN TEK SATIRDIR,
   başka hiçbir şeye dokunmanıza gerek yoktur.
5. Rate limiting ekleyin (örn. `flask-limiter`) — hem AI maliyetinizi
   hem de kötüye kullanımı sınırlar.
6. Bu proje ticari/gerçek kullanıcılara sunulacaksa, astrolojik
   yorumların "eğlence/kişisel gelişim amaçlı" olduğuna dair bir
   sorumluluk reddi eklemeniz önerilir.

---

## Dosya Yapısı

```
hiluxa-backend/
├── server.py              # Flask uygulaması, /api/chart ve /api/yorum uçları
├── ephemeris_engine.py    # Swiss Ephemeris hesaplama motoru (bağımsız, test edilebilir)
├── ai_client.py           # Gemini/Claude AI istemcisi (sağlayıcıdan bağımsız arayüz)
├── requirements.txt       # Python bağımlılıkları
├── .env                   # Sizin gerçek anahtarlarınız (GİZLİ TUTUN)
├── .env.example           # Paylaşılabilir şablon
├── ephe/                  # (opsiyonel) Chiron/Juno için Swiss Ephemeris veri dosyaları
└── README.md              # Bu dosya
```
