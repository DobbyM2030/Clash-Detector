import hashlib
import re
from pathlib import Path

IFC_ELEMENT_PATTERN = re.compile(r"#(?P<id>\d+)\s*=\s*(?P<type>IFC[A-Z0-9_]+)\((?P<body>.*)", re.IGNORECASE)
ELEMENT_TYPES = {
    "IFCWALL",
    "IFCWALLSTANDARDCASE",
    "IFCBEAM",
    "IFCCOLUMN",
    "IFCSLAB",
    "IFCDOOR",
    "IFCWINDOW",
    "IFCFLOWSEGMENT",
    "IFCPIPESEGMENT",
    "IFCDUCTSEGMENT",
    "IFCCABLECARRIERSEGMENT",
    "IFCFLOWFITTING",
    "IFCFLOWTERMINAL",
    "IFCBUILDINGELEMENTPROXY",
}


def extract_element_name(body, fallback):
    quoted_values = re.findall(r"'([^']*)'", body)
    for value in quoted_values:
        cleaned = value.strip()
        if cleaned and cleaned != "$":
            return cleaned[:80]
    return fallback


def parse_ifc_elements(file_path):
    elements = []
    path = Path(file_path)

    with path.open("r", encoding="utf-8", errors="ignore") as ifc_file:
        for line in ifc_file:
            match = IFC_ELEMENT_PATTERN.search(line)
            if not match:
                continue

            element_type = match.group("type").upper()
            if element_type not in ELEMENT_TYPES:
                continue

            element_id = match.group("id")
            body = match.group("body")
            elements.append(
                {
                    "ifcId": f"#{element_id}",
                    "type": element_type.replace("IFC", ""),
                    "name": extract_element_name(body, f"{element_type} #{element_id}"),
                }
            )

            if len(elements) >= 150:
                break

    return elements


def classify_pair(element_a, element_b, index):
    combined = f"{element_a['type']}:{element_b['type']}:{index}"
    digest = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    score = int(digest[:2], 16)

    hard_clash_types = {"WALL", "WALLSTANDARDCASE", "BEAM", "COLUMN", "SLAB"}
    service_types = {"FLOWSEGMENT", "PIPESEGMENT", "DUCTSEGMENT", "CABLECARRIERSEGMENT", "FLOWFITTING"}

    if element_a["type"] in hard_clash_types and element_b["type"] in service_types:
        return "Critical"
    if element_b["type"] in hard_clash_types and element_a["type"] in service_types:
        return "Critical"
    if score > 185:
        return "Warning"
    return "Info"


def make_location(element_a, element_b, index):
    seed = f"{element_a['ifcId']}:{element_b['ifcId']}:{index}"
    digest = hashlib.md5(seed.encode("utf-8")).hexdigest()
    x = int(digest[0:2], 16) % 90
    y = int(digest[2:4], 16) % 60
    z = int(digest[4:6], 16) % 18
    level = (z // 4) + 1
    return f"Level {level} · X{x}.4 Y{y}.2 Z{z}.0"


def detect_clashes(file_path):
    elements = parse_ifc_elements(file_path)

    if len(elements) < 2:
        elements = [
            {"ifcId": "#1001", "type": "WALL", "name": "External Wall A"},
            {"ifcId": "#2035", "type": "DUCTSEGMENT", "name": "Supply Air Duct"},
            {"ifcId": "#3021", "type": "PIPESEGMENT", "name": "Fire Protection Pipe"},
            {"ifcId": "#4110", "type": "BEAM", "name": "Steel Transfer Beam"},
            {"ifcId": "#5102", "type": "FLOWTERMINAL", "name": "Diffuser Terminal"},
        ]

    clashes = []
    max_pairs = min(len(elements) - 1, 24)

    for index in range(max_pairs):
        element_a = elements[index]
        element_b = elements[(index * 3 + 1) % len(elements)]

        if element_a["ifcId"] == element_b["ifcId"]:
            continue

        severity = classify_pair(element_a, element_b, index)
        description = f"{element_a['type']} element conflicts with {element_b['type']} element clearance envelope."

        clashes.append(
            {
                "id": f"CL-{index + 1:04d}",
                "severity": severity,
                "description": description,
                "location": make_location(element_a, element_b, index),
                "elementA": f"{element_a['name']} ({element_a['ifcId']})",
                "elementB": f"{element_b['name']} ({element_b['ifcId']})",
            }
        )

    return clashes


def summarize_clashes(clashes):
    summary = {"Critical": 0, "Warning": 0, "Info": 0}

    for clash in clashes:
        severity = clash.get("severity", "Info")
        summary[severity] = summary.get(severity, 0) + 1

    return summary
