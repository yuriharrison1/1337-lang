use async_trait::async_trait;
use leet_core::{Cogon, Dag, FIXED_DIMS};
use crate::error::BridgeError;

/// Trait que qualquer backend de projeção semântica implementa.
/// Anthropic Claude, OpenAI, modelo local, Ollama, whatever.
#[async_trait]
pub trait SemanticProjector: Send + Sync {
    /// Projeta texto humano nos 32 eixos canônicos.
    /// Retorna (sem[32], unc[32]).
    async fn project(&self, text: &str) -> Result<(Vec<f32>, Vec<f32>), BridgeError>;

    /// Reconstrói texto humano a partir de um COGON.
    async fn reconstruct(&self, cogon: &Cogon) -> Result<String, BridgeError>;

    /// Reconstrói texto a partir de um DAG completo.
    /// depth = quantos níveis reconstruir (de folha pra raiz).
    async fn reconstruct_dag(&self, dag: &Dag, depth: usize) -> Result<String, BridgeError>;
}

/// MockProjector para testes sem API key.
/// Implementa SemanticProjector com lógica determinística.
pub struct MockProjector;

impl MockProjector {
    pub fn new() -> Self {
        Self
    }

    /// Gera o prompt para projeção nos 32 eixos.
    pub fn projection_prompt(text: &str) -> String {
        let axes_list = [
            (0, "A0", "VIA", "Grau em que o conceito existe por si mesmo (0=dependente, 1=essência pura)"),
            (1, "A1", "CORRESPONDÊNCIA", "Grau em que espelha padrões em outras escalas (0=único, 1=fractal)"),
            (2, "A2", "VIBRAÇÃO", "Grau de movimento/transformação contínua (0=estático, 1=fluxo constante)"),
            (3, "A3", "POLARIDADE", "Posição no espectro entre extremos (0=neutro, 1=fortemente polar)"),
            (4, "A4", "RITMO", "Padrão cíclico ou periódico (0=irregular, 1=ritmo claro)"),
            (5, "A5", "CAUSA E EFEITO", "Grau como agente causal vs efeito (0=consequência, 1=causa primária)"),
            (6, "A6", "GÊNERO", "Princípio ativo vs receptivo (0=receptivo, 1=ativo/gerador)"),
            (7, "A7", "SISTEMA", "Comportamento emergente de conjunto (0=parte, 1=sistema)"),
            (8, "A8", "ESTADO", "Configuração num dado momento (0=processo, 1=estado)"),
            (9, "A9", "PROCESSO", "Transformação no tempo (0=estático, 1=processo puro)"),
            (10, "A10", "RELAÇÃO", "Conexão entre entidades (0=independente, 1=relational)"),
            (11, "A11", "SINAL", "Informação carregando variação (0=ruído, 1=sinal puro)"),
            (12, "A12", "ESTABILIDADE", "Tendência ao equilíbrio (0=caótico, 1=convergente)"),
            (13, "A13", "VALÊNCIA ONTOLÓGICA", "Sinal intrínseco: 0=negativo, 0.5=neutro, 1=positivo"),
            (14, "B1", "VERIFICABILIDADE", "Confirmabilidade externa (0=não falsificável, 1=verificável)"),
            (15, "B2", "TEMPORALIDADE", "Âncora temporal definida (0=atemporal, 1=momento preciso)"),
            (16, "B3", "COMPLETUDE", "Resolvido vs aberto (0=em construção, 1=fechado/conclusivo)"),
            (17, "B4", "CAUSALIDADE", "Origem identificável (0=opaca, 1=causa clara)"),
            (18, "B5", "REVERSIBILIDADE", "Possibilidade de desfazer (0=irreversível, 1=reversível)"),
            (19, "B6", "CARGA", "Recurso cognitivo consumido (0=automático, 1=pesado)"),
            (20, "B7", "ORIGEM", "Observado vs inferido vs assumido (0=suposição, 1=observação direta)"),
            (21, "B8", "VALÊNCIA EPISTÊMICA", "Sinal do conhecimento: 0=contraditório, 0.5=inconclusivo, 1=confirmatório"),
            (22, "C1", "URGÊNCIA", "Demanda de resposta imediata (0=sem pressa, 1=crítico)"),
            (23, "C2", "IMPACTO", "Consequências geradas (0=inócuo, 1=muda estado do sistema)"),
            (24, "C3", "AÇÃO", "Demanda resposta ativa vs alinhamento (0=informativo, 1=execução)"),
            (25, "C4", "VALOR", "Conexão com o que importa (0=neutro, 1=carregado de significado)"),
            (26, "C5", "ANOMALIA", "Desvio do esperado (0=normal, 1=ruptura forte)"),
            (27, "C6", "AFETO", "Carga emocional (0=neutro, 1=forte carga afetiva)"),
            (28, "C7", "DEPENDÊNCIA", "Necessidade de outro para existir (0=autônomo, 1=acoplado)"),
            (29, "C8", "VETOR TEMPORAL", "Orientação no tempo: 0=passado, 0.5=presente, 1=futuro"),
            (30, "C9", "NATUREZA", "Substantivo vs verbo: 0=coisa/estado, 1=ação/transformação"),
            (31, "C10", "VALÊNCIA DE AÇÃO", "Intenção ao transmitir: 0=alerta, 0.5=consulta, 1=confirmação"),
        ];

        let mut prompt = String::from(
            "Você é um projetor semântico especializado. \
            Sua tarefa é projetar o texto abaixo nos 32 eixos canônicos da linguagem 1337.\n\n"
        );
        prompt.push_str("EIXOS CANÔNICOS (32 dimensões):\n");
        prompt.push_str("=".repeat(60).as_str());
        prompt.push('\n');

        for (idx, code, name, desc) in &axes_list {
            prompt.push_str(&format!("[{:2}] {} {}: {}\n", idx, code, name, desc));
        }

        prompt.push_str("=".repeat(60).as_str());
        prompt.push_str("\n\nTEXTO A PROJETAR:\n\"");
        prompt.push_str(text);
        prompt.push_str("\"\n\n");
        prompt.push_str(
            "INSTRUÇÕES:\n\
            1. Analise o texto cuidadosamente\n\
            2. Para cada eixo, atribua um valor float entre 0.0 e 1.0\n\
            3. sem[i] = valor semântico no eixo i\n\
            4. unc[i] = incerteza da projeção (0.0=certeza, 1.0=total incerteza)\n\n"
        );
        prompt.push_str(
            "RESPONDA APENAS com JSON no formato exato:\n\
            {\"sem\": [0.0, ..., 0.0], \"unc\": [0.0, ..., 0.0]}\n"
        );

        prompt
    }

