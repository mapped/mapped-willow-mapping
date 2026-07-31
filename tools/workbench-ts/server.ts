import { readFileSync, writeFileSync } from "node:fs";
import { join, resolve } from "node:path";

// --- Types ---
export type Remap = { InputDtmi: string; OutputDtmi: string; [k: string]: unknown };
export type MappingDoc = { InterfaceRemaps: Remap[]; [k: string]: unknown };
export type RoundTrip = {
  inputDtmi: string;
  midDtmi: string;   // the mapped-to DTMI (willow when dir=m2w, mapped when dir=w2m)
  returnDtmi: string | null;
  granularityLoss: number | null; // 0 = lossless, >0 = hops to ancestor, null = unrelated
  unmappedReturn: boolean; // midDtmi has no reverse entry — top priority
};

// --- Paths ---
const REPO_ROOT = resolve(import.meta.dir, "../..");
export const M2W_PATH = join(
  REPO_ROOT,
  "Ontologies.Mappings/src/Mappings/v1/Willow/Mapped2Willow.json"
);
export const W2M_PATH = join(
  REPO_ROOT,
  "Ontologies.Mappings/src/Mappings/v1/Mapped/Willow2Mapped.json"
);
const MAPPED_ONT = join(REPO_ROOT, "data/ontologies/mapped.json");
const WILLOW_ONT = join(REPO_ROOT, "data/ontologies/willow.jsonld");

// --- Mapping I/O ---
export function loadDoc(path: string): MappingDoc {
  return JSON.parse(readFileSync(path, "utf8"));
}

export function saveDoc(path: string, doc: MappingDoc): void {
  const sorted = [...doc.InterfaceRemaps].sort((a, b) =>
    a.InputDtmi.localeCompare(b.InputDtmi)
  );
  writeFileSync(path, JSON.stringify({ ...doc, InterfaceRemaps: sorted }, null, 2) + "\n", "utf8");
}

// --- Ontology hierarchy ---
function loadParents(path: string): Map<string, string[]> {
  const ifaces: Array<{ "@id": string; extends?: string | string[] }> = JSON.parse(
    readFileSync(path, "utf8")
  );
  const out = new Map<string, string[]>();
  for (const iface of ifaces) {
    const id = iface["@id"];
    const ext = iface.extends ?? [];
    out.set(id, Array.isArray(ext) ? ext : [ext]);
  }
  return out;
}

export function buildParentMap(): Map<string, string[]> {
  const map = new Map<string, string[]>();
  for (const path of [MAPPED_ONT, WILLOW_ONT]) {
    try {
      for (const [id, parents] of loadParents(path)) map.set(id, parents);
    } catch {
      // ontology cache missing — hierarchy distances will be null
    }
  }
  return map;
}

// BFS up the hierarchy: how many hops from `from` to reach `to`?
export function hierarchyDistance(
  from: string,
  to: string,
  parents: Map<string, string[]>
): number | null {
  if (from === to) return 0;
  const visited = new Set<string>();
  const queue: Array<{ id: string; depth: number }> = [{ id: from, depth: 0 }];
  while (queue.length) {
    const { id, depth } = queue.shift()!;
    if (visited.has(id)) continue;
    visited.add(id);
    for (const p of parents.get(id) ?? []) {
      if (p === to) return depth + 1;
      queue.push({ id: p, depth: depth + 1 });
    }
  }
  return null;
}

// --- Round-trip analysis ---
// primary: mappings to iterate; secondary: lookup for the return leg
export function computeRoundTrips(
  primary: Remap[],
  secondary: Remap[],
  parents: Map<string, string[]>
): RoundTrip[] {
  const secondaryIndex = new Map(secondary.map((r) => [r.InputDtmi, r.OutputDtmi]));
  return primary.map((r) => {
    const returnDtmi = secondaryIndex.get(r.OutputDtmi) ?? null;
    const unmappedReturn = returnDtmi === null;
    const granularityLoss = returnDtmi === null
      ? null
      : hierarchyDistance(r.InputDtmi, returnDtmi, parents);
    return {
      inputDtmi: r.InputDtmi,
      midDtmi: r.OutputDtmi,
      returnDtmi,
      granularityLoss,
      unmappedReturn,
    };
  });
}

// --- Single-mutation operations (one entry changed per call) ---
export function addMapping(path: string, inputDtmi: string, outputDtmi: string): void {
  const doc = loadDoc(path);
  if (doc.InterfaceRemaps.some((r) => r.InputDtmi === inputDtmi)) {
    throw new Error(`Mapping already exists for ${inputDtmi}`);
  }
  doc.InterfaceRemaps.push({ InputDtmi: inputDtmi, OutputDtmi: outputDtmi });
  saveDoc(path, doc);
}

export function updateMapping(path: string, inputDtmi: string, newOutputDtmi: string): void {
  const doc = loadDoc(path);
  const entry = doc.InterfaceRemaps.find((r) => r.InputDtmi === inputDtmi);
  if (!entry) throw new Error(`Mapping not found for ${inputDtmi}`);
  entry.OutputDtmi = newOutputDtmi;
  saveDoc(path, doc);
}

