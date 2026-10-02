# Mapping Workbench

Interactive tool for visualizing and managing ontology mappings between Mapped and Willow.

## Usage

### Setup

```bash
cd tools/workbench
uv sync
```

### Running the server

```bash
uv run uvicorn server:app --reload
```

Open http://localhost:8000 in a browser.

### Ontology data

On first run the server loads cached ontology files from `data/ontologies/`. If the cache is missing it downloads the latest versions from NuGet automatically. Click **Refresh Ontologies** in the header to re-download.

You can also upload ontology or mapping files directly via the **Upload** button.

### Graph view

Click a node to see its 1-hop neighborhood (parents, children, and mapping targets). Use the search bar to find nodes by name — all space-separated terms must match (order-independent).

### Diagnosis

The **Diagnosis** sidebar tab lists:

- **Roundtrip gaps** — where A maps to B maps back to A' and A != A', meaning granularity is lost. Each gap shows the hierarchy distance and direction (generalized, specialized, or divergent).
- **Unmapped nodes** — classes in either ontology that have no `mapsTo` edge.

Click a gap to open the detail view showing both hierarchy chains side-by-side with cross-edges for the mapping connections.

### Mapping suggestions

Click **Suggest** on an unmapped node to get the top 3 candidate mapping targets. Suggestions are generated in two modes:

1. **Hierarchy-constrained** — if a parent class already has a mapping, candidates are restricted to subclasses of that parent's mapping target. Token similarity then ranks within that set. For example, if `TemperatureSensor` maps to `willow:TemperatureSensor`, suggestions for an unmapped `SupplyAirTemperatureSensor` will only consider subclasses of `willow:TemperatureSensor`.
2. **Global fallback** — when no mapped ancestor exists, all nodes in the target ontology are scored by token similarity (with constraint filtering).

Token similarity uses a co-occurrence graph built from existing mappings: tokens that frequently appear together across `mapsTo` edges receive higher weights, so even indirect name matches (e.g. "humidity" ↔ "moisture") can contribute.

### Applying changes

From the gap detail view you can:

- **Search** for a different mapping target manually.
- **Apply** a suggestion or search result to replace the current mapping.
- **Flag** a gap as an ontological gap (persisted to `data/flagged_gaps.json`).

All mapping changes are written back to `data/Mapped2Willow.json` and `data/Willow2Mapped.json` and recorded in `data/changelog.json`.

### Constraints

Mapping constraints in `constraints.json` define which category roots are compatible (e.g. Sensor can only map to Sensor, not to Equipment). Specific class pairs can be added as exceptions via the UI.
