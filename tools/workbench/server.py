import json
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse

from main import (
    build_graph, graph_to_json, diagnose_gaps, DATA_DIR,
    load_constraints, build_compatible_map, build_exception_set,
    classify_nodes, is_mapping_allowed, CONSTRAINTS_FILE,
    ONTOLOGY_PACKAGES, download_ontology,
)


def tokenize(text: str) -> list[str]:
    """Split camelCase, PascalCase, snake_case, and DTMI IDs into lowercase words."""
    # Extract the class name from DTMI: last segment before ;version
    name = text.split(":")[-1].split(";")[0]
    # Split on underscores
    parts = name.split("_")
    # Split camelCase/PascalCase within each part
    words = []
    for part in parts:
        words.extend(re.sub(r"([a-z])([A-Z])", r"\1 \2", part).split())
    return [w.lower() for w in words if w]


def build_token_graph(graph: nx.DiGraph) -> dict[str, dict[str, float]]:
    """Build a weighted token co-occurrence graph from mapsTo edges.

    For every mapsTo(classA, classB), each token in A gets an edge to each
    token in B (and vice versa). Weights are accumulated counts, so frequent
    pairings produce stronger edges.

    Returns {token: {related_token: weight}}.
    """
    from collections import defaultdict
    raw: dict[tuple[str, str], int] = defaultdict(int)
    for src, dst, data in graph.edges(data=True):
        if data.get("type") != "mapsTo":
            continue
        src_tokens = set(tokenize(src))
        dst_tokens = set(tokenize(dst))
        for s in src_tokens:
            for d in dst_tokens:
                if s != d:
                    raw[(s, d)] += 1
                    raw[(d, s)] += 1

    tg: dict[str, dict[str, float]] = {}
    for (a, b), count in raw.items():
        tg.setdefault(a, {})[b] = count
    return tg


# Global token graph — rebuilt alongside the class graph
TOKEN_GRAPH: dict[str, dict[str, float]] = {}


def rebuild_token_graph():
    global TOKEN_GRAPH
    TOKEN_GRAPH = build_token_graph(G)


def token_similarity(source_tokens: set[str], candidate_tokens: set[str]) -> float:
    """Score how well candidate_tokens match source_tokens using the token graph.

    Direct token overlap scores 1.0 per token.
    For each unmatched source token, find its single best match in the candidate
    via the token graph. Score that as weight / max_weight_for_that_token (0..1),
    so only strong relationships contribute meaningfully.
    """
    if not source_tokens or not candidate_tokens:
        return 0.0

    direct = len(source_tokens & candidate_tokens)

    # For unmatched source tokens, find the best single token-graph match
    indirect = 0.0
    unmatched_src = source_tokens - candidate_tokens
    unmatched_dst = candidate_tokens - source_tokens
    for s in unmatched_src:
        edges = TOKEN_GRAPH.get(s, {})
        if not edges:
            continue
        max_weight = max(edges.values())
        best = 0.0
        for d in unmatched_dst:
            if d in edges:
                best = max(best, edges[d] / max_weight)
        indirect += best  # 0..1 per unmatched source token

    return direct + indirect


def match_all_terms(terms: list[str], haystack: str) -> bool:
    """Check if all search terms appear in the haystack (order-independent)."""
    return all(t in haystack for t in terms)

app = FastAPI()

# Global state
G: nx.DiGraph = build_graph()
rebuild_token_graph()

_constraints = load_constraints()
COMPATIBLE = build_compatible_map(_constraints)
EXCEPTIONS = build_exception_set(_constraints)
CATEGORIES: dict[str, str | None] = classify_nodes(G, COMPATIBLE)


def reload_constraints():
    global COMPATIBLE, EXCEPTIONS, CATEGORIES
    c = load_constraints()
    COMPATIBLE = build_compatible_map(c)
    EXCEPTIONS = build_exception_set(c)
    CATEGORIES = classify_nodes(G, COMPATIBLE)


