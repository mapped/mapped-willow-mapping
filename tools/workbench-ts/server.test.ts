import { test, expect, describe, beforeEach } from "bun:test";
import { mkdtempSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";
import {
  loadDoc,
  saveDoc,
  addMapping,
  updateMapping,
  deleteMapping,
  hierarchyDistance,
  computeRoundTrips,
  type Remap,
} from "./server";

// --- Helpers ---
function tmpMappingFile(remaps: Remap[]): string {
  const dir = mkdtempSync(join(tmpdir(), "workbench-test-"));
  const path = join(dir, "mapping.json");
  writeFileSync(path, JSON.stringify({ Header: {}, InterfaceRemaps: remaps }, null, 2));
  return path;
}

const BASE_REMAPS: Remap[] = [
  { InputDtmi: "dtmi:a;1", OutputDtmi: "dtmi:x;1" },
  { InputDtmi: "dtmi:b;1", OutputDtmi: "dtmi:y;1" },
  { InputDtmi: "dtmi:c;1", OutputDtmi: "dtmi:z;1" },
];

// --- addMapping ---
describe("addMapping", () => {
  let file: string;
  beforeEach(() => { file = tmpMappingFile([...BASE_REMAPS]); });

  test("preserves all existing mappings", () => {
    addMapping(file, "dtmi:d;1", "dtmi:w;1");
    const doc = loadDoc(file);
    expect(doc.InterfaceRemaps).toHaveLength(4);
    expect(doc.InterfaceRemaps.find(r => r.InputDtmi === "dtmi:a;1")).toBeTruthy();
    expect(doc.InterfaceRemaps.find(r => r.InputDtmi === "dtmi:b;1")).toBeTruthy();
    expect(doc.InterfaceRemaps.find(r => r.InputDtmi === "dtmi:c;1")).toBeTruthy();
  });

  test("adds the new mapping", () => {
    addMapping(file, "dtmi:d;1", "dtmi:w;1");
    const doc = loadDoc(file);
    expect(doc.InterfaceRemaps.find(r => r.InputDtmi === "dtmi:d;1")?.OutputDtmi).toBe("dtmi:w;1");
  });

  test("throws if inputDtmi already exists", () => {
    expect(() => addMapping(file, "dtmi:a;1", "dtmi:new;1")).toThrow();
  });

  test("file unchanged after duplicate attempt", () => {
    try { addMapping(file, "dtmi:a;1", "dtmi:new;1"); } catch {}
    const doc = loadDoc(file);
    expect(doc.InterfaceRemaps).toHaveLength(3);
    expect(doc.InterfaceRemaps.find(r => r.InputDtmi === "dtmi:a;1")?.OutputDtmi).toBe("dtmi:x;1");
  });
});

// --- updateMapping ---
describe("updateMapping", () => {
  let file: string;
  beforeEach(() => { file = tmpMappingFile([...BASE_REMAPS]); });

  test("changes only the target entry's OutputDtmi", () => {
    updateMapping(file, "dtmi:b;1", "dtmi:updated;1");
    const doc = loadDoc(file);
    expect(doc.InterfaceRemaps.find(r => r.InputDtmi === "dtmi:b;1")?.OutputDtmi).toBe("dtmi:updated;1");
  });

  test("leaves other entries unchanged", () => {
    updateMapping(file, "dtmi:b;1", "dtmi:updated;1");
    const doc = loadDoc(file);
    expect(doc.InterfaceRemaps).toHaveLength(3);
    expect(doc.InterfaceRemaps.find(r => r.InputDtmi === "dtmi:a;1")?.OutputDtmi).toBe("dtmi:x;1");
    expect(doc.InterfaceRemaps.find(r => r.InputDtmi === "dtmi:c;1")?.OutputDtmi).toBe("dtmi:z;1");
  });

  test("throws if inputDtmi not found", () => {
    expect(() => updateMapping(file, "dtmi:nope;1", "dtmi:x;1")).toThrow();
  });

  test("file unchanged after failed update", () => {
    try { updateMapping(file, "dtmi:nope;1", "dtmi:x;1"); } catch {}
    const doc = loadDoc(file);
    expect(doc.InterfaceRemaps).toHaveLength(3);
  });
});

// --- deleteMapping ---
describe("deleteMapping", () => {
  let file: string;
  beforeEach(() => { file = tmpMappingFile([...BASE_REMAPS]); });

  test("removes exactly one mapping", () => {
    deleteMapping(file, "dtmi:b;1");
    const doc = loadDoc(file);
    expect(doc.InterfaceRemaps).toHaveLength(2);
    expect(doc.InterfaceRemaps.find(r => r.InputDtmi === "dtmi:b;1")).toBeUndefined();
  });

  test("leaves other entries intact", () => {
    deleteMapping(file, "dtmi:b;1");
    const doc = loadDoc(file);
    expect(doc.InterfaceRemaps.find(r => r.InputDtmi === "dtmi:a;1")).toBeTruthy();
    expect(doc.InterfaceRemaps.find(r => r.InputDtmi === "dtmi:c;1")).toBeTruthy();
  });

  test("throws if inputDtmi not found", () => {
    expect(() => deleteMapping(file, "dtmi:nope;1")).toThrow();
  });

  test("file unchanged after failed delete", () => {
    try { deleteMapping(file, "dtmi:nope;1"); } catch {}
    const doc = loadDoc(file);
    expect(doc.InterfaceRemaps).toHaveLength(3);
  });
});

// --- saveDoc ---
describe("saveDoc", () => {
  test("sorts InterfaceRemaps by InputDtmi", () => {
    const file = tmpMappingFile([
      { InputDtmi: "dtmi:z;1", OutputDtmi: "dtmi:1;1" },
      { InputDtmi: "dtmi:a;1", OutputDtmi: "dtmi:2;1" },
      { InputDtmi: "dtmi:m;1", OutputDtmi: "dtmi:3;1" },
    ]);
    const doc = loadDoc(file);
    saveDoc(file, doc);
    const saved = loadDoc(file);
    expect(saved.InterfaceRemaps[0].InputDtmi).toBe("dtmi:a;1");
    expect(saved.InterfaceRemaps[1].InputDtmi).toBe("dtmi:m;1");
    expect(saved.InterfaceRemaps[2].InputDtmi).toBe("dtmi:z;1");
  });

  test("preserves extra top-level fields", () => {
    const file = tmpMappingFile([]);
    const doc = loadDoc(file);
    (doc as Record<string, unknown>).CustomField = "preserved";
    saveDoc(file, doc);
    const saved = loadDoc(file) as Record<string, unknown>;
    expect(saved.CustomField).toBe("preserved");
  });
});

// --- hierarchyDistance ---
describe("hierarchyDistance", () => {
  const parents = new Map([
    ["dtmi:child;1", ["dtmi:parent;1"]],
    ["dtmi:parent;1", ["dtmi:grandparent;1"]],
    ["dtmi:grandparent;1", []],
    ["dtmi:other;1", ["dtmi:grandparent;1"]],
  ]);

  test("same node = 0", () => {
    expect(hierarchyDistance("dtmi:child;1", "dtmi:child;1", parents)).toBe(0);
  });

  test("direct parent = 1", () => {
    expect(hierarchyDistance("dtmi:child;1", "dtmi:parent;1", parents)).toBe(1);
  });

  test("grandparent = 2", () => {
    expect(hierarchyDistance("dtmi:child;1", "dtmi:grandparent;1", parents)).toBe(2);
  });

  test("unrelated = null", () => {
    expect(hierarchyDistance("dtmi:child;1", "dtmi:other;1", parents)).toBeNull();
  });

  test("unknown node = null", () => {
    expect(hierarchyDistance("dtmi:unknown;1", "dtmi:parent;1", parents)).toBeNull();
  });
});

// --- computeRoundTrips ---
describe("computeRoundTrips", () => {
  const parents = new Map([
    ["dtmi:mapped:specific;1", ["dtmi:mapped:general;1"]],
    ["dtmi:mapped:general;1", []],
  ]);

  test("lossless round trip = granularityLoss 0", () => {
    const m2w: Remap[] = [{ InputDtmi: "dtmi:mapped:specific;1", OutputDtmi: "dtmi:willow:x;1" }];
    const w2m: Remap[] = [{ InputDtmi: "dtmi:willow:x;1", OutputDtmi: "dtmi:mapped:specific;1" }];
    const [trip] = computeRoundTrips(m2w, w2m, parents);
    expect(trip.granularityLoss).toBe(0);
    expect(trip.unmappedReturn).toBe(false);
    expect(trip.returnDtmi).toBe("dtmi:mapped:specific;1");
  });

  test("granularity loss = hops to ancestor", () => {
    const m2w: Remap[] = [{ InputDtmi: "dtmi:mapped:specific;1", OutputDtmi: "dtmi:willow:x;1" }];
    const w2m: Remap[] = [{ InputDtmi: "dtmi:willow:x;1", OutputDtmi: "dtmi:mapped:general;1" }];
    const [trip] = computeRoundTrips(m2w, w2m, parents);
    expect(trip.granularityLoss).toBe(1);
    expect(trip.returnDtmi).toBe("dtmi:mapped:general;1");
  });

  test("unmapped return when willow DTMI has no W2M entry", () => {
    const m2w: Remap[] = [{ InputDtmi: "dtmi:mapped:specific;1", OutputDtmi: "dtmi:willow:x;1" }];
    const [trip] = computeRoundTrips(m2w, [], parents);
    expect(trip.unmappedReturn).toBe(true);
    expect(trip.returnDtmi).toBeNull();
    expect(trip.granularityLoss).toBeNull();
  });

  test("unrelated classes = null granularityLoss", () => {
    const m2w: Remap[] = [{ InputDtmi: "dtmi:mapped:specific;1", OutputDtmi: "dtmi:willow:x;1" }];
    const w2m: Remap[] = [{ InputDtmi: "dtmi:willow:x;1", OutputDtmi: "dtmi:mapped:unrelated;1" }];
    const [trip] = computeRoundTrips(m2w, w2m, parents);
    expect(trip.granularityLoss).toBeNull();
  });
});
