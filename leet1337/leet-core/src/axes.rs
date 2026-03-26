/// Index constants for the 32 canonical axes.
pub const A0_VIA: usize = 0;
pub const A1_CORRESPONDENCIA: usize = 1;
pub const A2_VIBRACAO: usize = 2;
pub const A3_POLARIDADE: usize = 3;
pub const A4_RITMO: usize = 4;
pub const A5_CAUSA_EFEITO: usize = 5;
pub const A6_GENERO: usize = 6;
pub const A7_SISTEMA: usize = 7;
pub const A8_ESTADO: usize = 8;
pub const A9_PROCESSO: usize = 9;
pub const A10_RELACAO: usize = 10;
pub const A11_SINAL: usize = 11;
pub const A12_ESTABILIDADE: usize = 12;
pub const A13_VALENCIA_ONTOLOGICA: usize = 13;
pub const B1_VERIFICABILIDADE: usize = 14;
pub const B2_TEMPORALIDADE: usize = 15;
pub const B3_COMPLETUDE: usize = 16;
pub const B4_CAUSALIDADE: usize = 17;
pub const B5_REVERSIBILIDADE: usize = 18;
pub const B6_CARGA: usize = 19;
pub const B7_ORIGEM: usize = 20;
pub const B8_VALENCIA_EPISTEMICA: usize = 21;
pub const C1_URGENCIA: usize = 22;
pub const C2_IMPACTO: usize = 23;
pub const C3_ACAO: usize = 24;
pub const C4_VALOR: usize = 25;
pub const C5_ANOMALIA: usize = 26;
pub const C6_AFETO: usize = 27;
pub const C7_DEPENDENCIA: usize = 28;
pub const C8_VETOR_TEMPORAL: usize = 29;
pub const C9_NATUREZA: usize = 30;
pub const C10_VALENCIA_ACAO: usize = 31;

#[derive(Debug, Clone, PartialEq)]
pub enum AxisGroup {
    Ontological,
    Epistemic,
    Pragmatic,
}

#[derive(Debug, Clone)]
pub struct AxisDef {
    pub index: usize,
    pub code: &'static str,
    pub name: &'static str,
    pub group: AxisGroup,
    pub description: &'static str,
}

