use leet_core::{Cogon, Dag, Msg1337, Payload};
use crate::error::BridgeError;
use crate::projector::SemanticProjector;

/// COGON → texto humano.
pub async fn cogon_to_text(
    cogon: &Cogon,
    projector: &dyn SemanticProjector,
) -> Result<String, BridgeError> {
    projector.reconstruct(cogon).await
}

/// DAG → texto humano.
/// Respeita depth: reconstrói depth níveis de folha pra raiz.
pub async fn dag_to_text(
    dag: &Dag,
    projector: &dyn SemanticProjector,
    depth: usize,
) -> Result<String, BridgeError> {
    projector.reconstruct_dag(dag, depth).await
}

/// MSG_1337 → texto humano.
/// Usa surface.reconstruct_depth. Inclui header com intent e urgency se relevante.
pub async fn msg_to_text(
    msg: &Msg1337,
    projector: &dyn SemanticProjector,
) -> Result<String, BridgeError> {
    let depth = msg.surface.reconstruct_depth as usize;
    
    // Reconstrói o payload
    let body = match &msg.payload {
        Payload::Single(cogon) => {
            cogon_to_text(cogon, projector).await?
        }
        Payload::Graph(dag) => {
            dag_to_text(dag, projector, depth).await?
        }
    };

    // Monta header se necessário
    let mut parts = Vec::new();
    
    // Intent
    parts.push(format!("[{}]", intent_to_str(&msg.intent)));
    
    // Urgência se alta
    if let Some(urgency) = msg.surface.urgency {
        if urgency > 0.7 {
            parts.push(format!("[URGÊNCIA: {:.0}%]", urgency * 100.0));
        }
    }
    
    // Corpo
    parts.push(body);
    
    Ok(parts.join(" "))
}

fn intent_to_str(intent: &leet_core::Intent) -> &'static str {
    match intent {
        leet_core::Intent::Assert => "ASSERT",
        leet_core::Intent::Query => "QUERY",
        leet_core::Intent::Delta => "DELTA",
        leet_core::Intent::Sync => "SYNC",
        leet_core::Intent::Anomaly => "ANOMALY",
        leet_core::Intent::Ack => "ACK",
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::projector::MockProjector;
    use leet_core::{Cogon, Intent, Receiver, CanonicalSpace, Surface, Msg1337};
    use uuid::Uuid;

    #[tokio::test]
    async fn test_cogon_to_text() {
        let projector = MockProjector::new();
        let cogon = Cogon::new(vec![0.5; 32], vec![0.1; 32]);
        
        let text = cogon_to_text(&cogon, &projector).await.unwrap();
        assert!(!text.is_empty());
        assert!(text.starts_with("[COGON:"));
    }

    #[tokio::test]
    async fn test_msg_to_text() {
        let projector = MockProjector::new();
        let cogon = Cogon::new(vec![0.5; 32], vec![0.1; 32]);
        
        let msg = Msg1337 {
            id: Uuid::new_v4(),
            sender: Uuid::new_v4(),
            receiver: Receiver::Broadcast,
            intent: Intent::Assert,
            ref_hash: None,
            patch: None,
            payload: Payload::Single(cogon),
            c5: CanonicalSpace {
                zone_fixed: vec![0.5; 32],
                zone_emergent: std::collections::HashMap::new(),
                schema_ver: "0.4.0".to_string(),
                align_hash: "0000000000000000000000000000000000000000000000000000000000000000".to_string(),
            },
            surface: Surface {
                human_required: false,
                urgency: Some(0.85),
                reconstruct_depth: 3,
                lang: "pt".to_string(),
            },
        };
        
        let text = msg_to_text(&msg, &projector).await.unwrap();
        assert!(text.contains("[ASSERT]"));
        assert!(text.contains("[URGÊNCIA:"));
    }
}