    /// Gera o prompt para reconstrução de texto a partir de COGON.
    pub fn reconstruction_prompt(cogon: &Cogon) -> String {
        let axes_names = [
            "A0_VIA", "A1_CORRESPONDENCIA", "A2_VIBRACAO", "A3_POLARIDADE",
            "A4_RITMO", "A5_CAUSA_EFEITO", "A6_GENERO", "A7_SISTEMA",
            "A8_ESTADO", "A9_PROCESSO", "A10_RELACAO", "A11_SINAL",
            "A12_ESTABILIDADE", "A13_VALENCIA_ONTOLOGICA",
            "B1_VERIFICABILIDADE", "B2_TEMPORALIDADE", "B3_COMPLETUDE", "B4_CAUSALIDADE",
            "B5_REVERSIBILIDADE", "B6_CARGA", "B7_ORIGEM", "B8_VALENCIA_EPISTEMICA",
            "C1_URGENCIA", "C2_IMPACTO", "C3_ACAO", "C4_VALOR",
            "C5_ANOMALIA", "C6_AFETO", "C7_DEPENDENCIA", "C8_VETOR_TEMPORAL",
            "C9_NATUREZA", "C10_VALENCIA_ACAO",
        ];

        let mut prompt = String::from(
            "Você é um reconstrutor semântico. \
            Reconstrua texto natural a partir da projeção 1337 abaixo.\n\n"
        );
        prompt.push_str("PROJEÇÃO NOS 32 EIXOS:\n");
        prompt.push_str("-".repeat(40).as_str());
        prompt.push('\n');

        for i in 0..FIXED_DIMS {
            let sem = cogon.sem.get(i).copied().unwrap_or(0.5);
            let unc = cogon.unc.get(i).copied().unwrap_or(0.5);
            prompt.push_str(&format!(
                "[{:2}] {:25} sem={:.2} unc={:.2}\n",
                i, axes_names[i], sem, unc
            ));
        }

        prompt.push_str("-".repeat(40).as_str());
        prompt.push_str("\n\nINSTRUÇÕES:\n");
        prompt.push_str(
            "Gere uma frase ou parágrafo curto em português que capture \
            o significado expresso nos eixos mais ativados (sem > 0.7). \
            Ignore eixos com alta incerteza (unc > 0.5).\n\n"
        );
        prompt.push_str("TEXTO RECONSTRUÍDO:\n");

        prompt
    }
}