def rebuild_graph():
    global G
    G = build_graph()
    rebuild_token_graph()
    reload_constraints()


@app.get("/", response_class=HTMLResponse)
def index():
    return Path(__file__).with_name("index.html").read_text()


@app.get("/api/graph")
def get_graph():
    data = graph_to_json(G)
    return {
        "nodes": data["nodes"],
        "edges": data["edges"],
        "stats": {
            "node_count": G.number_of_nodes(),
            "edge_count": G.number_of_edges(),
            "subClassOf": sum(1 for _, _, d in G.edges(data=True) if d["type"] == "subClassOf"),
            "mapsTo": sum(1 for _, _, d in G.edges(data=True) if d["type"] == "mapsTo"),
        },
    }


@app.get("/api/search")
def search_nodes(q: str, ontology: str | None = None):
    """Return nodes matching all space-separated terms (order-independent).
    Matches against tokenized ID and display_name. Optionally filter by ontology."""
    terms = q.lower().split()
    if not terms:
        return []
    results = []
    for nid, data in G.nodes(data=True):
        if ontology and data.get("ontology") != ontology:
            continue
        display = data.get("display_name", "")
        # Build a searchable string from tokenized words
        haystack = " ".join(tokenize(nid)) + " " + display.lower()
        if match_all_terms(terms, haystack):
            results.append({
                "id": nid,
                "ontology": data.get("ontology", "unknown"),
                "display_name": display,
            })
    results.sort(key=lambda r: r["display_name"] or r["id"])
    return results[:200]


def _find_mapped_ancestor(node_id: str) -> tuple[str | None, str | None]:
    """Walk up subClassOf from *node_id* and return the first ancestor that
    has a mapsTo edge, along with its mapping target.

    Returns (ancestor_id, mapped_target_id) or (None, None).
    """
    visited = {node_id}
    current = node_id
    while True:
        parents = [
            dst for _, dst, d in G.out_edges(current, data=True)
            if d.get("type") == "subClassOf"
        ]
        if not parents:
            break
        parent = parents[0]
        if parent in visited:
            break
        visited.add(parent)
        # Check if parent has a mapsTo edge
        for _, tgt, d in G.out_edges(parent, data=True):
            if d.get("type") == "mapsTo":
                return parent, tgt
        current = parent
    return None, None


def _descendants_of(node_id: str) -> set[str]:
    """Return all descendants of *node_id* via subClassOf (including itself).

    In the graph child→parent, so descendants are transitive predecessors.
    """
    descendants = {node_id}
    queue = [node_id]
    while queue:
        n = queue.pop()
        for src, _, d in G.in_edges(n, data=True):
            if d.get("type") == "subClassOf" and src not in descendants:
                descendants.add(src)
                queue.append(src)
    return descendants


