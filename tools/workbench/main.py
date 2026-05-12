import io
import json
import zipfile
from pathlib import Path
from urllib.request import urlopen

import networkx as nx

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

MAPPED_TO_WILLOW = DATA_DIR / "Mapped2Willow.json"
WILLOW_TO_MAPPED = DATA_DIR / "Willow2Mapped.json"

NUGET_FLAT = "https://api.nuget.org/v3-flatcontainer"

ONTOLOGY_PACKAGES = {
    "mapped": {
        "package": "mapped.ontologies.core.dtdl",
        "content_path": "content/mapped_dtdl.json",
        "cache": DATA_DIR / "ontologies" / "mapped.json",
    },
    "willow": {
        "package": "willowinc.ontology.dtdlv3",
        "content_path": "content/Willow.Ontology.DTDLv3.jsonld",
        "cache": DATA_DIR / "ontologies" / "willow.jsonld",
    },
}


def get_latest_version(package_id: str) -> str:
    """Get the latest version of a NuGet package."""
    url = f"{NUGET_FLAT}/{package_id}/index.json"
    with urlopen(url) as resp:
        data = json.loads(resp.read())
    return data["versions"][-1]


def download_ontology(name: str) -> list[dict]:
    """Download a NuGet package and extract the ontology JSON from it."""
    pkg = ONTOLOGY_PACKAGES[name]
    version = get_latest_version(pkg["package"])
    url = f"{NUGET_FLAT}/{pkg['package']}/{version}/{pkg['package']}.{version}.nupkg"
    print(f"Downloading {pkg['package']} v{version}...")

    with urlopen(url) as resp:
        nupkg_bytes = resp.read()

    with zipfile.ZipFile(io.BytesIO(nupkg_bytes)) as zf:
        with zf.open(pkg["content_path"]) as f:
            content = f.read()

    # Cache to disk
    pkg["cache"].parent.mkdir(parents=True, exist_ok=True)
    pkg["cache"].write_bytes(content)
    print(f"  Cached to {pkg['cache']}")

    return json.loads(content)


def load_ontology(name: str) -> list[dict]:
    """Load ontology from cache if available, otherwise download."""
    pkg = ONTOLOGY_PACKAGES[name]
    if pkg["cache"].exists():
        with open(pkg["cache"]) as f:
            return json.load(f)
    return download_ontology(name)


def load_mappings(path: Path) -> list[dict]:
    with open(path) as f:
        data = json.load(f)
    return data["InterfaceRemaps"]


def build_graph() -> nx.DiGraph:
    G = nx.DiGraph()

    for ontology_name in ["mapped", "willow"]:
        interfaces = load_ontology(ontology_name)
        for iface in interfaces:
            node_id = iface["@id"]
            display = iface.get("displayName", "")
            if isinstance(display, dict):
                display = display.get("en", "")
            G.add_node(node_id, ontology=ontology_name, display_name=display)

            for parent in iface.get("extends", []):
                G.add_edge(node_id, parent, type="subClassOf")

    for mapping_path in [MAPPED_TO_WILLOW, WILLOW_TO_MAPPED]:
        remaps = load_mappings(mapping_path)
        for remap in remaps:
            src = remap["InputDtmi"]
            dst = remap["OutputDtmi"]
            if src not in G:
                G.add_node(src, ontology="external", display_name="")
            if dst not in G:
                G.add_node(dst, ontology="external", display_name="")
            G.add_edge(src, dst, type="mapsTo")

    return G


CONSTRAINTS_FILE = DATA_DIR / "constraints.json"


def load_constraints() -> dict:
    if not CONSTRAINTS_FILE.exists():
        return {"compatible": [], "exceptions": []}
    with open(CONSTRAINTS_FILE) as f:
        return json.load(f)


def build_compatible_map(constraints: dict) -> dict[str, set[str]]:
    """Build {category_root: set of allowed target category roots}.
    Bidirectional — if A->B is listed, B->A is also allowed."""
    compat: dict[str, set[str]] = {}
    for rule in constraints.get("compatible", []):
        inp = rule["input"]
        outputs = rule["output"]
        compat.setdefault(inp, set()).update(outputs)
        for o in outputs:
            compat.setdefault(o, set()).add(inp)
    return compat


def classify_nodes(G: nx.DiGraph, compatible: dict[str, set[str]]) -> dict[str, str | None]:
    """Assign each node its category root by walking up subClassOf edges.

    Category roots are all IDs that appear in the compatible map.
    Returns {node_id: category_root_id | None}.
    """
    category_roots = set(compatible.keys())

    hierarchy = nx.DiGraph()
    for src, dst, data in G.edges(data=True):
        if data.get("type") == "subClassOf":
            hierarchy.add_edge(src, dst)

    categories: dict[str, str | None] = {}
    for nid in G.nodes():
        if nid in category_roots:
            categories[nid] = nid
            continue
        found = None
        visited = set()
        current = nid
        while current and current not in visited:
            if current in category_roots:
                found = current
                break
            visited.add(current)
            if current not in hierarchy:
                break
            parents = list(hierarchy.successors(current))
            current = parents[0] if parents else None
        categories[nid] = found

    return categories


