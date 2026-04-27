# domain-skills

One folder per domain. Each captures a real data source (ADEM eFile, TESS FITS,
FAERS quarterly dumps, USAspending awards, etc.) and validates a canonical
extraction via predicate-first fixtures.

Spec §10's diversity rubric defines the v0 set: ADEM, TESS, FAERS, USAspending,
ZTF, Vesuvius, GFW, USPTO, EDGAR, SoccerNet, DHS, Snapshot Serengeti.

Copy `_template/` to start a new domain. `dh check-skill <skill>` is the gate.