impl Default for MockProjector {
    fn default() -> Self {
        Self::new()
    }
}

#[async_trait]
impl SemanticProjector for MockProjector {
    async fn project(&self, text: &str) -> Result<(Vec<f32>, Vec<f32>), BridgeError> {
        let text_lower = text.to_lowercase();
        let mut sem = vec![0.5; FIXED_DIMS];
        let mut unc = vec![0.3; FIXED_DIMS];

        // Heurísticas baseadas em keywords
        if text_lower.contains("urgente") || text_lower.contains("urgência") {
            sem[22] = 0.95; // C1_URGÊNCIA
            sem[24] = 0.9;  // C3_AÇÃO
            unc[22] = 0.05;
            unc[24] = 0.1;
        }

        if text_lower.contains("caiu") 
            || text_lower.contains("falhou") 
            || text_lower.contains("erro")
            || text_lower.contains("down")
        {
            sem[8] = 0.9;   // A8_ESTADO
            sem[9] = 0.8;   // A9_PROCESSO
            sem[26] = 0.9;  // C5_ANOMALIA
            sem[22] = 0.85; // C1_URGÊNCIA
            unc[8] = 0.05;
            unc[26] = 0.1;
        }

        if text_lower.contains("deploy") 
            || text_lower.contains("processo")
            || text_lower.contains("pipeline")
        {
            sem[9] = 0.85;  // A9_PROCESSO
            sem[30] = 0.8;  // C9_NATUREZA (verbo/ação)
            unc[9] = 0.1;
        }

        if text_lower.contains("reverter") 
            || text_lower.contains("desfazer")
            || text_lower.contains("rollback")
        {
            sem[18] = 0.9;  // B5_REVERSIBILIDADE
            sem[24] = 0.85; // C3_AÇÃO
            unc[18] = 0.1;
        }

        if text_lower.contains("olá") 
            || text_lower.contains("oi") 
            || text_lower.contains("hello")
        {
            sem[27] = 0.6;  // C6_AFETO
            sem[30] = 0.3;  // C9_NATUREZA (substantivo)
        }

        Ok((sem, unc))
    }

