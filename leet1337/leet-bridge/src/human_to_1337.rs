use leet_core::{
    Cogon, Dag, Msg1337, Intent, Receiver, CanonicalSpace, Surface, 
    Payload, Validator, FIXED_DIMS, Hash as LeetHash
};
use uuid::Uuid;
use crate::error::BridgeError;
use crate::projector::SemanticProjector;

/// Bridge para tradução de texto humano → estruturas 1337.
pub struct HumanBridge {
    projector: Box<dyn SemanticProjector>,
}

impl HumanBridge {
    /// Cria um novo HumanBridge com o projetor especificado.
    pub fn new(projector: Box<dyn SemanticProjector>) -> Self {
        Self { projector }
    }

    /// Texto → COGON.
    /// Projeta, valida R5 (low confidence) implicitamente via unc values.
    pub async fn text_to_cogon(&self, text: &str) -> Result<Cogon, BridgeError> {
        let (sem, unc) = self.projector.project(text).await?;
        
        // Valida dimensões
        if sem.len() != FIXED_DIMS || unc.len() != FIXED_DIMS {
            return Err(BridgeError::ProjectionFailed(
                format!("Dimensões incorretas: sem={}, unc={}, esperado={}", 
                    sem.len(), unc.len(), FIXED_DIMS)
            ));
        }

        let cogon = Cogon::new(sem, unc);
        
        Ok(cogon)
    }

    /// Texto complexo → DAG com múltiplos COGONs.
    /// Separa o texto em sentenças/conceitos, projeta cada um,
    /// infere edges entre eles (CAUSA, CONDICIONA, etc).
    pub async fn text_to_dag(&self, text: &str) -> Result<Dag, BridgeError> {
        // Simples: split por '.' para sentenças
        let sentences: Vec<&str> = text
            .split('.')
            .map(|s| s.trim())
            .filter(|s| !s.is_empty())
            .collect();

        if sentences.is_empty() {
            return Err(BridgeError::ProjectionFailed(
                "Texto vazio ou sem sentenças".to_string()
            ));
        }

        // Se só tem uma frase, vira COGON único como raiz
        if sentences.len() == 1 {
            let cogon = self.text_to_cogon(sentences[0]).await?;
            return Ok(Dag::from_root(cogon));
        }

        // Múltiplas sentenças: cada uma vira um COGON
        let mut nodes = Vec::new();
        for sentence in &sentences {
            let cogon = self.text_to_cogon(sentence).await?;
            nodes.push(cogon);
        }

        // Cria DAG com primeiro nó como raiz
        let root = nodes[0].id;
        let mut dag = Dag {
            root,
            nodes: nodes.clone(),
            edges: Vec::new(),
        };

        // Heurística: sentenças se conectam com CONDICIONA (sequência lógica)
        for i in 0..nodes.len().saturating_sub(1) {
            let edge = leet_core::Edge {
                from: nodes[i].id,
                to: nodes[i + 1].id,
                edge_type: leet_core::EdgeType::Condiciona,
                weight: 0.7,
            };
            dag.add_edge(edge);
        }

        Ok(dag)
    }

    /// Texto → MSG_1337 completa.
    /// Monta o envelope com todos os campos, valida com Validator.
    pub async fn text_to_msg(
        &self,
        text: &str,
        sender: Uuid,
        receiver: Receiver,
        intent: Intent,
    ) -> Result<Msg1337, BridgeError> {
        // Determina se é DAG ou COGON simples
        let payload = if text.contains('.') && text.split('.').count() > 1 {
            let dag = self.text_to_dag(text).await?;
            Payload::Graph(dag)
        } else {
            let cogon = self.text_to_cogon(text).await?;
            Payload::Single(cogon)
        };

        // Extrai zone_fixed do payload
        let zone_fixed = match &payload {
            Payload::Single(c) => c.sem.clone(),
            Payload::Graph(d) => {
                // Usa a raiz como referência
                d.nodes.iter()
                    .find(|n| n.id == d.root)
                    .map(|n| n.sem.clone())
                    .unwrap_or_else(|| vec![0.5; FIXED_DIMS])
            }
        };

        // Extrai urgência da dimensão C1 (índice 22)
        let urgency = zone_fixed.get(22).copied();

        // Cria C5 (espaço canônico)
        let c5 = CanonicalSpace {
            zone_fixed,
            zone_emergent: std::collections::HashMap::new(),
            schema_ver: "0.4.0".to_string(),
            align_hash: "0000000000000000000000000000000000000000000000000000000000000000".to_string(), // hash genérico
        };

        // Cria Surface (interface humana)
        let surface = Surface {
            human_required: false,
            urgency,
            reconstruct_depth: 3,
            lang: "pt".to_string(),
        };

        // Monta a mensagem
        let msg = Msg1337 {
            id: Uuid::new_v4(),
            sender,
            receiver,
            intent,
            ref_hash: None,
            patch: None,
            payload,
            c5,
            surface,
        };

        // Validação via leet_core
        Validator::validate(&msg)
            .map_err(|e| BridgeError::ValidationFailed(e))?;

        Ok(msg)
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::projector::MockProjector;

    #[tokio::test]
    async fn test_text_to_cogon_basic() {
        let bridge = HumanBridge::new(Box::new(MockProjector::new()));
        let cogon = bridge.text_to_cogon("olá mundo").await.unwrap();
        
        assert_eq!(cogon.sem.len(), 32);
        assert_eq!(cogon.unc.len(), 32);
        assert!(!cogon.id.is_nil());
    }

    #[tokio::test]
    async fn test_text_to_dag_single_sentence() {
        let bridge = HumanBridge::new(Box::new(MockProjector::new()));
        let dag = bridge.text_to_dag("o sol brilha").await.unwrap();
        
        assert_eq!(dag.nodes.len(), 1);
        assert!(dag.edges.is_empty());
    }

    #[tokio::test]
    async fn test_text_to_dag_multi_sentence() {
        let bridge = HumanBridge::new(Box::new(MockProjector::new()));
        let dag = bridge.text_to_dag("O servidor caiu. Precisamos agir.").await.unwrap();
        
        assert_eq!(dag.nodes.len(), 2);
        assert_eq!(dag.edges.len(), 1); // CONDICIONA entre as frases
    }

    #[tokio::test]
    async fn test_msg_envelope() {
        let bridge = HumanBridge::new(Box::new(MockProjector::new()));
        let sender = Uuid::new_v4();
        let receiver = Receiver::Agent(Uuid::new_v4());
        
        let msg = bridge.text_to_msg(
            "Teste de mensagem",
            sender,
            receiver,
            Intent::Assert
        ).await.unwrap();
        
        assert_eq!(msg.sender, sender);
        assert_eq!(msg.intent, Intent::Assert);
        assert_eq!(msg.c5.schema_ver, "0.4.0");
        assert_eq!(msg.surface.lang, "pt");
    }
}
