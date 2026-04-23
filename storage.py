from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

DEFAULT_DATA = {
    "categories": {
        "chroma": {"surahs": {}, "sheikhs": {}},
        "designs": {"surahs": {}, "sheikhs": {}},
        "nature": []
    },
    "settings": {
        "default_sheikhs": [
            "عبدالباسط عبدالصمد",
            "محمد صديق المنشاوي",
            "محمود خليل الحصري",
            "مشاري راشد العفاسي",
            "ماهر المعيقلي",
            "أحمد العجمي",
            "سعد الغامدي",
            "ياسر الدوسري",
            "علي جابر",
            "عبدالرحمن السديس"
        ],
        "page_size": 12,
        "item_page_size": 8
    }
}

SURAHS: List[str] = [
    "الفاتحة","البقرة","آل عمران","النساء","المائدة","الأنعام","الأعراف","الأنفال","التوبة",
    "يونس","هود","يوسف","الرعد","إبراهيم","الحجر","النحل","الإسراء","الكهف","مريم","طه",
    "الأنبياء","الحج","المؤمنون","النور","الفرقان","الشعراء","النمل","القصص","العنكبوت",
    "الروم","لقمان","السجدة","الأحزاب","سبأ","فاطر","يس","الصافات","ص","الزمر","غافر",
    "فصلت","الشورى","الزخرف","الدخان","الجاثية","الأحقاف","محمد","الفتح","الحجرات","ق",
    "الذاريات","الطور","النجم","القمر","الرحمن","الواقعة","الحديد","المجادلة","الحشر",
    "الممتحنة","الصف","الجمعة","المنافقون","التغابن","الطلاق","التحريم","الملك","القلم",
    "الحاقة","المعارج","نوح","الجن","المزمل","المدثر","القيامة","الإنسان","المرسلات",
    "النبأ","النازعات","عبس","التكوير","الانفطار","المطففين","الانشقاق","البروج","الطارق",
    "الأعلى","الغاشية","الفجر","البلد","الشمس","الليل","الضحى","الشرح","التين","العلق",
    "القدر","البينة","الزلزلة","العاديات","القارعة","التكاثر","العصر","الهمزة","الفيل",
    "قريش","الماعون","الكوثر","الكافرون","النصر","المسد","الإخلاص","الفلق","الناس"
]


def ensure_structure(data: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(data, dict):
        data = {}

    for key, value in DEFAULT_DATA.items():
        if key not in data or not isinstance(data[key], type(value)):
            data[key] = json.loads(json.dumps(value, ensure_ascii=False))

    categories = data["categories"]
    for category in ("chroma", "designs"):
        if category not in categories or not isinstance(categories.get(category), dict):
            categories[category] = {"surahs": {}, "sheikhs": {}}
        for t in ("surahs", "sheikhs"):
            if t not in categories[category] or not isinstance(categories[category].get(t), dict):
                categories[category][t] = {}

    if "nature" not in categories or not isinstance(categories.get("nature"), list):
        categories["nature"] = []

    settings = data["settings"]
    if not isinstance(settings.get("default_sheikhs"), list):
        settings["default_sheikhs"] = DEFAULT_DATA["settings"]["default_sheikhs"][:]
    settings["page_size"] = int(settings.get("page_size", DEFAULT_DATA["settings"]["page_size"]))
    settings["item_page_size"] = int(settings.get("item_page_size", DEFAULT_DATA["settings"]["item_page_size"]))

    return data


class Storage:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save(json.loads(json.dumps(DEFAULT_DATA, ensure_ascii=False)))

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return json.loads(json.dumps(DEFAULT_DATA, ensure_ascii=False))
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return ensure_structure(data)

    def save(self, data: Dict[str, Any]) -> None:
        data = ensure_structure(data)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get_target_name(self, content_type: str, index: int, data: Optional[Dict[str, Any]] = None) -> Optional[str]:
        if content_type == "surahs":
            if 0 <= index < len(SURAHS):
                return SURAHS[index]
            return None
        if content_type == "sheikhs":
            source = (data or self.load())["settings"]["default_sheikhs"]
            if 0 <= index < len(source):
                return source[index]
            return None
        return None

    def get_targets(self, content_type: str, data: Optional[Dict[str, Any]] = None) -> List[str]:
        if content_type == "surahs":
            return SURAHS[:]
        if content_type == "sheikhs":
            return (data or self.load())["settings"]["default_sheikhs"][:]
        return []

    def get_items(self, data: Dict[str, Any], category: str, content_type: Optional[str], target_name: Optional[str]) -> List[Dict[str, Any]]:
        if category == "nature":
            return data["categories"]["nature"]
        if content_type is None or target_name is None:
            return []
        return data["categories"].get(category, {}).get(content_type, {}).get(target_name, [])

    def set_items(self, data: Dict[str, Any], category: str, content_type: str, target_name: str, items: List[Dict[str, Any]]) -> None:
        data["categories"][category][content_type][target_name] = items

    def add_item(self, data: Dict[str, Any], category: str, content_type: Optional[str], target_name: Optional[str], item: Dict[str, Any]) -> None:
        if category == "nature":
            data["categories"]["nature"].append(item)
            return
        if content_type is None or target_name is None:
            return
        bucket = data["categories"][category][content_type].setdefault(target_name, [])
        bucket.append(item)

    def remove_item(self, data: Dict[str, Any], category: str, content_type: Optional[str], target_name: Optional[str], item_index: int) -> bool:
        if category == "nature":
            items = data["categories"]["nature"]
            if 0 <= item_index < len(items):
                items.pop(item_index)
                return True
            return False
        if content_type is None or target_name is None:
            return False
        items = data["categories"][category][content_type].get(target_name, [])
        if 0 <= item_index < len(items):
            items.pop(item_index)
            return True
        return False

    def clear_target(self, data: Dict[str, Any], category: str, content_type: Optional[str], target_name: Optional[str]) -> bool:
        if category == "nature":
            data["categories"]["nature"] = []
            return True
        if content_type is None or target_name is None:
            return False
        data["categories"][category][content_type][target_name] = []
        return True

    def stats(self, data: Dict[str, Any]) -> Dict[str, int]:
        out = {"nature": len(data["categories"]["nature"]), "chroma": 0, "designs": 0}
        for cat in ("chroma", "designs"):
            for t in ("surahs", "sheikhs"):
                for items in data["categories"][cat][t].values():
                    out[cat] += len(items)
        return out