export function deleteMapping(path: string, inputDtmi: string): void {
  const doc = loadDoc(path);
  const before = doc.InterfaceRemaps.length;
  doc.InterfaceRemaps = doc.InterfaceRemaps.filter((r) => r.InputDtmi !== inputDtmi);
  if (doc.InterfaceRemaps.length === before) {
    throw new Error(`Mapping not found for ${inputDtmi}`);
  }
  saveDoc(path, doc);
}

// --- HTTP server ---
if (import.meta.main) {
  const PORT = Number(process.env.PORT ?? 3000);
  const indexHtml = readFileSync(join(import.meta.dir, "index.html"), "utf8");

  Bun.serve({
    port: PORT,
    async fetch(req) {
      const { method } = req;
      const url = new URL(req.url);
      const path = url.pathname;

      if (path === "/" || path === "/index.html") {
        return new Response(indexHtml, { headers: { "Content-Type": "text/html" } });
      }

      // GET /api/roundtrips?dir=m2w|w2m
      if (method === "GET" && path === "/api/roundtrips") {
        const dir = url.searchParams.get("dir") ?? "m2w";
        const m2w = loadDoc(M2W_PATH).InterfaceRemaps;
        const w2m = loadDoc(W2M_PATH).InterfaceRemaps;
        const parents = buildParentMap();
        const [primary, secondary] = dir === "w2m" ? [w2m, m2w] : [m2w, w2m];
        const trips = computeRoundTrips(primary, secondary, parents);
        trips.sort((a, b) => {
          if (a.unmappedReturn !== b.unmappedReturn) return a.unmappedReturn ? -1 : 1;
          return (b.granularityLoss ?? 0) - (a.granularityLoss ?? 0);
        });
        return json(trips);
      }

      // GET /api/ontology — id + parents for both ontologies
      if (method === "GET" && path === "/api/ontology") {
        const out: Array<{ id: string; parents: string[] }> = [];
        for (const ontPath of [MAPPED_ONT, WILLOW_ONT]) {
          try {
            for (const [id, parents] of loadParents(ontPath))
              out.push({ id, parents });
          } catch {}
        }
        return json(out);
      }

      // GET /api/unmapped/m2w  or  /api/unmapped/w2m
      const unmappedMatch = path.match(/^\/api\/unmapped\/(m2w|w2m)$/);
      if (method === "GET" && unmappedMatch) {
        const dir = unmappedMatch[1];
        // m2w: candidates = mapped ontology ∪ W2M.OutputDtmi; primary = M2W
        // w2m: candidates = willow ontology ∪ M2W.OutputDtmi; primary = W2M
        const [ontPath, primaryPath, reversePath] = dir === "m2w"
          ? [MAPPED_ONT, M2W_PATH, W2M_PATH]
          : [WILLOW_ONT, W2M_PATH, M2W_PATH];
        try {
          const ifaces: Array<{ "@id": string }> = JSON.parse(readFileSync(ontPath, "utf8"));
          const candidates = new Set(ifaces.map(i => i["@id"]));
          for (const r of loadDoc(reversePath).InterfaceRemaps) candidates.add(r.OutputDtmi);
          const mapped = new Set(loadDoc(primaryPath).InterfaceRemaps.map(r => r.InputDtmi));
          return json([...candidates].filter(id => !mapped.has(id)).sort());
        } catch {
          return json([]);
        }
      }

      // GET /api/mappings/m2w  or  /api/mappings/w2m
      const mappingsMatch = path.match(/^\/api\/mappings\/(m2w|w2m)$/);
      if (method === "GET" && mappingsMatch) {
        const p = mappingsMatch[1] === "m2w" ? M2W_PATH : W2M_PATH;
        return json(loadDoc(p).InterfaceRemaps);
      }

      // POST/PUT/DELETE /api/mapping/m2w  or  /api/mapping/w2m
      const mutateMatch = path.match(/^\/api\/mapping\/(m2w|w2m)$/);
      if (mutateMatch) {
        const p = mutateMatch[1] === "m2w" ? M2W_PATH : W2M_PATH;
        let body: Record<string, string>;
        try {
          body = await req.json();
        } catch {
          return jsonErr("invalid JSON body");
        }
        const { inputDtmi, outputDtmi } = body;

        try {
          if (method === "POST") {
            if (!inputDtmi || !outputDtmi) return jsonErr("inputDtmi and outputDtmi required");
            addMapping(p, inputDtmi, outputDtmi);
          } else if (method === "PUT") {
            if (!inputDtmi || !outputDtmi) return jsonErr("inputDtmi and outputDtmi required");
            updateMapping(p, inputDtmi, outputDtmi);
          } else if (method === "DELETE") {
            if (!inputDtmi) return jsonErr("inputDtmi required");
            deleteMapping(p, inputDtmi);
          } else {
            return new Response("Method not allowed", { status: 405 });
          }
          return json({ ok: true });
        } catch (e) {
          return jsonErr(String(e), 400);
        }
      }

      return new Response("Not found", { status: 404 });
    },
  });

  console.log(`Workbench running at http://localhost:${PORT}`);
}

function json(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function jsonErr(msg: string, status = 400): Response {
  return json({ error: msg }, status);
}
