from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

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

DEFAULT_SHEIKHS: List[str] = [
    "عبدالباسط عبدالصمد",
    "محمد صديق المنشاوي",
    "محمود خليل الحصري",
    "مشاري راشد العفاسي",
    "ماهر المعيقلي",
    "أحمد العجمي",
    "سعد الغامدي",
    "ياسر الدوسري",
    "علي جابر",
    "عبدالرحمن السديس",
]

DEFAULT_DATA: Dict[str, Any] = {
    "categories": {
        "chroma": {"surahs": {}, "sheikhs": {}},
        "designs": {"surahs": {}, "sheikhs": {}},
        "nature": [],
    },
    "settings": {
        "default_sheikhs": DEFAULT_SHEIKHS[:],
        "page_size": 12,
        "item_page_size": 8,
    },
}


def _copy_default() -> Dict[str, Any]:
    return json.loads(json.dumps(DEFAULT_DATA, ensure_ascii=False))


def _ensure_item(item: Any) -> Dict[str, Any]:
    if isinstance(item, dict):
        return {
            "media_type": str(item.get("media_type", "photo")),
            "file_id": str(item.get("file_id", "")),
            "caption": str(item.get("caption", "")),
        }
    return {"media_type": "photo", "file_id": str(item), "caption": ""}


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

        # Normalize surah items
        for surah, items in list(categories[category]["surahs"].items()):
            if not isinstance(items, list):
                categories[category]["surahs"][surah] = []
            else:
                categories[category]["surahs"][surah] = [_ensure_item(x) for x in items]

        # Normalize sheikh -> surah -> items
        for sheikh, value in list(categories[category]["sheikhs"].items()):
            if isinstance(value, list):
                categories[category]["sheikhs"][sheikh] = {"عام": [_ensure_item(x) for x in value]}
                continue
            if not isinstance(value, dict):
                categories[category]["sheikhs"][sheikh] = {}
                continue
            for surah, items in list(value.items()):
                if not isinstance(items, list):
                    categories[category]["sheikhs"][sheikh][surah] = []
                else:
                    categories[category]["sheikhs"][sheikh][surah] = [_ensure_item(x) for x in items]

    if "nature" not in categories or not isinstance(categories.get("nature"), list):
        categories["nature"] = []
    categories["nature"] = [_ensure_item(x) for x in categories["nature"]]

    settings = data["settings"]
    if not isinstance(settings.get("default_sheikhs"), list):
        settings["default_sheikhs"] = DEFAULT_SHEIKHS[:]
    else:
        settings["default_sheikhs"] = [str(x).strip() for x in settings["default_sheikhs"] if str(x).strip()]
    settings["page_size"] = int(settings.get("page_size", DEFAULT_DATA["settings"]["page_size"]))
    settings["item_page_size"] = int(settings.get("item_page_size", DEFAULT_DATA["settings"]["item_page_size"]))

    return data


