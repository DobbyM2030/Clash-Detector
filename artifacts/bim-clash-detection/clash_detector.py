from dataclasses import dataclass
from itertools import combinations
STRUCTURAL_TYPES = {
    "IfcBeam",
    "IfcColumn",
    "IfcFooting",
    "IfcMember",
    "IfcPile",
    "IfcPlate",
    "IfcRailing",
    "IfcRamp",
    "IfcRampFlight",
    "IfcRoof",
    "IfcSlab",
    "IfcStair",
    "IfcStairFlight",
    "IfcWall",
    "IfcWallStandardCase",
}

MEP_TYPES = {
    "IfcCableCarrierSegment",
    "IfcCableSegment",
    "IfcDistributionFlowElement",
    "IfcDuctFitting",
    "IfcDuctSegment",
    "IfcFlowFitting",
    "IfcFlowSegment",
    "IfcPipeFitting",
    "IfcPipeSegment",
}

SUPPORT_TYPES = {
    "IfcBuildingElementProxy",
    "IfcDiscreteAccessory",
    "IfcFastener",
    "IfcMechanicalFastener",
    "IfcMember",
    "IfcPlate",
}

OPENING_TYPES = {"IfcDoor", "IfcWindow", "IfcOpeningElement"}
REBAR_TYPES = {"IfcReinforcingBar", "IfcReinforcingMesh", "IfcTendon", "IfcTendonAnchor"}
PIPE_TYPES = {"IfcPipeSegment", "IfcPipeFitting", "IfcFlowSegment"}
CABLE_TRAY_TYPES = {"IfcCableCarrierSegment", "IfcCableCarrierFitting"}
STRUCTURAL_JOINT_TYPES = {"IfcBeam", "IfcColumn", "IfcMember", "IfcPlate", "IfcSlab", "IfcWall", "IfcWallStandardCase"}

MIN_OVERLAP_TOLERANCE = 0.003
MAX_ELEMENTS = 450
MAX_CLASHES = 500
MAX_IGNORED_CLASHES = 500


@dataclass
class ElementGeometry:
    entity: object
    global_id: str
    ifc_id: str
    ifc_type: str
    name: str
    bbox_min: tuple[float, float, float]
    bbox_max: tuple[float, float, float]
    center: tuple[float, float, float]
    volume: float
    container: str
    material: str
    predefined_type: str


def get_ifcopenshell():
    try:
        import ifcopenshell
        import ifcopenshell.geom
    except ImportError as exc:
        raise RuntimeError("IfcOpenShell is not installed. Install project dependencies before running geometry clash detection.") from exc
    return ifcopenshell


def safe_string(value):
    if value is None:
        return ""
    return str(value).strip()


def normalize_words(*values):
    return " ".join(safe_string(value).lower() for value in values if value)


def get_container_name(entity):
    try:
        contained_in = getattr(entity, "ContainedInStructure", None) or []
        for relation in contained_in:
            structure = getattr(relation, "RelatingStructure", None)
            if structure:
                return safe_string(getattr(structure, "Name", "")) or safe_string(getattr(structure, "LongName", ""))
    except Exception:
        return ""
    return ""


def get_material_name(entity):
    names = []
    try:
        for association in getattr(entity, "HasAssociations", None) or []:
            material = getattr(association, "RelatingMaterial", None)
            if not material:
                continue
            if hasattr(material, "Name"):
                names.append(safe_string(material.Name))
            if hasattr(material, "Materials"):
                names.extend(safe_string(getattr(item, "Name", "")) for item in material.Materials)
            if hasattr(material, "MaterialLayers"):
                for layer in material.MaterialLayers:
                    layer_material = getattr(layer, "Material", None)
                    if layer_material:
                        names.append(safe_string(getattr(layer_material, "Name", "")))
    except Exception:
        return ""
    return " ".join(name for name in names if name)


def get_predefined_type(entity):
    value = getattr(entity, "PredefinedType", None)
    if value:
        return safe_string(value)
    return ""


def element_label(element):
    return f"{element.name} ({element.ifc_type} {element.ifc_id})"


def build_settings(ifcopenshell):
    settings = ifcopenshell.geom.settings()
    for option, value in (("use-world-coords", True), ("disable-opening-subtractions", False)):
        try:
            settings.set(option, value)
        except Exception:
            pass
    return settings


def bbox_from_vertices(vertices):
    xs = vertices[0::3]
    ys = vertices[1::3]
    zs = vertices[2::3]
    bbox_min = (min(xs), min(ys), min(zs))
    bbox_max = (max(xs), max(ys), max(zs))
    center = tuple((bbox_min[index] + bbox_max[index]) / 2 for index in range(3))
    dimensions = tuple(max(bbox_max[index] - bbox_min[index], 0) for index in range(3))
    volume = dimensions[0] * dimensions[1] * dimensions[2]
    return bbox_min, bbox_max, center, volume


