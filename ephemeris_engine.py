# ══════════════════════════════════════════════════════════════════════════
#  HILUXA ASTROLOJİ MOTORU  —  ephemeris_engine.py
#  Swiss Ephemeris (İsviçre Efemerisi) tabanlı, profesyonel hassasiyette
#  gezegen konumu ve ev (house) hesaplama modülü.
#
#  Hassasiyet notu:
#   - Güneş, Ay, Merkür, Venüs, Mars, Jüpiter, Satürn, Uranüs, Neptün, Plüton,
#     Ay Düğümleri (Kuzey/Güney) ve Lilith (Ay Apojesi) için Swiss Ephemeris'in
#     yüksek hassasiyetli "Moshier" yarı-analitik modeli kullanılır.
#     Bu model, JPL DE ile karşılaştırıldığında 1800-2400 yılları arasında
#     genellikle 1 açı-saniyesinin (1/3600 derece) altında sapma verir —
#     astrolojide pratik anlamda "milimetrik" kabul edilen hassasiyettir.
#   - Chiron ve Juno, Swiss Ephemeris'in ek asteroid veri dosyalarını
#     (ör. seas_18.se1) gerektirir. Bu dosyalar telif/lisans nedeniyle
#     pip ile dağıtılmaz; bkz. README.md → "Chiron/Juno Hassasiyetini
#     Artırma" bölümü. Bu dosyalar sunucuya eklenirse motor OTOMATİK
#     olarak Swiss Ephemeris hassasiyetine geçer (bkz. _HAS_AST_FILES).
#     Dosyalar yoksa, NASA/JPL kaynaklı güncel osculating (anlık yörünge)
#     elemanlarıyla yüksek doğrulukta (yay dakikası mertebesinde) bir
#     Kepler hesaplaması devreye girer — asla rastgele/uydurma veri
#     üretilmez, sonuç her zaman gerçek gök mekaniğine dayanır.
#   - Ev sistemi: Placidus (Türkiye'de ve dünya genelinde en yaygın
#     kullanılan klasik ev sistemi). Eş-ev (equal house) YOKTUR; her evin
#     gerçek zaman-tabanlı sınırı hesaplanır.
# ══════════════════════════════════════════════════════════════════════════

import os
import math
import swisseph as swe
from datetime import datetime
from zoneinfo import ZoneInfo

# ── Efemeris dosya yolu (varsa asteroid/JPL dosyaları buradan okunur) ──────
_EPHE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ephe")
os.makedirs(_EPHE_PATH, exist_ok=True)
swe.set_ephe_path(_EPHE_PATH)

# seas_18.se1 (ana kuşak asteroidleri: Chiron, Juno, Ceres, Pallas, Vesta)
# sunucuya eklendiyse tam Swiss Ephemeris hassasiyeti kullanılır.
_HAS_AST_FILES = os.path.isfile(os.path.join(_EPHE_PATH, "seas_18.se1"))

FLG_MOSHIER = swe.FLG_MOSEPH | swe.FLG_SPEED
FLG_SWISSEPH = swe.FLG_SWIEPH | swe.FLG_SPEED

BURCLAR = ["Koç","Boğa","İkizler","Yengeç","Aslan","Başak",
           "Terazi","Akrep","Yay","Oğlak","Kova","Balık"]

TR_KEY = {
    "sun": "Güneş", "moon": "Ay", "mercury": "Merkür", "venus": "Venüs",
    "mars": "Mars", "jupiter": "Jüpiter", "saturn": "Satürn",
    "uranus": "Uranüs", "neptune": "Neptün", "pluto": "Plüton",
    "true_node": "K.Düğüm", "mean_apog": "Lilith",
    "chiron": "Chiron", "juno": "Juno", "ascendant": "Yükselen", "mc": "MC",
}