@app.get("/api/suggest-mappings/{node_id:path}")
def suggest_mappings(node_id: str):
    """Suggest top 3 mapping targets from the other ontology.

    If a parent class already has a mapping, suggestions are restricted to
    subclasses of that parent's mapping target — then ranked by token
    similarity.  Falls back to a global token-similarity search when no
    mapped ancestor exists.
    """
    if node_id not in G:
        return {"tokens": [], "suggestions": []}

    source_ont = G.nodes[node_id].get("ontology", "unknown")
    target_ont = "willow" if source_ont in ("mapped", "external") else "mapped"
    source_words = set(tokenize(node_id))

    # --- Determine candidate pool ---
    ancestor_id, ancestor_target = _find_mapped_ancestor(node_id)
    if ancestor_target:
        candidate_pool = _descendants_of(ancestor_target)
    else:
        candidate_pool = None  # unrestricted

    scored = []
    for nid, data in G.nodes(data=True):
        if data.get("ontology") != target_ont:
            continue
        # If we have a mapped ancestor, restrict to descendants of its target
        if candidate_pool is not None and nid not in candidate_pool:
            continue
        # Skip incompatible categories
        allowed, _ = is_mapping_allowed(node_id, nid, CATEGORIES, COMPATIBLE, EXCEPTIONS)
        if not allowed:
            continue
        candidate_words = set(tokenize(nid))
        sim = token_similarity(source_words, candidate_words)
        if sim <= 0:
            continue
        # Penalize size difference to prefer tighter matches
        size_diff = len(candidate_words - source_words) + len(source_words - candidate_words)
        scored.append((sim, size_diff, nid, data.get("display_name", "")))

    scored.sort(key=lambda x: (-x[0], x[1]))

    # Build token info with top related tokens from the token graph
    tokens_info = []
    for w in tokenize(node_id):
        related = TOKEN_GRAPH.get(w, {})
        # Top 3 related tokens by weight, excluding tokens already in source
        top = sorted(
            ((t, wt) for t, wt in related.items() if t not in source_words),
            key=lambda x: -x[1],
        )[:3]
        tokens_info.append({
            "word": w,
            "related": [{"token": t, "weight": round(wt, 1)} for t, wt in top],
        })

    response: dict = {
        "tokens": tokens_info,
        "suggestions": [
            {"id": nid, "ontology": target_ont, "display_name": display}
            for _, _, nid, display in scored[:3]
        ],
    }
    if ancestor_id:
        response["ancestor"] = ancestor_id
        response["ancestor_target"] = ancestor_target
    return response


@app.get("/api/neighborhood/{node_id:path}")
def get_neighborhood(node_id: str):
    """Return the 1-hop neighborhood of a node: the node itself, its neighbors, and connecting edges."""
    if node_id not in G:
        return {"nodes": [], "edges": []}

    neighbor_ids = set()
    neighbor_ids.add(node_id)
    for pred in G.predecessors(node_id):
        neighbor_ids.add(pred)
    for succ in G.successors(node_id):
        neighbor_ids.add(succ)

    nodes = []
    for nid in neighbor_ids:
        data = G.nodes[nid]
        nodes.append({
            "id": nid,
            "ontology": data.get("ontology", "unknown"),
            "display_name": data.get("display_name", ""),
        })

    edges = []
    for src, dst, data in G.edges(data=True):
        if src in neighbor_ids and dst in neighbor_ids:
            edges.append({
                "source": src,
                "target": dst,
                "type": data.get("type", "unknown"),
            })

    return {"nodes": nodes, "edges": edges, "focus": node_id}


@app.post("/api/upload/ontology")
async def upload_ontology(
    file: UploadFile = File(...),
    ontology: str = Form(...),
):
    """Upload a new version of an ontology file. ontology must be 'mapped' or 'willow'."""
    content = await file.read()
    # Validate JSON
    json.loads(content)

    if ontology not in ONTOLOGY_PACKAGES:
        return {"error": f"Unknown ontology: {ontology}"}
    dest = ONTOLOGY_PACKAGES[ontology]["cache"]

    dest.write_bytes(content)
    rebuild_graph()
    return {"status": "ok", "ontology": ontology, "nodes": G.number_of_nodes(), "edges": G.number_of_edges()}


@app.post("/api/refresh-ontologies")
async def refresh_ontologies():
    """Re-download latest ontologies from NuGet and rebuild the graph."""
    for name in ONTOLOGY_PACKAGES:
        download_ontology(name)
    rebuild_graph()
    return {
        "status": "ok",
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
    }


@app.post("/api/upload/mapping")
async def upload_mapping(
    file: UploadFile = File(...),
    direction: str = Form(...),
):
    """Upload a new version of a mapping file. direction must be 'mapped2willow' or 'willow2mapped'."""
    content = await file.read()
    data = json.loads(content)
    if "InterfaceRemaps" not in data:
        return {"error": "Missing InterfaceRemaps key"}

    if direction == "mapped2willow":
        dest = DATA_DIR / "Mapped2Willow.json"
    elif direction == "willow2mapped":
        dest = DATA_DIR / "Willow2Mapped.json"
    else:
        return {"error": f"Unknown direction: {direction}"}

    dest.write_bytes(content)
    rebuild_graph()
    return {"status": "ok", "direction": direction, "nodes": G.number_of_nodes(), "edges": G.number_of_edges()}


