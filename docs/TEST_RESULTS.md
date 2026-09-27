# v0.4.2 test results

Local QA completed before packaging:

- Python compile: PASS
- unit/integration tests: 19/19 PASS
- built-in sabotage acceptance suite: PASS
- repository validation: PASS
- canonical agent protocol manifest generation: PASS
- assembled role prompt generation: PASS
- agent-run provenance record generation: PASS
- verification packet includes agent protocol artifacts: PASS
- workflow YAML parse: PASS
- ruleset JSON parse: PASS
- shell syntax: PASS
- HUMAN_MANUAL.tex compilation: PASS (15 rendered pages)
- PDF visual QA of the new agent-protocol section: PASS

The local runtime used for this packaging pass does not provide the target project's Lean toolchain; Lean-only acceptance remains a GitHub/local-project test as documented in FIRST_RUN.md. Earlier v0.4 acceptance on the user's environment confirmed Lean 4.34.1 build, fresh axiom traversal, and exact dependency extraction.