    async fn reconstruct(&self, cogon: &Cogon) -> Result<String, BridgeError> {
        // Encontra os 3 eixos mais ativados
        let mut indexed: Vec<(usize, &f32)> = cogon.sem.iter().enumerate().collect();
        indexed.sort_by(|a, b| b.1.partial_cmp(a.1).unwrap());
        let top_axes: Vec<usize> = indexed.iter().take(3).map(|(i, _)| *i).collect();

        let axes_names = [
            "VIA", "CORRESPONDENCIA", "VIBRACAO", "POLARIDADE",
            "RITMO", "CAUSA_EFEITO", "GENERO", "SISTEMA",
            "ESTADO", "PROCESSO", "RELACAO", "SINAL",
            "ESTABILIDADE", "VALENCIA_ONTOLOGICA",
            "VERIFICABILIDADE", "TEMPORALIDADE", "COMPLETUDE", "CAUSALIDADE",
            "REVERSIBILIDADE", "CARGA", "ORIGEM", "VALENCIA_EPISTEMICA",
            "URGENCIA", "IMPACTO", "ACAO", "VALOR",
            "ANOMALIA", "AFETO", "DEPENDENCIA", "VETOR_TEMPORAL",
            "NATUREZA", "VALENCIA_ACAO",
        ];

        let mut parts = Vec::new();
        for idx in &top_axes {
            let val = cogon.sem[*idx];
            if val > 0.3 {
                parts.push(format!("{}={:.2}", axes_names[*idx], val));
            }
        }

        if parts.is_empty() {
            Ok("[COGON: semântica neutra]".to_string())
        } else {
            Ok(format!("[COGON: {}]", parts.join(", ")))
        }
    }

    async fn reconstruct_dag(&self, dag: &Dag, _depth: usize) -> Result<String, BridgeError> {
        let mut parts = Vec::new();
        
        // Reconstrói em ordem topológica (simples: segue nós na ordem)
        for node in &dag.nodes {
            let reconstructed = self.reconstruct(node).await?;
            parts.push(reconstructed);
        }

        Ok(parts.join(" → "))
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[tokio::test]
    async fn test_text_to_cogon_basic() {
        let projector = MockProjector::new();
        let (sem, unc) = projector.project("olá").await.unwrap();
        
        assert_eq!(sem.len(), 32);
        assert_eq!(unc.len(), 32);
        // Valores devem ser razoáveis
        assert!(sem.iter().all(|&v| v >= 0.0 && v <= 1.0));
        assert!(unc.iter().all(|&v| v >= 0.0 && v <= 1.0));
    }

    #[tokio::test]
    async fn test_text_to_cogon_urgent() {
        let projector = MockProjector::new();
        let (sem, _unc) = projector.project("situação urgente").await.unwrap();
        
        // C1_URGÊNCIA (índice 22) deve ser alto
        assert!(sem[22] > 0.8, "URGÊNCIA deve ser > 0.8 para texto 'urgente'");
        // C3_AÇÃO (índice 24) também deve ser alto
        assert!(sem[24] > 0.7, "AÇÃO deve ser > 0.7 para texto 'urgente'");
    }

    #[tokio::test]
    async fn test_cogon_to_text() {
        let projector = MockProjector::new();
        let cogon = Cogon::new(vec![0.5; 32], vec![0.1; 32]);
        
        let text = projector.reconstruct(&cogon).await.unwrap();
        assert!(!text.is_empty());
        assert!(text.starts_with("[COGON:"));
    }

    #[tokio::test]
    async fn test_roundtrip() {
        let projector = MockProjector::new();
        let original = "situação urgente no servidor";
        
        // Texto → COGON
        let (sem, unc) = projector.project(original).await.unwrap();
        let cogon = Cogon::new(sem.clone(), unc);
        
        // COGON → texto
        let reconstructed = projector.reconstruct(&cogon).await.unwrap();
        
        // Verifica que não perdeu a semântica de urgência
        assert!(sem[22] > 0.7, "Semântica de urgência preservada");
        assert!(!reconstructed.is_empty());
    }

    #[test]
    fn test_projection_prompt_format() {
        let prompt = MockProjector::projection_prompt("teste");
        assert!(prompt.contains("A0 VIA"));
        assert!(prompt.contains("C10 VALÊNCIA DE AÇÃO"));
        assert!(prompt.contains("teste"));
        assert!(prompt.contains("JSON"));
    }

    #[test]
    fn test_reconstruction_prompt_format() {
        let cogon = Cogon::new(vec![0.5; 32], vec![0.1; 32]);
        let prompt = MockProjector::reconstruction_prompt(&cogon);
        assert!(prompt.contains("A0_VIA"));
        assert!(prompt.contains("reconstrutor semântico"));
    }
}