@app.post("/api/mapping")
async def add_mapping(request: dict):
    """Replace the mapsTo edge from source: remove any existing mapsTo from source, then add source->target."""
    source = request.get("source")
    target = request.get("target")
    if not source or not target:
        return {"error": "source and target are required"}
    if source not in G:
        return {"error": f"source node not found: {source}"}
    if target not in G:
        return {"error": f"target node not found: {target}"}

    allowed, reason = is_mapping_allowed(source, target, CATEGORIES, COMPATIBLE, EXCEPTIONS)
    if not allowed:
        return {"error": reason}

    # Remove existing mapsTo edges from source
    to_remove = [
        (s, d) for s, d, data in G.out_edges(source, data=True)
        if data.get("type") == "mapsTo"
    ]
    for s, d in to_remove:
        G.remove_edge(s, d)

    old_target = to_remove[0][1] if to_remove else None
    G.add_edge(source, target, type="mapsTo")
    rebuild_token_graph()
    persist_mappings()

    append_changelog({
        "action": "mapping_changed",
        "source": source,
        "old_target": old_target,
        "new_target": target,
    })

    return {
        "status": "ok",
        "source": source,
        "target": target,
        "removed": len(to_remove),
        "edges": G.number_of_edges(),
    }


def persist_mappings():
    """Write current mapsTo edges back to the mapping JSON files on disk."""
    from main import MAPPED_TO_WILLOW, WILLOW_TO_MAPPED

    m2w_remaps = []
    w2m_remaps = []
    for src, dst, data in G.edges(data=True):
        if data.get("type") != "mapsTo":
            continue
        src_ont = G.nodes[src].get("ontology", "")
        dst_ont = G.nodes[dst].get("ontology", "")
        if dst_ont == "willow":
            m2w_remaps.append({"InputDtmi": src, "OutputDtmi": dst})
        elif src_ont == "willow":
            w2m_remaps.append({"InputDtmi": src, "OutputDtmi": dst})

    for path, remaps in [(MAPPED_TO_WILLOW, m2w_remaps), (WILLOW_TO_MAPPED, w2m_remaps)]:
        with open(path) as f:
            doc = json.load(f)
        doc["InterfaceRemaps"] = sorted(remaps, key=lambda r: r["InputDtmi"])
        with open(path, "w") as f:
            json.dump(doc, f, indent=2)


@app.post("/api/add-exception")
async def add_exception(request: dict):
    """Add a specific class pair as an exception to constraints."""
    source = request.get("source")
    target = request.get("target")
    if not source or not target:
        return {"error": "source and target are required"}

    constraints = load_constraints()
    exceptions = constraints.get("exceptions", [])

    # Avoid duplicates
    for exc in exceptions:
        if (exc["input"] == source and exc["output"] == target) or \
           (exc["input"] == target and exc["output"] == source):
            return {"status": "already_exists"}

    exceptions.append({"input": source, "output": target})
    constraints["exceptions"] = exceptions
    with open(CONSTRAINTS_FILE, "w") as f:
        json.dump(constraints, f, indent=2)

    reload_constraints()
    return {"status": "ok"}


CHANGELOG_FILE = DATA_DIR / "changelog.json"
CHANGELOG_MD = DATA_DIR / "changelog.md"


def _short(dtmi: str) -> str:
    """Short display name for a DTMI."""
    name = dtmi.split(":")[-1].split(";")[0]
    if dtmi.startswith("dtmi:com:willowinc:"):
        return f"willow:{name}"
    if dtmi.startswith("dtmi:mapped:core:"):
        return f"mapped:{name}"
    if "brickschema" in dtmi:
        return f"brick:{name}"
    return name


def load_changelog() -> list[dict]:
    if CHANGELOG_FILE.exists():
        with open(CHANGELOG_FILE) as f:
            return json.load(f)
    return []