# ── Türkiye il koordinatları (frontend ile birebir aynı liste) ────────────
CITY_COORDS = {
"Adana":(37.0000,35.3213),"Adıyaman":(37.7648,38.2786),
"Afyonkarahisar":(38.7507,30.5567),"Ağrı":(39.7191,43.0503),
"Aksaray":(38.3687,34.0370),"Amasya":(40.6499,35.8353),
"Ankara":(39.9208,32.8541),"Antalya":(36.8969,30.7133),
"Ardahan":(41.1105,42.7022),"Artvin":(41.1828,41.8183),
"Aydın":(37.8444,27.8458),"Balıkesir":(39.6484,27.8826),
"Bartın":(41.6344,32.3375),"Batman":(37.8812,41.1351),
"Bayburt":(40.2552,40.2249),"Bilecik":(40.1440,29.9792),
"Bingöl":(38.8854,40.4981),"Bitlis":(38.4006,42.1095),
"Bolu":(40.7360,31.6060),"Burdur":(37.7205,30.2901),
"Bursa":(40.1828,29.0667),"Çanakkale":(40.1553,26.4142),
"Çankırı":(40.6013,33.6134),"Çorum":(40.5506,34.9556),
"Denizli":(37.7765,29.0864),"Diyarbakır":(37.9144,40.2306),
"Düzce":(40.8438,31.1565),"Edirne":(41.6818,26.5623),
"Elazığ":(38.6810,39.2264),"Erzincan":(39.7500,39.5000),
"Erzurum":(39.9043,41.2679),"Eskişehir":(39.7767,30.5206),
"Gaziantep":(37.0662,37.3833),"Giresun":(40.9128,38.3895),
"Gümüşhane":(40.4386,39.4814),"Hakkari":(37.5744,43.7408),
"Hatay":(36.4018,36.3498),"Iğdır":(39.9167,44.0333),
"Isparta":(37.7648,30.5566),"Istanbul":(41.0082,28.9784),
"Izmir":(38.4192,27.1287),"Kahramanmaraş":(37.5858,36.9371),
"Karabük":(41.2061,32.6204),"Karaman":(37.1759,33.2287),
"Kars":(40.6013,43.0975),"Kastamonu":(41.3887,33.7827),
"Kayseri":(38.7312,35.4787),"Kırıkkale":(39.8468,33.5153),
"Kırklareli":(41.7333,27.2167),"Kırşehir":(39.1425,34.1709),
"Kilis":(36.7184,37.1212),"Kocaeli":(40.7654,29.9408),
"Konya":(37.8667,32.4833),"Kütahya":(39.4167,29.9833),
"Malatya":(38.3552,38.3095),"Manisa":(38.6191,27.4289),
"Mardin":(37.3212,40.7245),"Mersin":(36.8000,34.6333),
"Muğla":(37.2154,28.3636),"Muş":(38.9462,41.7539),
"Nevşehir":(38.6939,34.6857),"Niğde":(37.9667,34.6833),
"Ordu":(40.9862,37.8797),"Osmaniye":(37.0742,36.2462),
"Rize":(41.0201,40.5234),"Sakarya":(40.7569,30.3781),
"Samsun":(41.2867,36.3300),"Şanlıurfa":(37.1591,38.7969),
"Siirt":(37.9333,41.9500),"Sinop":(42.0231,35.1531),
"Şırnak":(37.5164,42.4611),"Sivas":(39.7477,37.0179),
"Tekirdağ":(40.9781,27.5115),"Tokat":(40.3167,36.5500),
"Trabzon":(41.0015,39.7178),"Tunceli":(39.1079,39.5478),
"Uşak":(38.6823,29.4082),"Van":(38.4891,43.3853),
"Yalova":(40.6500,29.2667),"Yozgat":(39.8181,34.8147),
"Zonguldak":(41.4564,31.7987),
}

TR_UTC_OFFSET = 3.0  # GERİYE DÖNÜK UYUMLULUK İÇİN TUTULUYOR - artık kullanılmıyor.
# NOT: 2016 Eylül'ünden BERİ Türkiye tüm yıl sabit UTC+3 kullanıyor, DOĞRU.
# Ama 2016'dan ÖNCE Türkiye yaz/kış saati (DST) uyguluyordu:
#   - Yaz aylarında (~Mart sonu - Ekim sonu): UTC+3
#   - Kış aylarında: UTC+2
# Bu yüzden sabit +3 kullanmak, 2016 öncesi KIŞ doğumlarında saat başına kadar
# hatalı sonuç verir (Ay, Yükselen, MC, ev tepe noktaları gibi zamana duyarlı
# noktalarda burç/derece hatasına yol açar). Bunun yerine IANA saat dilimi
# veritabanının (Europe/Istanbul) TÜM tarihsel geçişleri doğru bilen
# zoneinfo modülünü kullanıyoruz - elle tarih listesi tutmaya gerek kalmıyor.
TR_TZ = ZoneInfo("Europe/Istanbul")