def create_element_geometry(settings, product):
    try:
        shape = get_ifcopenshell().geom.create_shape(settings, product)
        vertices = list(shape.geometry.verts)
    except Exception:
        return None

    if len(vertices) < 6:
        return None

    bbox_min, bbox_max, center, volume = bbox_from_vertices(vertices)
    if volume <= 0:
        return None

    entity_id = product.id()
    entity_type = product.is_a()
    name = safe_string(getattr(product, "Name", "")) or safe_string(getattr(product, "ObjectType", "")) or f"{entity_type} #{entity_id}"

    return ElementGeometry(
        entity=product,
        global_id=safe_string(getattr(product, "GlobalId", "")),
        ifc_id=f"#{entity_id}",
        ifc_type=entity_type,
        name=name[:90],
        bbox_min=bbox_min,
        bbox_max=bbox_max,
        center=center,
        volume=volume,
        container=get_container_name(product),
        material=get_material_name(product),
        predefined_type=get_predefined_type(product),
    )


def load_geometry(file_path):
    ifcopenshell = get_ifcopenshell()
    model = ifcopenshell.open(str(file_path))
    settings = build_settings(ifcopenshell)
    elements = []

    for product in model.by_type("IfcProduct"):
        if len(elements) >= MAX_ELEMENTS:
            break
        if not getattr(product, "Representation", None):
            continue
        if product.is_a("IfcOpeningElement") or product.is_a("IfcSpace") or product.is_a("IfcAnnotation"):
            continue
        geometry = create_element_geometry(settings, product)
        if geometry:
            elements.append(geometry)

    return elements


def axis_overlap(a_min, a_max, b_min, b_max):
    return min(a_max, b_max) - max(a_min, b_min)


def bbox_overlap(element_a, element_b):
    overlaps = tuple(
        axis_overlap(element_a.bbox_min[index], element_a.bbox_max[index], element_b.bbox_min[index], element_b.bbox_max[index])
        for index in range(3)
    )
    if any(overlap <= MIN_OVERLAP_TOLERANCE for overlap in overlaps):
        return None
    volume = overlaps[0] * overlaps[1] * overlaps[2]
    return overlaps, volume


def distance_between_centers(element_a, element_b):
    return sum((element_a.center[index] - element_b.center[index]) ** 2 for index in range(3)) ** 0.5


def likely_named_support(element):
    text = normalize_words(element.name, element.ifc_type, element.predefined_type, element.material)
    return any(word in text for word in ("support", "hanger", "bracket", "clamp", "saddle", "strut", "unistrut", "clip", "anchor"))


def is_pipe_support_pair(element_a, element_b):
    pair_types = {element_a.ifc_type, element_b.ifc_type}
    if not (pair_types & PIPE_TYPES):
        return False
    support = element_b if element_a.ifc_type in PIPE_TYPES else element_a
    return support.ifc_type in SUPPORT_TYPES or likely_named_support(support)


def is_cable_tray_support_pair(element_a, element_b):
    pair_types = {element_a.ifc_type, element_b.ifc_type}
    if not (pair_types & CABLE_TRAY_TYPES):
        return False
    support = element_b if element_a.ifc_type in CABLE_TRAY_TYPES else element_a
    support_text = normalize_words(support.name, support.ifc_type, support.predefined_type)
    return support.ifc_type in SUPPORT_TYPES or likely_named_support(support) or "tray support" in support_text


def is_rebar_in_concrete_pair(element_a, element_b):
    pair_types = {element_a.ifc_type, element_b.ifc_type}
    if not (pair_types & REBAR_TYPES):
        return False
    host = element_b if element_a.ifc_type in REBAR_TYPES else element_a
    host_text = normalize_words(host.name, host.ifc_type, host.material, host.predefined_type)
    return host.ifc_type in STRUCTURAL_TYPES and any(word in host_text for word in ("concrete", "rc", "reinforced", "cast", "slab", "wall", "beam", "column"))


def is_door_window_opening_in_wall_pair(element_a, element_b):
    pair_types = {element_a.ifc_type, element_b.ifc_type}
    if not (pair_types & OPENING_TYPES):
        return False
    if not ({"IfcWall", "IfcWallStandardCase"} & pair_types):
        return False
    opening = element_b if element_a.ifc_type in {"IfcWall", "IfcWallStandardCase"} else element_a
    opening_text = normalize_words(opening.name, opening.ifc_type, opening.predefined_type)
    return any(word in opening_text for word in ("door", "window", "opening", "void", "rough opening"))


def is_structural_joint_pair(element_a, element_b, overlap_volume):
    if element_a.ifc_type not in STRUCTURAL_JOINT_TYPES or element_b.ifc_type not in STRUCTURAL_JOINT_TYPES:
        return False
    same_level = element_a.container and element_a.container == element_b.container
    smaller = max(min(element_a.volume, element_b.volume), 0.000001)
    overlap_ratio = overlap_volume / smaller
    joint_words = normalize_words(element_a.name, element_b.name, element_a.predefined_type, element_b.predefined_type)
    return same_level and (overlap_ratio < 0.08 or any(word in joint_words for word in ("connection", "joint", "bearing", "embed", "plate")))


