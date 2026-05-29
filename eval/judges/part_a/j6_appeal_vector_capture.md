# J6 Appeal-Vector Capture

This is the teacher-only judge. Score only whether the appeal found and used
the flaw embedded by the synthetic-case generator.

Use the teacher packet fields:

- `matrix_cell.sub_tactic`
- `denial_pattern_sources`
- `expected_appeal_vectors`
- `exploitable_weaknesses`
- `strong_defenses`
- timestamps
- plan funding type

5: The appeal directly attacks at least one expected appeal vector and does so
with facts from this case. Examples: uses a 1-5 minute denial timestamp to
argue lack of meaningful review; requests reviewer credentials when credentials
are missing; invokes plan funding type when state-law mandate logic matters;
points out ignored prior treatment when step therapy was wrongly demanded.

3: The appeal addresses the general denial category but only partially or
implicitly reaches the embedded flaw.

1: The appeal misses the embedded flaw, rebuts a different issue, or writes a
generic medical-record appeal.

Quote appeal evidence and teacher-packet evidence first. Output score 1, 3, or
5 as JSON.