def build_exception_set(constraints: dict) -> set[tuple[str, str]]:
    """Build a set of (source, target) instance pairs that bypass constraints."""
    pairs = set()
    for exc in constraints.get("exceptions", []):
        pairs.add((exc["input"], exc["output"]))
        pairs.add((exc["output"], exc["input"]))
    return pairs


def is_mapping_allowed(
    source: str,
    target: str,
    categories: dict[str, str | None],
    compatible: dict[str, set[str]],
    exceptions: set[tuple[str, str]],
) -> tuple[bool, str]:
    """Check if a mapping from source to target is allowed.
    Returns (allowed, reason)."""
    if (source, target) in exceptions:
        return True, "exception"

    src_cat = categories.get(source)
    tgt_cat = categories.get(target)

    # If either has no category, allow (unconstrained)
    if not src_cat or not tgt_cat:
        return True, "ok"

    allowed_targets = compatible.get(src_cat, set())
    if tgt_cat in allowed_targets:
        return True, "ok"

    return False, f"{src_cat} can only map to {allowed_targets}, not {tgt_cat}"


def graph_to_json(G: nx.DiGraph) -> dict:
    nodes = []
    for nid, data in G.nodes(data=True):
        nodes.append({
            "id": nid,
            "ontology": data.get("ontology", "unknown"),
            "display_name": data.get("display_name", ""),
        })
    edges = []
    for src, dst, data in G.edges(data=True):
        edges.append({
            "source": src,
            "target": dst,
            "type": data.get("type", "unknown"),
        })
    return {"nodes": nodes, "edges": edges}


def diagnose_gaps(G: nx.DiGraph) -> list[dict]:
    """Find roundtrip granularity losses across mappings.

    For every mapsTo edge A->B, if there's a mapsTo edge B->A',
    check if A != A' and compute the subClassOf distance.
    Positive distance = generalization (granularity lost).
    """
    # Build mapping lookup: source -> target for mapsTo edges
    maps_to: dict[str, list[str]] = {}
    for src, dst, data in G.edges(data=True):
        if data.get("type") == "mapsTo":
            maps_to.setdefault(src, []).append(dst)

    # Build subClassOf-only graph for distance computation
    hierarchy = nx.DiGraph()
    for src, dst, data in G.edges(data=True):
        if data.get("type") == "subClassOf":
            hierarchy.add_edge(src, dst)

    gaps = []
    seen = set()

    for a, b_list in maps_to.items():
        for b in b_list:
            if b not in maps_to:
                continue
            for a_prime in maps_to[b]:
                if a == a_prime:
                    continue

                pair_key = (a, b, a_prime)
                if pair_key in seen:
                    continue
                seen.add(pair_key)

                a_ont = G.nodes[a].get("ontology", "unknown")
                b_ont = G.nodes[b].get("ontology", "unknown")
                a_display = G.nodes[a].get("display_name", "")
                b_display = G.nodes[b].get("display_name", "")
                a_prime_display = G.nodes[a_prime].get("display_name", "")

                gap = {
                    "start": a,
                    "start_display": a_display,
                    "start_ontology": a_ont,
                    "mid": b,
                    "mid_display": b_display,
                    "mid_ontology": b_ont,
                    "end": a_prime,
                    "end_display": a_prime_display,
                    "distance": None,
                    "direction": None,
                    "path": [],
                }

                # Try a -> a_prime (a is more specific, generalization loss)
                if hierarchy.has_node(a) and hierarchy.has_node(a_prime):
                    try:
                        path = nx.shortest_path(hierarchy, a, a_prime)
                        gap["distance"] = len(path) - 1
                        gap["direction"] = "generalized"
                        gap["path"] = path
                    except nx.NetworkXNoPath:
                        try:
                            path = nx.shortest_path(hierarchy, a_prime, a)
                            gap["distance"] = len(path) - 1
                            gap["direction"] = "specialized"
                            gap["path"] = path
                        except nx.NetworkXNoPath:
                            gap["direction"] = "divergent"

                gaps.append(gap)

    gaps.sort(key=lambda g: (-(g["distance"] or 0), g["start"]))
    return gaps


def main():
    G = build_graph()

    node_count = G.number_of_nodes()
    edge_count = G.number_of_edges()
    subclass_edges = sum(1 for _, _, d in G.edges(data=True) if d["type"] == "subClassOf")
    maps_to_edges = sum(1 for _, _, d in G.edges(data=True) if d["type"] == "mapsTo")

    ontology_counts = {}
    for _, d in G.nodes(data=True):
        ont = d.get("ontology", "unknown")
        ontology_counts[ont] = ontology_counts.get(ont, 0) + 1

    print(f"Nodes: {node_count}")
    for ont, count in sorted(ontology_counts.items()):
        print(f"  {ont}: {count}")
    print(f"Edges: {edge_count}")
    print(f"  subClassOf: {subclass_edges}")
    print(f"  mapsTo:     {maps_to_edges}")

    print("\nRunning gap diagnosis...")
    gaps = diagnose_gaps(G)
    print(f"Found {len(gaps)} roundtrip gaps")
    for g in gaps[:10]:
        d = g['distance']
        print(f"  {g['start_display']} -> {g['mid_display']} -> {g['end_display']}  "
              f"({g['direction']}, distance={d})")


if __name__ == "__main__":
    main()
