# Towards Verifiably Safe Tool Use for LLM Agents

Published record: [DOI 10.1145/3786582.3786839](https://doi.org/10.1145/3786582.3786839), ICSE-NIER 2026, pp. 201-205. Crossref confirms the title, authors, venue, and pages. The ACM page returned HTTP 403 in this review pass; no local full text or hash is stored. Detailed method claims below must be checked against the published PDF before final submission.

The project’s earlier review notes describe a pipeline that derives safety requirements using STPA, expresses information-flow and temporal properties, attaches them to MCP tool affordances, and uses Alloy-style model checking. This is enough to treat formal safety requirements, tool-level specification, and verification as established architectural neighbors. It is not evidence that the paper trains a natural-language per-request constraint compiler.

For ConsDAG, this further narrows C2: the general idea of separating an intent/specification layer from tool execution and verifying actions is not novel. A possible empirical distinction is the trained, compact compiler’s typed per-request record and its measured interaction with a fixed planner, but the current synthetic semantic labels and incomplete public-input E2 do not yet establish that distinction as a useful contribution.
