use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use uuid::Uuid;

/// Scalar value clamped to [0,1].
#[derive(Debug, Clone, Copy, PartialEq, PartialOrd, Serialize, Deserialize)]
pub struct Scalar(f32);

impl Scalar {
    pub fn new(v: f32) -> Result<Self, crate::error::LeetError> {
        if !(0.0..=1.0).contains(&v) {
            return Err(crate::error::LeetError::ScalarOutOfRange(v));
        }
        Ok(Self(v))
    }

    pub fn clamp(v: f32) -> Self {
        Self(v.clamp(0.0, 1.0))
    }

    pub fn value(self) -> f32 {
        self.0
    }
}

impl From<Scalar> for f32 {
    fn from(s: Scalar) -> f32 {
        s.0
    }
}

/// Semantic vector — 32 dimensions, indexed by position (R10).
pub type SemVec = [f32; 32];

/// Raw field role (lives inside COGON only).
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum RawRole {
    Evidence,
    Artifact,
    Trace,
    Bridge,
}

/// Raw field — arbitrary content attached to a COGON.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct RawField {
    /// MIME type or enum string
    pub content_type: String,
    pub content: serde_json::Value,
    pub role: RawRole,
}

/// The semantic word — a 32-dimensional concept with uncertainty.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Cogon {
    pub id: Uuid,
    /// Semantic vector [0,1]^32 — indexed by position (R10).
    pub sem: SemVec,
    /// Uncertainty companion [0,1]^32.
    pub unc: SemVec,
    /// Unix timestamp millis.
    pub stamp: i64,
    /// Optional raw attachment.
    pub raw: Option<RawField>,
}

/// The nil UUID used for COGON_ZERO.
pub const ZERO_UUID_STR: &str = "00000000-0000-0000-0000-000000000000";

impl Cogon {
    /// Construct COGON_ZERO per spec.
    pub fn zero() -> Self {
        Self {
            id: Uuid::nil(),
            sem: [1.0_f32; 32],
            unc: [0.0_f32; 32],
            stamp: 0,
            raw: None,
        }
    }

    pub fn is_zero(&self) -> bool {
        self.id == Uuid::nil()
            && self.sem.iter().all(|&v| v == 1.0)
            && self.unc.iter().all(|&v| v == 0.0)
            && self.stamp == 0
            && self.raw.is_none()
    }

    /// Dimensions with uncertainty above 0.9 (R5 flag).
    pub fn low_confidence_dims(&self) -> Vec<(usize, f32)> {
        self.unc
            .iter()
            .enumerate()
            .filter(|(_, &u)| u > 0.9)
            .map(|(i, &u)| (i, u))
            .collect()
    }
}

/// Edge type between two COGONs.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum EdgeType {
    Causa,
    Condiciona,
    Contradiz,
    Refina,
    Emerge,
}

/// Directed edge in a DAG.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Edge {
    pub from: Uuid,
    pub to: Uuid,
    pub edge_type: EdgeType,
    /// Weight in [0,1].
    pub weight: f32,
}

/// Directed acyclic graph of COGONs — the semantic sentence.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Dag {
    pub root: Uuid,
    pub nodes: Vec<Cogon>,
    pub edges: Vec<Edge>,
    /// Cached topological order (invalidated on structural changes)
    #[serde(skip)]
    topo_cache: Option<Vec<Uuid>>,
}

impl Dag {
    /// Create a new DAG with the given root.
    pub fn new(root: Uuid) -> Self {
        Self {
            root,
            nodes: Vec::new(),
            edges: Vec::new(),
            topo_cache: None,
        }
    }

    /// Add a node to the DAG (invalidates cache).
    pub fn add_node(&mut self, cogon: Cogon) {
        self.nodes.push(cogon);
        self.topo_cache = None;
    }

    /// Add an edge to the DAG (invalidates cache).
    pub fn add_edge(&mut self, edge: Edge) {
        self.edges.push(edge);
        self.topo_cache = None;
    }

    /// Get cached topological order or compute it.
    pub fn topological_order(&mut self) -> Result<Vec<Uuid>, crate::error::LeetError> {
        if let Some(ref cache) = self.topo_cache {
            return Ok(cache.clone());
        }
        
        let order = self.compute_topological_order()?;
        self.topo_cache = Some(order.clone());
        Ok(order)
    }

    /// Compute topological order using Kahn's algorithm.
    fn compute_topological_order(&self) -> Result<Vec<Uuid>, crate::error::LeetError> {
        use std::collections::HashMap;
        
        let mut in_degree: HashMap<Uuid, usize> = 
            self.nodes.iter().map(|n| (n.id, 0)).collect();
        let mut adj: HashMap<Uuid, Vec<Uuid>> = 
            self.nodes.iter().map(|n| (n.id, Vec::new())).collect();
        
        for edge in &self.edges {
            adj.get_mut(&edge.from).unwrap().push(edge.to);
            *in_degree.get_mut(&edge.to).unwrap() += 1;
        }

        let mut queue: Vec<Uuid> = in_degree
            .iter()
            .filter(|(_, &d)| d == 0)
            .map(|(&id, _)| id)
            .collect();
        
        let mut result = Vec::new();

        while let Some(node) = queue.pop() {
            result.push(node);
            for &neighbor in &adj[&node] {
                let deg = in_degree.get_mut(&neighbor).unwrap();
                *deg -= 1;
                if *deg == 0 {
                    queue.push(neighbor);
                }
            }
        }

        if result.len() != self.nodes.len() {
            return Err(crate::error::LeetError::R4Cycle);
        }

        Ok(result)
    }
}

/// Message intent.
#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]
#[serde(rename_all = "UPPERCASE")]
pub enum Intent {
    Assert,
    Query,
    Delta,
    Sync,
    Anomaly,
    Ack,
}

/// Receiver — specific agent or broadcast.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Receiver {
    Agent(Uuid),
    Broadcast,
}

/// Emergent zone record.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmergentRecord {
    pub id: Uuid,
    pub index: usize,
    pub name: String,
    #[serde(default)]
    pub deprecated: bool,
}

/// C5 canonical space block.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct C5Block {
    /// Fixed 32-dim zone.
    pub zone_fixed: SemVec,
    /// Emergent zone: agent_id → scalar weight.
    pub zone_emergent: HashMap<Uuid, f32>,
    /// Schema version (semver string).
    pub schema_ver: String,
    /// SHA256 of shared alignment.
    pub align_hash: [u8; 32],
}

/// Surface block — human interface metadata.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct SurfaceBlock {
    pub human_required: bool,
    pub urgency: Option<f32>,
    pub reconstruct_depth: i32,
    /// ISO 639 language code.
    pub lang: String,
}

/// Payload is either a single COGON or a full DAG.
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Payload {
    Cogon(Cogon),
    Dag(Dag),
}

/// The full envelope — MSG_1337.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Msg1337 {
    pub id: Uuid,
    pub sender: Uuid,
    pub receiver: Receiver,
    pub intent: Intent,
    /// SHA256 reference hash (required for DELTA, R2).
    pub ref_hash: Option<[u8; 32]>,
    /// Semantic patch (required for DELTA, R2).
    pub patch: Option<SemVec>,
    pub payload: Payload,
    pub c5: C5Block,
    pub surface: SurfaceBlock,
}
