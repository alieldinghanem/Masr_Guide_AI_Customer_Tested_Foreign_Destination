"""Curated starter catalog. Visit durations are illustrative, not opening hours."""

# Sources are reference links, not a guarantee of real-time operating information.
# Update periodically and verify admission rules on official venue sites before travel.

def place(slug, name, city, category, tags, lat, lng, minutes, summary, url, family=True):
    return {"id": slug, "name": name, "city": city, "category": category,
            "tags": tags, "lat": lat, "lng": lng, "visit_minutes": minutes,
            "description": summary, "source_url": url, "family_friendly": family}

PLACES = [
    place("giza-pyramids", "Pyramids of Giza", "Giza", "Heritage", ["history", "culture", "adventure"], 29.9792,31.1342,150,"The Giza plateau is home to the pyramids of Khufu, Khafre and Menkaure and their surrounding ancient monuments.","https://whc.unesco.org/en/list/86/"),
    place("great-sphinx", "Great Sphinx of Giza", "Giza", "Heritage", ["history", "culture", "family"], 29.9753,31.1376,60,"The limestone Great Sphinx stands on the Giza plateau, with a lion's body and a human head.","https://whc.unesco.org/en/list/86/"),
    place("grand-egyptian-museum", "Grand Egyptian Museum", "Giza", "Museum", ["museums", "history", "culture", "family"], 29.9940,31.1193,180,"A major archaeological museum near the Giza pyramids dedicated to ancient Egyptian heritage.","https://gem.eg/"),
    place("saqqara", "Saqqara Step Pyramid", "Giza", "Heritage", ["history", "culture"], 29.8713,31.2165,150,"The Step Pyramid of Djoser is part of the extensive ancient necropolis at Saqqara.","https://whc.unesco.org/en/list/86/"),
    place("citadel", "Citadel of Saladin", "Cairo", "Heritage", ["history", "culture", "family"], 30.0299,31.2613,120,"A historic medieval fortress overlooking Cairo, including significant monuments from later periods.","https://whc.unesco.org/en/list/89/"),
    place("egyptian-museum-tahrir", "Egyptian Museum in Tahrir", "Cairo", "Museum", ["museums", "history", "culture", "family"], 30.0478,31.2336,150,"A historic museum in central Cairo with a large collection of antiquities from ancient Egypt.","https://egymonuments.gov.eg/en/museums/egyptian-museum/"),
    place("nmec", "National Museum of Egyptian Civilization", "Cairo", "Museum", ["museums", "history", "culture", "family"], 30.0079,31.2482,150,"The NMEC presents Egypt's civilization across historical eras and houses the Royal Mummies Hall.","https://nmec.gov.eg/"),
    place("khan-el-khalili", "Khan el-Khalili", "Cairo", "Market", ["culture", "food", "family"], 30.0477,31.2622,100,"A traditional bazaar district in historic Cairo known for shops, crafts and lively streets.","https://whc.unesco.org/en/list/89/"),
    place("al-azhar-park", "Al-Azhar Park", "Cairo", "Park", ["nature", "family", "culture"], 30.0429,31.2657,90,"A landscaped urban park offering open spaces and views over historic Cairo.","https://www.azarpark.com/"),
    place("coptic-cairo", "Coptic Cairo", "Cairo", "Heritage", ["history", "culture", "family"], 30.0059,31.2307,120,"A historic area of Old Cairo containing important Christian religious landmarks.","https://whc.unesco.org/en/list/89/"),
    place("hanging-church", "The Hanging Church", "Cairo", "Heritage", ["history", "culture", "family"], 30.0054,31.2301,75,"A historic Coptic church in Old Cairo built above part of the Roman Fortress of Babylon.","https://egymonuments.gov.eg/monuments/the-hanging-church/"),
    place("bab-zuwayla", "Bab Zuwayla", "Cairo", "Heritage", ["history", "culture", "family"], 30.0428,31.2578,60,"A surviving southern gate of Fatimid Cairo, built in the late eleventh century.","https://egymonuments.gov.eg/monuments/bab-zuwayla"),
    # Additional Cairo attractions individually documented by Egyptian Ministry of
    # Tourism and Antiquities or UNESCO. Coordinates are approximate map pins, not routes.
    # Different places may share entry tickets or be neighbours; check venues first.
    place("museum-of-islamic-art", "Museum of Islamic Art", "Cairo", "Museum", ["museums", "history", "culture", "family"], 30.0446,31.2562,140, "A Cairo museum preserving art and objects from Islamic societies across centuries.", "https://egymonuments.gov.eg/museums/museum-of-islamic-art/"),
    place("gayer-anderson-museum", "Gayer-Anderson Museum", "Cairo", "Museum", ["museums", "history", "culture", "family"], 30.0292,31.2498,110, "Two historic Ottoman-era houses displaying domestic architecture and collections near Ibn Tulun Mosque.", "https://egymonuments.gov.eg/museums/gayer-anderson-museum/"),
    place("sultan-hassan-mosque", "Mosque and Madrasa of Sultan Hassan", "Cairo", "Heritage", ["history", "culture", "family"], 30.0309,31.2624,110, "Fourteenth-century Mamluk mosque and madrasa near the Citadel in historic Cairo.", "https://egymonuments.gov.eg/en/monuments/mosque-and-madrasa-of-sultan-hasan"),
    place("al-rifai-mosque", "Al-Rifa'i Mosque", "Cairo", "Heritage", ["history", "culture", "family"], 30.0312,31.2618,80, "A monumental mosque beside Sultan Hassan, with royal burials dating to the Muhammad Ali dynasty.", "https://egymonuments.gov.eg/en/monuments/al-rifa-i-mosque"),
    place("manial-palace-museum", "Manial Palace Museum", "Cairo", "Museum", ["history", "museums", "culture", "family"], 30.0274,31.2246,150, "Historic palace and gardens of Prince Muhammad Ali in the Manial district, displaying distinctive architecture and collections.", "https://egymonuments.gov.eg/en/museums/manial-palace-museum/"),
    place("baron-empain-palace", "Baron Empain Palace", "Cairo", "Heritage", ["history", "culture", "family"], 30.0870,31.3306,100, "Distinctive early twentieth-century palace in Heliopolis built for Baron Empain.", "https://egymonuments.gov.eg/en/monuments/baron-empain-palace"),
    place("ibn-tulun-mosque", "Mosque of Ahmad Ibn Tulun", "Cairo", "Heritage", ["history", "culture", "family"], 30.0287,31.2486,85, "Historic ninth-century mosque in Cairo known for its courtyard and architecture.", "https://whc.unesco.org/en/list/89/"),
    place("al-azhar-mosque", "Al-Azhar Mosque", "Cairo", "Heritage", ["history", "culture", "family"], 30.0459,31.2628,75, "Historic mosque and centre of Islamic learning in the heart of Cairo.", "https://whc.unesco.org/en/list/89/"),
    place("nilometer-roda", "Nilometer on Roda Island", "Cairo", "Heritage", ["history", "culture", "family"], 30.0065,31.2254,75, "Historic Nile water-level measurement structure on Roda Island in Cairo.", "https://whc.unesco.org/en/list/89/"),
    place("al-hakim-mosque", "Al-Hakim Mosque", "Cairo", "Heritage", ["history", "culture", "family"], 30.0545,31.2622,75, "Historic Fatimid-era mosque located in the northern part of Islamic Cairo.", "https://whc.unesco.org/en/list/89/"),
    place("karnak", "Karnak Temple Complex", "Luxor", "Heritage", ["history", "culture", "family"], 25.7188,32.6573,150,"A vast ancient Egyptian temple complex and part of the UNESCO-listed site of Ancient Thebes.","https://whc.unesco.org/en/list/87/"),
    place("luxor-temple", "Luxor Temple", "Luxor", "Heritage", ["history", "culture", "family"], 25.6995,32.6391,100,"A major temple on the east bank of the Nile, linked in antiquity with Karnak.","https://whc.unesco.org/en/list/87/"),
    place("valley-of-kings", "Valley of the Kings", "Luxor", "Heritage", ["history", "culture", "adventure"], 25.7402,32.6014,180,"A royal burial valley on Luxor's west bank featuring tombs of New Kingdom pharaohs.","https://whc.unesco.org/en/list/87/"),
    place("hatshepsut", "Temple of Hatshepsut", "Luxor", "Heritage", ["history", "culture", "family"], 25.7381,32.6061,100,"A striking terraced mortuary temple at Deir el-Bahari dedicated to Queen Hatshepsut.","https://whc.unesco.org/en/list/87/"),
    place("colossi-memnon", "Colossi of Memnon", "Luxor", "Heritage", ["history", "culture", "family"], 25.7206,32.6105,45,"Two monumental stone statues associated with the mortuary temple of Amenhotep III.","https://whc.unesco.org/en/list/87/"),
    place("philae", "Philae Temple", "Aswan", "Heritage", ["history", "culture", "family"], 24.0259,32.8846,150,"An island temple complex dedicated chiefly to Isis, relocated during the Nubian monument rescue campaign.","https://whc.unesco.org/en/list/88/"),
    place("aswan-high-dam", "Aswan High Dam", "Aswan", "Landmark", ["culture", "family"], 23.9708,32.8777,60,"A major modern dam across the Nile associated with the creation of Lake Nasser.","https://www.britannica.com/topic/Aswan-High-Dam"),
    place("nubian-museum", "Nubian Museum", "Aswan", "Museum", ["museums", "history", "culture", "family"], 24.0766,32.8957,110,"A museum interpreting the archaeology, arts and heritage of Nubia.","https://www.britannica.com/place/Nubia"),
    place("elephantine-island", "Elephantine Island", "Aswan", "Nature", ["history", "nature", "culture"], 24.0890,32.8900,120,"A Nile island with archaeological remains and communities near central Aswan.","https://www.britannica.com/place/Elephantine"),
    place("abu-simbel", "Abu Simbel Temples", "Abu Simbel", "Heritage", ["history", "culture", "adventure"], 22.3360,31.6258,160,"Two rock-cut temples built under Ramesses II; they were moved to save them from flooding.","https://whc.unesco.org/en/list/88/"),
    place("bibliotheca-alexandrina", "Bibliotheca Alexandrina", "Alexandria", "Culture", ["culture", "museums", "family"], 31.2089,29.9092,120,"A contemporary cultural center and library built near the site of ancient Alexandria's famous library.","https://www.bibalex.org/"),
    place("qaitbay", "Citadel of Qaitbay", "Alexandria", "Heritage", ["history", "culture", "family"], 31.2139,29.8854,100,"A 15th-century coastal fortress built at Alexandria's eastern harbor.","https://www.britannica.com/place/Alexandria-Egypt"),
    place("montaza-gardens", "Montaza Gardens", "Alexandria", "Park", ["nature", "family", "culture"], 31.2888,30.0160,100,"Seaside palace gardens on the eastern side of Alexandria, known for landscaped grounds.","https://www.britannica.com/place/Alexandria-Egypt"),
    place("catacombs-kom-shoqafa", "Catacombs of Kom el Shoqafa", "Alexandria", "Heritage", ["history", "culture"], 31.1788,29.8924,105,"A subterranean Roman-era burial complex reflecting Egyptian, Greek and Roman artistic influences.","https://www.britannica.com/place/Alexandria-Egypt"),
    place("ras-mohammed", "Ras Mohammed National Park", "Sharm El Sheikh", "Nature", ["nature", "beaches", "adventure"], 27.7376,34.2511,180,"A protected Red Sea coastal area known for coral reefs and marine biodiversity.","https://www.britannica.com/place/Red-Sea"),
    place("naama-bay", "Naama Bay", "Sharm El Sheikh", "Beach", ["beaches", "food", "family"], 27.9110,34.3264,120,"A beach and tourism hub in Sharm El Sheikh with seaside restaurants and leisure facilities.","https://www.britannica.com/place/Sharm-el-Sheikh"),
    place("soho-square", "SOHO Square", "Sharm El Sheikh", "Leisure", ["family", "food", "culture"], 27.9639,34.3952,100,"A modern shopping and entertainment square near Shark's Bay.","https://www.sohosquare-sharm.com/"),
    place("giftun-island", "Giftun Islands", "Hurghada", "Nature", ["beaches", "nature", "adventure"], 27.2046,33.9477,240,"Red Sea islands off Hurghada known for beaches and marine excursions; boat trips require separate arrangements.","https://www.britannica.com/place/Red-Sea"),
    place("hurghada-marina", "Hurghada Marina", "Hurghada", "Leisure", ["food", "family", "beaches"], 27.2240,33.8428,100,"A waterside promenade with restaurants, boats and visitor facilities.","https://www.britannica.com/place/Hurghada"),
    place("el-gouna", "El Gouna", "Hurghada", "Beach", ["beaches", "nature", "food", "family"], 27.3940,33.6780,160,"A planned Red Sea resort town north of Hurghada with lagoons and recreational activities.","https://www.elgouna.com/"),
    place("siwa-fortress", "Shali Fortress", "Siwa", "Heritage", ["culture", "history", "adventure"], 29.2032,25.5186,110,"The historic mud-brick settlement at the heart of Siwa Oasis.","https://www.britannica.com/place/Siwa-Oasis"),
    place("siwa-salt-lakes", "Siwa Salt Lakes", "Siwa", "Nature", ["nature", "adventure"], 29.1972,25.5529,130,"Saline pools around Siwa Oasis known for their distinctive colors and landscapes.","https://www.britannica.com/place/Siwa-Oasis"),
    place("oracle-temple", "Temple of the Oracle", "Siwa", "Heritage", ["history", "culture", "adventure"], 29.2053,25.5358,90,"Ancient oracle sanctuary in the Siwa Oasis associated with the god Amun.","https://www.britannica.com/place/Siwa-Oasis"),
    place("wadi-el-hitan", "Wadi Al-Hitan", "Fayoum", "Nature", ["nature", "history", "adventure"], 29.3333,30.1833,180,"A UNESCO World Heritage fossil site notable for early whale remains in the Western Desert.","https://whc.unesco.org/en/list/1186/"),
    place("qarun-lake", "Lake Qarun", "Fayoum", "Nature", ["nature", "family"], 29.4671,30.6214,110,"A large lake in the Fayoum depression with surrounding desert landscapes.","https://www.britannica.com/place/Al-Fayyum"),
    place("tunis-village", "Tunis Village", "Fayoum", "Culture", ["culture", "family", "food"], 29.3990,30.4926,110,"A lakeside village in Fayoum associated with pottery workshops and local crafts.","https://www.britannica.com/place/Al-Fayyum"),
    place("st-catherine-monastery", "Saint Catherine's Monastery", "Saint Catherine", "Heritage", ["history", "culture", "nature"], 28.5559,33.9760,130,"An early Christian monastery at the foot of Mount Sinai, part of a UNESCO World Heritage site.","https://whc.unesco.org/en/list/954/"),
    place("mount-sinai", "Mount Sinai", "Saint Catherine", "Nature", ["nature", "adventure", "history"], 28.5391,33.9750,300,"A mountain in the southern Sinai region, visited by hikers and pilgrims. Guided hiking may be required.","https://whc.unesco.org/en/list/954/", False),
    place("blue-hole-dahab", "Blue Hole", "Dahab", "Nature", ["beaches", "nature", "adventure"], 28.5727,34.5378,160,"A well-known Red Sea dive site near Dahab. Deep diving is hazardous and requires appropriate certified guidance.","https://www.britannica.com/place/Red-Sea", False),
    place("dahab-lagoon", "Dahab Lagoon", "Dahab", "Beach", ["beaches", "nature", "family"], 28.4826,34.5015,150,"A shallow coastal lagoon near Dahab popular for waterside relaxation and wind sports.","https://www.britannica.com/place/Dahab"),
]

INTERESTS = ["history", "culture", "museums", "nature", "beaches", "adventure", "food", "family"]

# Merge bilingual content (Arabic names/summaries, extra details, general tips).
from .catalog_extra import EXTRA  # noqa: E402

_missing = [p["id"] for p in PLACES if p["id"] not in EXTRA]
if _missing:  # fail fast at import time rather than serving incomplete records
    raise RuntimeError(f"catalog_extra is missing entries for: {_missing}")
for _p in PLACES:
    _p.update(EXTRA[_p["id"]])