class Storage:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.save(_copy_default())

    def load(self) -> Dict[str, Any]:
        if not self.path.exists():
            return _copy_default()
        with self.path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return ensure_structure(data)

    def save(self, data: Dict[str, Any]) -> None:
        data = ensure_structure(data)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _available_surahs(self, data: Dict[str, Any], category: str) -> List[str]:
        keys = set(data["categories"].get(category, {}).get("surahs", {}).keys())
        return [s for s in SURAHS if s in keys]

    def _available_sheikhs(self, data: Dict[str, Any], category: str) -> List[str]:
        out: List[str] = []
        sheikhs = data["categories"].get(category, {}).get("sheikhs", {})
        for sheikh, surah_map in sheikhs.items():
            if isinstance(surah_map, dict) and any(items for items in surah_map.values()):
                out.append(sheikh)
        return out

    def get_targets(
        self,
        content_type: str,
        data: Optional[Dict[str, Any]] = None,
        *,
        category: Optional[str] = None,
        available_only: bool = False,
    ) -> List[str]:
        data = data or self.load()
        if content_type == "surahs":
            if available_only and category in {"chroma", "designs"}:
                return self._available_surahs(data, category)
            return SURAHS[:]
        if content_type == "sheikhs":
            if available_only and category in {"chroma", "designs"}:
                return self._available_sheikhs(data, category)
            return data["settings"]["default_sheikhs"][:]
        return []

    def get_surah_targets_for_sheikh(self, data: Dict[str, Any], category: str, sheikh_name: str) -> List[str]:
        surah_map = data["categories"].get(category, {}).get("sheikhs", {}).get(sheikh_name, {})
        if not isinstance(surah_map, dict):
            return []
        out: List[str] = []
        if any(surah_map.get(k, []) for k in ("عشوائي", "عام")):
            out.append("عشوائي")
        keys = set(surah_map.keys())
        for surah in SURAHS:
            if surah in keys and surah_map.get(surah):
                out.append(surah)
        return out

    def get_items(
        self,
        data: Dict[str, Any],
        category: str,
        content_type: Optional[str],
        target_name: Optional[str],
        subtarget_name: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        if category == "nature":
            return data["categories"]["nature"]
        if content_type == "surahs":
            if not target_name:
                return []
            return data["categories"].get(category, {}).get("surahs", {}).get(target_name, [])
        if content_type == "sheikhs":
            if not target_name:
                return []
            sheikh_map = data["categories"].get(category, {}).get("sheikhs", {}).get(target_name, {})
            if not isinstance(sheikh_map, dict):
                return []
            if subtarget_name:
                if subtarget_name in sheikh_map:
                    return sheikh_map.get(subtarget_name, [])
                if subtarget_name == "عشوائي" and "عام" in sheikh_map:
                    return sheikh_map.get("عام", [])
                return []
            merged: List[Dict[str, Any]] = []
            if sheikh_map.get("عشوائي"):
                merged.extend(sheikh_map.get("عشوائي", []))
            elif sheikh_map.get("عام"):
                merged.extend(sheikh_map.get("عام", []))
            for surah in SURAHS:
                items = sheikh_map.get(surah, [])
                if items:
                    merged.extend(items)
            for key, items in sheikh_map.items():
                if key in SURAHS or key in {"عشوائي", "عام"}:
                    continue
                merged.extend(items)
            return merged
        return []

    def set_items(
        self,
        data: Dict[str, Any],
        category: str,
        content_type: str,
        target_name: str,
        items: List[Dict[str, Any]],
        subtarget_name: Optional[str] = None,
    ) -> None:
        if category == "nature":
            data["categories"]["nature"] = items
            return
        if content_type == "surahs":
            data["categories"][category][content_type][target_name] = items
            return
        if content_type == "sheikhs":
            sheikhs = data["categories"][category]["sheikhs"]
            sheikh_bucket = sheikhs.setdefault(target_name, {})
            if subtarget_name is None:
                subtarget_name = "عشوائي"
            sheikh_bucket[subtarget_name] = items

    def add_item(
        self,
        data: Dict[str, Any],
        category: str,
        content_type: Optional[str],
        target_name: Optional[str],
        item: Dict[str, Any],
        subtarget_name: Optional[str] = None,
    ) -> None:
        item = _ensure_item(item)
        if category == "nature":
            data["categories"]["nature"].append(item)
            return
        if content_type == "surahs":
            if content_type is None or target_name is None:
                return
            bucket = data["categories"][category]["surahs"].setdefault(target_name, [])
            bucket.append(item)
            return
        if content_type == "sheikhs":
            if target_name is None:
                return
            sheikh_bucket = data["categories"][category]["sheikhs"].setdefault(target_name, {})
            if not isinstance(sheikh_bucket, dict):
                sheikh_bucket = {"عشوائي": []}
                data["categories"][category]["sheikhs"][target_name] = sheikh_bucket
            if subtarget_name is None:
                subtarget_name = "عشوائي"
            sheikh_bucket.setdefault(subtarget_name, []).append(item)

    def remove_item(
        self,
        data: Dict[str, Any],
        category: str,
        content_type: Optional[str],
        target_name: Optional[str],
        item_index: int,
        subtarget_name: Optional[str] = None,
    ) -> bool:
        if category == "nature":
            items = data["categories"]["nature"]
            if 0 <= item_index < len(items):
                items.pop(item_index)
                return True
            return False
        if content_type == "surahs":
            if target_name is None:
                return False
            items = data["categories"][category]["surahs"].get(target_name, [])
            if 0 <= item_index < len(items):
                items.pop(item_index)
                return True
            return False
        if content_type == "sheikhs":
            if target_name is None:
                return False
            sheikh_map = data["categories"][category]["sheikhs"].get(target_name, {})
            if not isinstance(sheikh_map, dict):
                return False
            if subtarget_name:
                items = sheikh_map.get(subtarget_name, [])
                if 0 <= item_index < len(items):
                    items.pop(item_index)
                    return True
                return False
            merged: List[tuple[str, Dict[str, Any]]] = []
            for surah, items in sheikh_map.items():
                for item in items:
                    merged.append((surah, item))
            if 0 <= item_index < len(merged):
                # remove from the flattened list by searching again
                remaining = item_index
                for surah, items in sheikh_map.items():
                    if remaining < len(items):
                        items.pop(remaining)
                        return True
                    remaining -= len(items)
            return False
        return False

    def clear_target(
        self,
        data: Dict[str, Any],
        category: str,
        content_type: Optional[str],
        target_name: Optional[str],
        subtarget_name: Optional[str] = None,
    ) -> bool:
        if category == "nature":
            data["categories"]["nature"] = []
            return True
        if content_type == "surahs":
            if target_name is None:
                return False
            data["categories"][category]["surahs"][target_name] = []
            return True
        if content_type == "sheikhs":
            if target_name is None:
                return False
            sheikh_map = data["categories"][category]["sheikhs"].setdefault(target_name, {})
            if not isinstance(sheikh_map, dict):
                sheikh_map = {}
                data["categories"][category]["sheikhs"][target_name] = sheikh_map
            if subtarget_name:
                sheikh_map[subtarget_name] = []
            else:
                data["categories"][category]["sheikhs"][target_name] = {}
            return True
        return False

    def stats(self, data: Dict[str, Any]) -> Dict[str, int]:
        out = {"nature": len(data["categories"]["nature"]), "chroma": 0, "designs": 0}
        for cat in ("chroma", "designs"):
            for item in data["categories"][cat]["surahs"].values():
                out[cat] += len(item)
            for sheikh_map in data["categories"][cat]["sheikhs"].values():
                if isinstance(sheikh_map, dict):
                    for items in sheikh_map.values():
                        out[cat] += len(items)
        return out

    def add_sheikh_names(self, data: Dict[str, Any], names: List[str]) -> List[str]:
        current = data["settings"]["default_sheikhs"]
        added: List[str] = []
        existing = {name.strip() for name in current}
        for raw in names:
            name = raw.strip()
            if not name or name in existing:
                continue
            current.append(name)
            existing.add(name)
            added.append(name)
        return added