pub static CANONICAL_AXES: [AxisDef; 32] = [
    AxisDef { index: 0,  code: "A0",  name: "VIA",                    group: AxisGroup::Ontological, description: "Grau em que o conceito existe por si mesmo, independente de relações externas. Alta=essência pura. Baixa=só existe em função de outro." },
    AxisDef { index: 1,  code: "A1",  name: "CORRESPONDÊNCIA",        group: AxisGroup::Ontological, description: "Grau em que o conceito espelha padrões em outros níveis de abstração. Alta=mesmo padrão em múltiplas escalas." },
    AxisDef { index: 2,  code: "A2",  name: "VIBRAÇÃO",               group: AxisGroup::Ontological, description: "Grau em que o conceito está em movimento/transformação contínua. Alta=fluxo constante. Baixa=estático." },
    AxisDef { index: 3,  code: "A3",  name: "POLARIDADE",             group: AxisGroup::Ontological, description: "Grau em que o conceito está posicionado num espectro entre extremos. Alta=fortemente polar. Baixa=neutro." },
    AxisDef { index: 4,  code: "A4",  name: "RITMO",                  group: AxisGroup::Ontological, description: "Grau em que o conceito exibe padrão cíclico ou periódico. Alta=ritmo claro. Baixa=irregular ou único." },
    AxisDef { index: 5,  code: "A5",  name: "CAUSA E EFEITO",         group: AxisGroup::Ontological, description: "Grau em que o conceito é agente causal vs efeito. Alta=causa primária. Baixa=consequência pura." },
    AxisDef { index: 6,  code: "A6",  name: "GÊNERO",                 group: AxisGroup::Ontological, description: "Grau em que o conceito é gerador/ativo vs receptivo/passivo. Alta=princípio ativo. Baixa=princípio receptivo." },
    AxisDef { index: 7,  code: "A7",  name: "SISTEMA",                group: AxisGroup::Ontological, description: "Grau em que o conceito é um conjunto com comportamento emergente." },
    AxisDef { index: 8,  code: "A8",  name: "ESTADO",                 group: AxisGroup::Ontological, description: "Grau em que o conceito é uma configuração num dado momento." },
    AxisDef { index: 9,  code: "A9",  name: "PROCESSO",               group: AxisGroup::Ontological, description: "Grau em que o conceito é transformação no tempo." },
    AxisDef { index: 10, code: "A10", name: "RELAÇÃO",                group: AxisGroup::Ontological, description: "Grau em que o conceito é conexão entre entidades." },
    AxisDef { index: 11, code: "A11", name: "SINAL",                  group: AxisGroup::Ontological, description: "Grau em que o conceito é informação carregando variação." },
    AxisDef { index: 12, code: "A12", name: "ESTABILIDADE",           group: AxisGroup::Ontological, description: "Grau em que o conceito tende ao equilíbrio ou à divergência. Alta=convergente. Baixa=instável/caótico." },
    AxisDef { index: 13, code: "A13", name: "VALÊNCIA ONTOLÓGICA",    group: AxisGroup::Ontological, description: "Sinal intrínseco do conceito. 0=negativo/contrativo → 0.5=neutro → 1=positivo/expansivo." },
    AxisDef { index: 14, code: "B1",  name: "VERIFICABILIDADE",       group: AxisGroup::Epistemic,   description: "Grau em que o conceito pode ser confirmado externamente. Alta=verificável por evidência. Baixa=não falsificável." },
    AxisDef { index: 15, code: "B2",  name: "TEMPORALIDADE",          group: AxisGroup::Epistemic,   description: "Grau em que o conceito tem âncora temporal definida. Alta=momento preciso. Baixa=atemporal ou indefinido." },
    AxisDef { index: 16, code: "B3",  name: "COMPLETUDE",             group: AxisGroup::Epistemic,   description: "Grau em que o conceito está resolvido. Alta=fechado, conclusivo. Baixa=aberto, em construção." },
    AxisDef { index: 17, code: "B4",  name: "CAUSALIDADE",            group: AxisGroup::Epistemic,   description: "Grau em que a origem do conceito é identificável. Alta=causa clara. Baixa=origem opaca ou difusa." },
    AxisDef { index: 18, code: "B5",  name: "REVERSIBILIDADE",        group: AxisGroup::Epistemic,   description: "Grau em que o conceito pode ser desfeito. Alta=totalmente reversível. Baixa=irreversível." },
    AxisDef { index: 19, code: "B6",  name: "CARGA",                  group: AxisGroup::Epistemic,   description: "Grau de recurso cognitivo que o conceito consome. Alta=pesado, exige atenção. Baixa=automático, fluido." },
    AxisDef { index: 20, code: "B7",  name: "ORIGEM",                 group: AxisGroup::Epistemic,   description: "Grau em que o conhecimento é observado vs inferido vs assumido. Alta=observação direta. Baixa=suposição pura." },
    AxisDef { index: 21, code: "B8",  name: "VALÊNCIA EPISTÊMICA",   group: AxisGroup::Epistemic,   description: "Sinal do conhecimento do agente. 0=evidência contraditória → 0.5=inconclusivo → 1=evidência confirmatória." },
    AxisDef { index: 22, code: "C1",  name: "URGÊNCIA",               group: AxisGroup::Pragmatic,   description: "Grau em que o conceito exige resposta imediata. Alta=pressão temporal crítica. Baixa=sem pressa." },
    AxisDef { index: 23, code: "C2",  name: "IMPACTO",                group: AxisGroup::Pragmatic,   description: "Grau em que o conceito gera consequências. Alta=muda estado do sistema. Baixa=inócuo." },
    AxisDef { index: 24, code: "C3",  name: "AÇÃO",                   group: AxisGroup::Pragmatic,   description: "Grau em que o conceito exige resposta ativa vs é só alinhamento. Alta=demanda execução. Baixa=puramente informativo." },
    AxisDef { index: 25, code: "C4",  name: "VALOR",                  group: AxisGroup::Pragmatic,   description: "Grau em que o conceito conecta com algo que importa de verdade. Alta=carregado de significado. Baixa=neutro axiologicamente." },
    AxisDef { index: 26, code: "C5",  name: "ANOMALIA",               group: AxisGroup::Pragmatic,   description: "Grau em que o conceito é desvio do padrão esperado. Alta=ruptura forte. Baixa=dentro do normal." },
    AxisDef { index: 27, code: "C6",  name: "AFETO",                  group: AxisGroup::Pragmatic,   description: "Grau em que o conceito carrega valência emocional relevante. Alta=forte carga afetiva. Baixa=neutro emocionalmente." },
    AxisDef { index: 28, code: "C7",  name: "DEPENDÊNCIA",            group: AxisGroup::Pragmatic,   description: "Grau em que o conceito precisa de outro para existir. Alta=totalmente acoplado. Baixa=autônomo." },
    AxisDef { index: 29, code: "C8",  name: "VETOR TEMPORAL",         group: AxisGroup::Pragmatic,   description: "Orientação no tempo. 0=passado puro → 0.5=presente → 1=futuro puro." },
    AxisDef { index: 30, code: "C9",  name: "NATUREZA",               group: AxisGroup::Pragmatic,   description: "Categoria semântica fundamental. 0=substantivo puro → 1=verbo puro." },
    AxisDef { index: 31, code: "C10", name: "VALÊNCIA DE AÇÃO",       group: AxisGroup::Pragmatic,   description: "Sinal da intenção do agente ao transmitir. 0=negativo/alerta/contrativo → 0.5=neutro/consulta → 1=positivo/confirmação/expansivo." },
];

pub fn axis(index: usize) -> Option<&'static AxisDef> {
    CANONICAL_AXES.get(index)
}

pub fn axes_in_group(group: &AxisGroup) -> Vec<&'static AxisDef> {
    CANONICAL_AXES.iter().filter(|a| &a.group == group).collect()
}
