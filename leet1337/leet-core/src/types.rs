use std::collections::HashMap;
use std::time::{SystemTime, UNIX_EPOCH};

use serde::{Deserialize, Serialize};
use sha2::{Digest, Sha256};
use uuid::Uuid;

use crate::error::{LeetError, LeetResult};
use crate::FIXED_DIMS;

pub type Scalar = f32;
pub type SemanticVector = Vec<f32>;
pub type Hash = String;
pub type Id = Uuid;

// ─── RAW ────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum RawRole {
    Evidence,
    Artifact,
    Trace,
    Bridge,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Raw {
    pub content_type: String,
    pub content: serde_json::Value,
    pub role: RawRole,
}

// ─── COGON ───────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Cogon {
    pub id: Uuid,
    pub sem: Vec<f32>,
    pub unc: Vec<f32>,
    pub stamp: i64,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub raw: Option<Raw>,
}

impl Cogon {
    /// Create a new COGON with auto-generated UUID and current timestamp.
    pub fn new(sem: Vec<f32>, unc: Vec<f32>) -> Self {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map(|d| d.as_nanos() as i64)
            .unwrap_or(0);
        Cogon {
            id: Uuid::new_v4(),
            sem,
            unc,
            stamp,
            raw: None,
        }
    }

    /// COGON_ZERO — "I AM" — primordial utterance.
    /// sem=[1;32], unc=[0;32], id=nil, stamp=0, raw=None
    pub fn zero() -> Self {
        Cogon {
            id: Uuid::nil(),
            sem: vec![1.0f32; FIXED_DIMS],
            unc: vec![0.0f32; FIXED_DIMS],
            stamp: 0,
            raw: None,
        }
    }

    /// Returns true if this is COGON_ZERO (nil id + stamp=0).
    pub fn is_zero(&self) -> bool {
        self.id == Uuid::nil() && self.stamp == 0
    }

    /// Returns indices where unc > LOW_CONFIDENCE_THRESHOLD (R5).
    pub fn low_confidence_dims(&self) -> Vec<usize> {
        self.unc
            .iter()
            .enumerate()
            .filter(|(_, &u)| u > crate::LOW_CONFIDENCE_THRESHOLD)
            .map(|(i, _)| i)
            .collect()
    }

    /// Returns a clone with the given RAW field set.
    pub fn with_raw(mut self, raw: Raw) -> Self {
        self.raw = Some(raw);
        self
    }
}

// ─── EDGE ────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum EdgeType {
    Causa,
    Condiciona,
    Contradiz,
    Refina,
    Emerge,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Edge {
    pub from: Uuid,
    pub to: Uuid,
    pub edge_type: EdgeType,
    pub weight: f32,
}

// ─── DAG ─────────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Dag {
    pub root: Uuid,
    pub nodes: Vec<Cogon>,
    pub edges: Vec<Edge>,
}

impl Dag {
    /// Create a DAG with a single root node.
    pub fn from_root(cogon: Cogon) -> Self {
        let root = cogon.id;
        Dag {
            root,
            nodes: vec![cogon],
            edges: vec![],
        }
    }

    pub fn add_node(&mut self, cogon: Cogon) {
        self.nodes.push(cogon);
    }

    pub fn add_edge(&mut self, edge: Edge) {
        self.edges.push(edge);
    }

    pub fn node_ids(&self) -> Vec<Uuid> {
        self.nodes.iter().map(|n| n.id).collect()
    }

    pub fn parents_of(&self, id: Uuid) -> Vec<Uuid> {
        self.edges
            .iter()
            .filter(|e| e.to == id)
            .map(|e| e.from)
            .collect()
    }

    /// Topological order using Kahn's algorithm. Returns R4 error if cycle detected.
    pub fn topological_order(&self) -> LeetResult<Vec<Uuid>> {
        let ids = self.node_ids();
        let n = ids.len();

        // Build in-degree map
        let mut in_degree: HashMap<Uuid, usize> = ids.iter().map(|&id| (id, 0)).collect();
        for edge in &self.edges {
            if let Some(deg) = in_degree.get_mut(&edge.to) {
                *deg += 1;
            }
        }

        // Queue of nodes with in-degree 0
        let mut queue: std::collections::VecDeque<Uuid> = in_degree
            .iter()
            .filter(|(_, &d)| d == 0)
            .map(|(&id, _)| id)
            .collect();

        let mut result = Vec::with_capacity(n);

        while let Some(node) = queue.pop_front() {
            result.push(node);
            for edge in self.edges.iter().filter(|e| e.from == node) {
                if let Some(deg) = in_degree.get_mut(&edge.to) {
                    *deg -= 1;
                    if *deg == 0 {
                        queue.push_back(edge.to);
                    }
                }
            }
        }

        if result.len() != n {
            return Err(LeetError::R4DagCycle);
        }

        Ok(result)
    }
}

// ─── INTENT ──────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize, PartialEq)]
#[serde(rename_all = "SCREAMING_SNAKE_CASE")]
pub enum Intent {
    Assert,
    Query,
    Delta,
    Sync,
    Anomaly,
    Ack,
}

// ─── RECEIVER ────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Receiver {
    Agent(Uuid),
    Broadcast,
}

impl Receiver {
    pub fn is_broadcast(&self) -> bool {
        matches!(self, Receiver::Broadcast)
    }
}

// ─── PAYLOAD ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum Payload {
    Single(Cogon),
    Graph(Dag),
}

// ─── CANONICAL SPACE (C5) ────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct CanonicalSpace {
    pub zone_fixed: Vec<f32>,
    pub zone_emergent: HashMap<Uuid, f32>,
    pub schema_ver: String,
    pub align_hash: Hash,
}

// ─── SURFACE (C4) ────────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Surface {
    pub human_required: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub urgency: Option<f32>,
    pub reconstruct_depth: i32,
    pub lang: String,
}

// ─── MSG_1337 ────────────────────────────────────────────────────────────────

/// Complete message envelope. Fields in canonical order (R17).
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Msg1337 {
    // [1] Identity
    pub id: Uuid,
    pub sender: Uuid,
    pub receiver: Receiver,

    // [2] Intention
    pub intent: Intent,

    // [3] Delta reference
    #[serde(skip_serializing_if = "Option::is_none")]
    pub ref_hash: Option<Hash>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub patch: Option<Vec<f32>>,

    // [4] Semantic content
    pub payload: Payload,

    // [5] Canonical space
    pub c5: CanonicalSpace,

    // [6] Human interface
    pub surface: Surface,
}

impl Msg1337 {
    /// SHA-256 hash of the canonical JSON serialization.
    pub fn hash(&self) -> Hash {
        let json = serde_json::to_string(self).unwrap_or_default();
        let result = Sha256::digest(json.as_bytes());
        hex::encode(result)
    }
}

// ─── EMERGENT ZONE ───────────────────────────────────────────────────────────

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct EmergentRegistration {
    pub id: Uuid,
    pub created_by: Vec<Uuid>,
    pub freq: u64,
    pub anchor_ref: Vec<f32>,
    pub label_human: Option<String>,
}

// ─── ANCHORS ─────────────────────────────────────────────────────────────────

#[derive(Debug, Clone, PartialEq)]
pub enum Anchor {
    Presenca,
    Ausencia,
    Mudanca,
    Agencia,
    Incerteza,
}