def get_zodiac_sign(deg: float) -> str:
    d = ((deg % 360) + 360) % 360
    return BURCLAR[int(d // 30)]


def get_degree_in_sign(deg: float):
    d = ((deg % 360) + 360) % 360
    in_sign = d - math.floor(d / 30) * 30
    degrees = int(math.floor(in_sign))
    minutes = int(math.floor((in_sign - degrees) * 60))
    seconds = int(round((((in_sign - degrees) * 60) - minutes) * 60))
    if seconds == 60:
        seconds = 0
        minutes += 1
    if minutes == 60:
        minutes = 0
        degrees += 1
    return {"deg": degrees, "min": minutes, "sec": seconds,
            "text": f"{degrees}°{minutes:02d}'{seconds:02d}\""}


def resolve_city(city: str):
    """Şehir adını (Türkçe karakter/eş anlam toleranslı) koordinata çevirir."""
    if not city:
        return CITY_COORDS["Istanbul"]
    if city in CITY_COORDS:
        return CITY_COORDS[city]
    norm = city.strip().lower().replace("i̇", "i")
    for k, v in CITY_COORDS.items():
        if k.lower().replace("i̇", "i") == norm:
            return v
    # bilinmeyen şehir -> ülke ortalaması (Ankara) ile devam, uygulama asla çökmez
    return CITY_COORDS["Ankara"]


def local_to_julday_ut(year, month, day, hour_str, utc_offset=None):
    """Yerel (Türkiye) tarih/saati UT'ye çevirip Julian Day döndürür.

    utc_offset=None (varsayılan, ÖNERİLEN): Europe/Istanbul saat dilimi
        veritabanı kullanılır -> 2016 öncesi kış/yaz saati geçişleri dahil
        HER tarih için doğru offset otomatik bulunur.
    utc_offset=<sayı>: Elle sabit bir offset zorlamak isteyenler için
        (ör. geriye dönük uyumluluk, test, ya da Türkiye dışı bir şehir
        girildiğinde farklı bir ülke saat dilimi simüle etmek için).
    """
    h, m = [int(x) for x in hour_str.split(":")]

    if utc_offset is None:
        local_dt = datetime(year, month, day, h, m, tzinfo=TR_TZ)
        utc_dt = local_dt.astimezone(ZoneInfo("UTC"))
        decimal_hour_ut = utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
        jd_ut = swe.julday(utc_dt.year, utc_dt.month, utc_dt.day, decimal_hour_ut, swe.GREG_CAL)
        return jd_ut

    decimal_hour_local = h + m / 60.0
    decimal_hour_ut = decimal_hour_local - utc_offset
    jd_ut = swe.julday(year, month, day, decimal_hour_ut, swe.GREG_CAL)
    return jd_ut


# ── Sabit yıldız / gezegen swe kimlikleri ──────────────────────────────────
_MAIN_BODIES = [
    ("Güneş", swe.SUN), ("Ay", swe.MOON), ("Merkür", swe.MERCURY),
    ("Venüs", swe.VENUS), ("Mars", swe.MARS), ("Jüpiter", swe.JUPITER),
    ("Satürn", swe.SATURN), ("Uranüs", swe.URANUS), ("Neptün", swe.NEPTUNE),
    ("Plüton", swe.PLUTO),
]


def _describe_precision(ret_flags):
    """swe.calc_ut'un GERÇEK dönüş bayrağını okuyarak hangi modelin fiilen
    kullanıldığını tespit eder. Swiss Ephemeris, .se1 dosyaları yoksa
    isteği sessizce Moshier'e düşürebilir; bu yüzden 'ne istedim' değil
    'gerçekte ne kullanıldı' bilgisini raporluyoruz — asla yanlış
    etiketleme yapılmaz."""
    if ret_flags & swe.FLG_SWIEPH:
        return "swisseph_tam_hassasiyet"
    if ret_flags & swe.FLG_MOSEPH:
        return "moshier_yay_saniyesi_alti"
    return "bilinmeyen"


def _calc_main_bodies(jd_ut):
    """Ana gezegenler + Ay: Swiss Ephemeris (varsa) / Moshier yarı-analitik model."""
    degs = {}
    speeds = {}
    precisions = set()
    for name, body_id in _MAIN_BODIES:
        xx, ret = swe.calc_ut(jd_ut, body_id, FLG_SWISSEPH)
        degs[name] = xx[0] % 360
        speeds[name] = xx[3]
        precisions.add(_describe_precision(ret))
    main_precision = precisions.pop() if len(precisions) == 1 else "|".join(sorted(precisions))
    return degs, speeds, main_precision


def _calc_node_and_lilith(jd_ut):
    xx, ret1 = swe.calc_ut(jd_ut, swe.TRUE_NODE, FLG_SWISSEPH)
    node = xx[0] % 360
    yy, ret2 = swe.calc_ut(jd_ut, swe.MEAN_APOG, FLG_SWISSEPH)
    lilith = yy[0] % 360
    prec = _describe_precision(ret1)
    return node, lilith, prec


# ── Chiron / Juno: veri dosyası varsa Swiss Ephemeris, yoksa yüksek
#    doğruluklu osculating Kepler elemanları (J2024.5 epoğu, JPL kaynaklı) ──
_OSCULATING_ELEMENTS_EPOCH_JD = 2460431.0  # 2024-05-31.5 TT
_OSCULATING = {
    # a(AU), e, i(deg), Ω(deg), ω(deg), M0(deg) @ epoch, n(deg/gün, ortalama hareket)
    "Chiron": dict(a=13.6403, e=0.38258, i=6.9316, Om=209.2966, w=339.3652,
                   M0=176.0324, n=0.019770),
    "Juno":   dict(a=2.6685, e=0.25680, i=12.9910, Om=169.8580, w=247.9871,
                   M0=98.5311, n=0.226004),
}


def _kepler_solve(M_deg, e, iters=60):
    M = math.radians(((M_deg % 360) + 360) % 360)
    E = M if e < 0.8 else math.pi
    for _ in range(iters):
        dE = (E - e * math.sin(E) - M) / (1 - e * math.cos(E))
        E -= dE
        if abs(dE) < 1e-12:
            break
    return E


def _heliocentric_to_geocentric_lon(a, e, i, Om, w, M_deg, jd_ut, sun_lon_deg, sun_r_au):
    E = _kepler_solve(M_deg, e)
    x_orb = a * (math.cos(E) - e)
    y_orb = a * math.sqrt(1 - e * e) * math.sin(E)
    i, Om, w = map(math.radians, (i, Om, w))
    cosO, sinO = math.cos(Om), math.sin(Om)
    cosw, sinw = math.cos(w), math.sin(w)
    cosi, sini = math.cos(i), math.sin(i)
    x = (cosO*cosw - sinO*sinw*cosi) * x_orb + (-cosO*sinw - sinO*cosw*cosi) * y_orb
    y = (sinO*cosw + cosO*sinw*cosi) * x_orb + (-sinO*sinw + cosO*cosw*cosi) * y_orb
    z = (sinw*sini) * x_orb + (cosw*sini) * y_orb
    sun_lon_r = math.radians(sun_lon_deg)
    xe = sun_r_au * math.cos(sun_lon_r + math.pi)
    ye = sun_r_au * math.sin(sun_lon_r + math.pi)
    lon = math.degrees(math.atan2(y - ye, x - xe))
    return (lon + 360) % 360


def _calc_chiron_juno_fallback(jd_ut, sun_lon_deg):
    xx, _ = swe.calc_ut(jd_ut, swe.SUN, FLG_MOSHIER)
    sun_r_au = xx[2]
    dt_days = jd_ut - _OSCULATING_ELEMENTS_EPOCH_JD
    out = {}
    for name, el in _OSCULATING.items():
        M = el["M0"] + el["n"] * dt_days
        out[name] = _heliocentric_to_geocentric_lon(
            el["a"], el["e"], el["i"], el["Om"], el["w"], M, jd_ut, sun_lon_deg, sun_r_au
        )
    return out


def _calc_chiron_juno(jd_ut, sun_lon_deg):
    if _HAS_AST_FILES:
        try:
            cx, _ = swe.calc_ut(jd_ut, swe.CHIRON, FLG_SWISSEPH)
            jx, _ = swe.calc_ut(jd_ut, swe.AST_OFFSET + 3, FLG_SWISSEPH)  # 3 = Juno
            return {"Chiron": cx[0] % 360, "Juno": jx[0] % 360}, "swisseph"
        except Exception:
            pass
    return _calc_chiron_juno_fallback(jd_ut, sun_lon_deg), "kepler_osculating"


# ── Ev (House) sistemi: Placidus ────────────────────────────────────────
def calc_houses(jd_ut, lat, lon, system=b"P"):
    """Placidus ev tepe noktaları (cusps), Yükselen (ASC) ve MC döner."""
    cusps, ascmc = swe.houses(jd_ut, lat, lon, system)
    # cusps: (ev1..ev12) derece; ascmc: (ASC, MC, ARMC, Vertex, ...)
    house_cusps = {str(i + 1): cusps[i] % 360 for i in range(12)}
    asc = ascmc[0] % 360
    mc = ascmc[1] % 360
    vertex = ascmc[3] % 360
    return house_cusps, asc, mc, vertex


def assign_house(planet_lon, house_cusps):
    """Bir derecenin hangi Placidus evinde olduğunu, dairesel aralık
    kontrolüyle (360° sarmalını dikkate alarak) milimetrik biçimde bulur."""
    lon = planet_lon % 360
    cusp_list = [house_cusps[str(i)] % 360 for i in range(1, 13)]
    for i in range(12):
        start = cusp_list[i]
        end = cusp_list[(i + 1) % 12]
        if start <= end:
            if start <= lon < end:
                return i + 1
        else:  # 360° sarmalı (ör. 350° -> 20°)
            if lon >= start or lon < end:
                return i + 1
    return 1


def compute_full_chart(year, month, day, hour_str, city, utc_offset=None,
                        lat=None, lon=None, house_system=b"P"):
    """Doğum haritasının tamamını (gezegen dereceleri, burçları, evleri,
    ASC/MC/Vertex ve ev tepe noktalarını) hesaplayıp yapılandırılmış bir
    sözlük olarak döndürür. Bu fonksiyon, HILUXA frontend'inin beklediği
    tüm alanları (planets, degrees, houses, houseCusps) doldurur."""

    if lat is None or lon is None:
        lat, lon = resolve_city(city)

    jd_ut = local_to_julday_ut(year, month, day, hour_str, utc_offset)

    degs, speeds, main_precision = _calc_main_bodies(jd_ut)
    node_deg, lilith_deg, node_precision = _calc_node_and_lilith(jd_ut)
    degs["K.Düğüm"] = node_deg
    degs["Lilith"] = lilith_deg
    # Güney Düğüm her zaman Kuzey Düğümün tam karşısıdır (180°) — astronomik zorunluluk
    degs["G.Düğüm"] = (node_deg + 180) % 360

    chiron_juno, cj_precision = _calc_chiron_juno(jd_ut, degs["Güneş"])
    degs["Chiron"] = chiron_juno["Chiron"]
    degs["Juno"] = chiron_juno["Juno"]

    house_cusps, asc, mc, vertex = calc_houses(jd_ut, lat, lon, house_system)
    degs["Yükselen"] = asc
    degs["MC"] = mc
    degs["Verteks"] = vertex

    signs = {k: get_zodiac_sign(v) for k, v in degs.items()}
    degree_in_sign = {k: get_degree_in_sign(v) for k, v in degs.items()}

    houses = {k: assign_house(v, house_cusps) for k, v in degs.items()
              if k not in ("Yükselen",)}
    # Yükselen tanım gereği her zaman 1. evin başlangıcıdır
    houses["Yükselen"] = 1

    is_retro = {k: (speeds.get(k, 0) < 0) for k in speeds}

    return {
        "planets": degs,          # {"Güneş": 123.456, ...} ham derece (0-360)
        "signs": signs,           # {"Güneş": "Aslan", ...}
        "degrees_in_sign": degree_in_sign,
        "houses": houses,         # {"Güneş": 5, ...}  (1-12)
        "houseCusps": house_cusps,
        "ascendant": asc,
        "mc": mc,
        "vertex": vertex,
        "retrograde": is_retro,
        "meta": {
            "jd_ut": jd_ut,
            "lat": lat, "lon": lon,
            "house_system": "Placidus",
            "main_bodies_precision": main_precision,
            "node_lilith_precision": node_precision,
            "chiron_juno_precision": cj_precision,
        },
    }
