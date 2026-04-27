# domain-skills

One folder per domain. Each captures a real data source (ADEM eFile, TESS FITS,
FAERS quarterly dumps, USAspending awards, etc.) and validates a canonical
extraction via predicate-first fixtures whose predicates encode externally-
citable facts about the target — a registered identifier, a published value,
a documented schema, a physical-law range — not just whatever the skill
happens to produce.

The 12 domains shipped today were chosen for diversity along several axes —
data volume (KB JSON to TB volumetric), modality (tabular, document, image,
3D voxel, time-series, vector embeddings), regulatory regime (FDA, SEC, USPTO,
ITU, NASA, USAID), capture mode (REST API, bulk download, web scrape, public
mirror), and analytical surface (identity validation, schema conformance,
content provenance). The set: ADEM, TESS, FAERS, USAspending, ZTF, Vesuvius,
GFW, USPTO, EDGAR, SoccerNet, DHS, Snapshot Serengeti.

Copy `_template/` to start a new domain. `dh check-skill <skill>` is the gate.
