//! leet-mcp as a library: exposes PersonalStore and consolidation primitives
//! for use by leet-cli and other in-workspace consumers.

pub mod index;
pub mod store;
// tools/protocol/server are MCP-specific and intentionally not re-exported.