def append_changelog(entry: dict):
    log = load_changelog()
    entry["timestamp"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    log.append(entry)
    with open(CHANGELOG_FILE, "w") as f:
        json.dump(log, f, indent=2)
    regenerate_changelog_md(log)


def regenerate_changelog_md(log: list[dict] | None = None):
    if log is None:
        log = load_changelog()

    lines = ["# Mapping Gaps Changelog\n"]

    mappings = [e for e in log if e["action"] == "mapping_changed"]
    flags = [e for e in log if e["action"] == "gap_flagged"]

    if mappings:
        lines.append("## Mapping Changes\n")
        lines.append("| Time | Source | Old Target | New Target |")
        lines.append("|------|--------|------------|------------|")
        for e in mappings:
            t = e["timestamp"][:16].replace("T", " ")
            src = _short(e["source"])
            old = _short(e["old_target"]) if e.get("old_target") else "-"
            new = _short(e["new_target"])
            lines.append(f"| {t} | {src} | {old} | {new} |")
        lines.append("")

    if flags:
        lines.append("## Flagged Ontological Gaps\n")
        lines.append("| Time | A | B | A' |")
        lines.append("|------|---|---|-----|")
        for e in flags:
            t = e["timestamp"][:16].replace("T", " ")
            lines.append(f"| {t} | {_short(e['start'])} | {_short(e['mid'])} | {_short(e['end'])} |")
        lines.append("")

    if not mappings and not flags:
        lines.append("No changes recorded yet.\n")

    with open(CHANGELOG_MD, "w") as f:
        f.write("\n".join(lines))


FLAGGED_GAPS_FILE = DATA_DIR / "flagged_gaps.json"


def load_flagged_gaps() -> list[dict]:
    if FLAGGED_GAPS_FILE.exists():
        with open(FLAGGED_GAPS_FILE) as f:
            return json.load(f)
    return []


def save_flagged_gaps(gaps: list[dict]):
    with open(FLAGGED_GAPS_FILE, "w") as f:
        json.dump(gaps, f, indent=2)


@app.post("/api/flag-gap")
async def flag_gap(request: dict):
    """Flag a gap as an ontological gap. Persisted to flagged_gaps.json."""
    start = request.get("start")
    mid = request.get("mid")
    end = request.get("end")
    if not start or not mid or not end:
        return {"error": "start, mid, and end are required"}

    flagged = load_flagged_gaps()
    # Avoid duplicates
    for f in flagged:
        if f["start"] == start and f["mid"] == mid and f["end"] == end:
            return {"status": "already_flagged"}

    flagged.append({
        "start": start,
        "start_display": G.nodes.get(start, {}).get("display_name", ""),
        "mid": mid,
        "mid_display": G.nodes.get(mid, {}).get("display_name", ""),
        "end": end,
        "end_display": G.nodes.get(end, {}).get("display_name", ""),
    })
    save_flagged_gaps(flagged)

    append_changelog({
        "action": "gap_flagged",
        "start": start,
        "mid": mid,
        "end": end,
    })

    return {"status": "ok", "total_flagged": len(flagged)}


@app.get("/api/flagged-gaps")
def get_flagged_gaps():
    return load_flagged_gaps()


@app.get("/api/diagnose")
def diagnose():
    gaps = diagnose_gaps(G)
    flagged = load_flagged_gaps()
    flagged_keys = {(f["start"], f["mid"], f["end"]) for f in flagged}
    gaps = [g for g in gaps if (g["start"], g["mid"], g["end"]) not in flagged_keys]

    total_distance = sum(g["distance"] for g in gaps if g["distance"] is not None)

    # Find unmapped nodes
    unmapped = []
    for nid, data in G.nodes(data=True):
        ont = data.get("ontology", "unknown")
        if ont == "unknown":
            continue
        has_mapping = any(
            d.get("type") == "mapsTo" for _, _, d in G.out_edges(nid, data=True)
        )
        if not has_mapping:
            unmapped.append({
                "id": nid,
                "display_name": data.get("display_name", ""),
                "ontology": ont,
            })
    unmapped.sort(key=lambda u: u["display_name"] or u["id"])

    return {
        "total_gaps": len(gaps),
        "total_distance": total_distance,
        "gaps": gaps,
        "unmapped": unmapped,
    }


@app.get("/api/descendants/{node_id:path}")
def get_descendants(node_id: str):
    """Return all descendant IDs of a node via subClassOf (including itself)."""
    hierarchy = nx.DiGraph()
    for src, dst, data in G.edges(data=True):
        if data.get("type") == "subClassOf":
            hierarchy.add_edge(src, dst)

    if node_id not in hierarchy:
        return [node_id] if node_id in G else []

    # In our hierarchy child→parent, so descendants are predecessors transitively
    descendants = {node_id}
    queue = [node_id]
    while queue:
        n = queue.pop()
        for child in hierarchy.predecessors(n):
            if child not in descendants:
                descendants.add(child)
                queue.append(child)
    return sorted(descendants)


@app.get("/api/gap-detail")
def gap_detail(start: str, mid: str, end: str):
    """Return the two hierarchy columns and cross-edges for a gap.

    Left column: A's ancestor chain from start up to end (within one ontology).
    Right column: B (mid) and its ancestors via subClassOf.
    Cross edges: all mapsTo edges between left and right column nodes.
    """
    hierarchy = nx.DiGraph()
    maps_from: dict[str, list[str]] = {}
    for src, dst, data in G.edges(data=True):
        if data.get("type") == "subClassOf":
            hierarchy.add_edge(src, dst)
        elif data.get("type") == "mapsTo":
            maps_from.setdefault(src, []).append(dst)

    def ancestor_chain(node: str, max_depth: int = 2) -> list[str]:
        """Return [node, parent, grandparent, ...] up to max_depth ancestors."""
        chain = [node]
        current = node
        visited = {node}
        for _ in range(max_depth):
            parents = list(hierarchy.successors(current))
            if not parents:
                break
            parent = parents[0]
            if parent in visited:
                break
            visited.add(parent)
            chain.append(parent)
            current = parent
        return chain

    left_chain = ancestor_chain(start, 2)
    right_chain = ancestor_chain(mid, 2)

    # Ensure 'end' appears in the left chain if it's an ancestor of start
    # (the return mapping mid→end needs a target to draw to)
    if end not in set(left_chain) and end not in set(right_chain):
        if hierarchy.has_node(start) and hierarchy.has_node(end):
            try:
                path = nx.shortest_path(hierarchy, start, end)
                # Add end (and bridge node if needed) to left chain
                for nid in path:
                    if nid not in set(left_chain):
                        left_chain.append(nid)
            except nx.NetworkXNoPath:
                left_chain.append(end)
        else:
            left_chain.append(end)

    left_set = set(left_chain)
    right_set = set(right_chain)

    # Only the two edges that define this mapping group: start→mid and mid→end
    cross_edges = []
    if mid in maps_from.get(start, []):
        bidir = start in maps_from.get(mid, [])
        cross_edges.append({
            "source": start, "target": mid,
            "direction": "left_to_right",
            "bidirectional": bidir,
        })
    if end in maps_from.get(mid, []) and not (end == start and cross_edges and cross_edges[0].get("bidirectional")):
        bidir = mid in maps_from.get(end, [])
        cross_edges.append({
            "source": mid, "target": end,
            "direction": "right_to_left",
            "bidirectional": bidir,
        })

    def node_info(nid: str) -> dict:
        data = G.nodes.get(nid, {})
        return {
            "id": nid,
            "ontology": data.get("ontology", "unknown"),
            "display_name": data.get("display_name", "") or "",
        }

    return {
        "left": [node_info(n) for n in left_chain],
        "right": [node_info(n) for n in right_chain],
        "cross_edges": cross_edges,
        "start": start,
        "mid": mid,
        "end": end,
    }