def ignore_reason(element_a, element_b, overlap_volume):
    if is_structural_joint_pair(element_a, element_b, overlap_volume):
        return "Ignored structural joint"
    if is_pipe_support_pair(element_a, element_b):
        return "Ignored pipe support"
    if is_rebar_in_concrete_pair(element_a, element_b):
        return "Ignored rebar embedded in concrete"
    if is_door_window_opening_in_wall_pair(element_a, element_b):
        return "Ignored wall door/window opening"
    if is_cable_tray_support_pair(element_a, element_b):
        return "Ignored cable tray support"
    return ""


def classify_clash(element_a, element_b, overlap_volume):
    pair_types = {element_a.ifc_type, element_b.ifc_type}
    smaller = max(min(element_a.volume, element_b.volume), 0.000001)
    overlap_ratio = overlap_volume / smaller

    if pair_types & MEP_TYPES and pair_types & STRUCTURAL_TYPES:
        return "Critical"
    if overlap_ratio > 0.18:
        return "Critical"
    if overlap_ratio > 0.04:
        return "Warning"
    return "Info"


def format_location(element_a, element_b):
    center = tuple((element_a.center[index] + element_b.center[index]) / 2 for index in range(3))
    level = element_a.container or element_b.container or "Model coordinates"
    return f"{level} · X{center[0]:.2f} Y{center[1]:.2f} Z{center[2]:.2f}"


def describe_clash(element_a, element_b, overlap_axes, overlap_volume):
    overlap_mm = min(overlap_axes) * 1000
    return (
        f"Geometry overlap detected between {element_a.ifc_type} and {element_b.ifc_type}; "
        f"minimum overlap depth is {overlap_mm:.0f} mm with intersecting bounding volume {overlap_volume:.3f} m³."
    )


def describe_ignored_clash(element_a, element_b, overlap_axes, overlap_volume):
    overlap_mm = min(overlap_axes) * 1000
    return (
        f"Intentional or expected geometry relationship between {element_a.ifc_type} and {element_b.ifc_type}; "
        f"overlap depth is {overlap_mm:.0f} mm with intersecting bounding volume {overlap_volume:.3f} m³."
    )


def sort_pair_priority(pair):
    element_a, element_b, overlap_axes, overlap_volume = pair
    severity_rank = {"Critical": 0, "Warning": 1, "Info": 2}
    return (
        severity_rank[classify_clash(element_a, element_b, overlap_volume)],
        -overlap_volume,
        distance_between_centers(element_a, element_b),
    )


def sort_ignored_priority(pair):
    element_a, element_b, overlap_axes, overlap_volume, reason = pair
    return (reason, -overlap_volume, distance_between_centers(element_a, element_b))


def detect_clashes(file_path):
    elements = load_geometry(file_path)
    candidate_pairs = []
    ignored_pairs = []

    for element_a, element_b in combinations(elements, 2):
        overlap = bbox_overlap(element_a, element_b)
        if not overlap:
            continue

        overlap_axes, overlap_volume = overlap
        reason = ignore_reason(element_a, element_b, overlap_volume)
        if reason:
            ignored_pairs.append((element_a, element_b, overlap_axes, overlap_volume, reason))
            continue

        candidate_pairs.append((element_a, element_b, overlap_axes, overlap_volume))

    candidate_pairs.sort(key=sort_pair_priority)
    ignored_pairs.sort(key=sort_ignored_priority)
    clashes = []
    ignored_clashes = []

    for index, (element_a, element_b, overlap_axes, overlap_volume) in enumerate(candidate_pairs[:MAX_CLASHES], start=1):
        clashes.append(
            {
                "id": f"CL-{index:04d}",
                "severity": classify_clash(element_a, element_b, overlap_volume),
                "description": describe_clash(element_a, element_b, overlap_axes, overlap_volume),
                "location": format_location(element_a, element_b),
                "elementA": element_label(element_a),
                "elementB": element_label(element_b),
            }
        )

    for index, (element_a, element_b, overlap_axes, overlap_volume, reason) in enumerate(ignored_pairs[:MAX_IGNORED_CLASHES], start=1):
        ignored_clashes.append(
            {
                "id": f"IG-{index:04d}",
                "reason": reason,
                "description": describe_ignored_clash(element_a, element_b, overlap_axes, overlap_volume),
                "location": format_location(element_a, element_b),
                "elementA": element_label(element_a),
                "elementB": element_label(element_b),
            }
        )

    return {"clashes": clashes, "ignoredClashes": ignored_clashes}


def summarize_clashes(clashes):
    summary = {"Critical": 0, "Warning": 0, "Info": 0}

    for clash in clashes:
        severity = clash.get("severity", "Info")
        summary[severity] = summary.get(severity, 0) + 1

    return summary
