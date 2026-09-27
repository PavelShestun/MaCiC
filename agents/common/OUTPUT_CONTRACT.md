# Common output contract

Every agent output must identify:
- hypothesis ID;
- role;
- repository commit or working-tree state if known;
- frozen statement hash if available;
- input artifacts examined;
- actions performed;
- findings;
- unresolved risks;
- proposed next action.

Do not emit a human approval. The strongest allowed conclusion is role-specific and defined in that role's schema.

For structured outputs, conform to the role's `OUTPUT_SCHEMA.yaml`. Narrative explanation may accompany the structured record, but must not contradict it.
