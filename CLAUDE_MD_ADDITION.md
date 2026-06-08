## Memory and Session Context

This project may include a local memory layer to help preserve project context across development sessions.

When available, Claude may use memory tools to:

- Understand the current demo project state
- Summarize completed work
- Track high-level technical decisions
- Record session outcomes
- Support continuity between development sessions

Memory should be treated as local project context only.

Do not expose private memory content, personal notes, local file paths, internal planning details, function names, or sensitive configuration in public-facing responses or documentation.
