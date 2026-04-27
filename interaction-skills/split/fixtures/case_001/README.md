# case_001 — planted overlap leak

`train` has ids 1..10; `test` has ids 8..15. Ids 8, 9, 10 overlap — three
rows present in both partitions. The skill must detect this (`overlap_count`
≥ 1, `leak_score` > 0, `group_collisions` non-empty).

Future: case_002 = clean random split; case_003 = group-leak (different ids
but same entity_id).
