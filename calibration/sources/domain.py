"""
Fontes de dados especializadas por domínio.

Fornecem textos típicos de domínios específicos (tech, medical, legal)
para treinamento especializado da matriz W.
"""

from typing import Iterator
import random

from .base import DataSource, TextSample, SourceConfig


class TechDomainSource(DataSource):
    """
    Fonte de dados especializada em tecnologia/software.
    
    Gera ou retorna textos típicos de:
    - Logs de sistema
    - Mensagens de commit
    - Descrições de bugs
    - Documentação técnica
    - Alertas de monitoramento
    
    Exemplo:
        config = SourceConfig(max_samples=200)
        source = TechDomainSource(config=config)
        samples = source.fetch_all()
    """
    
    # Templates de textos técnicos
    LOG_MESSAGES = [
        "ERROR: Connection timeout after 30s to database cluster db-primary-03",
        "WARN: Memory usage at 87%, approaching threshold of 90%",
        "INFO: Deploy completed successfully, version 2.4.1 active",
        "DEBUG: Cache miss for key user:12345:profile, fetching from DB",
        "FATAL: OutOfMemoryError in worker thread #7, process terminating",
        "ERROR: Failed to parse JSON payload: unexpected token at position 42",
        "INFO: Background job completed: 15000 records processed in 4.2s",
        "WARN: API rate limit at 85% for key sk_live_****",
        "ERROR: Deadlock detected in transaction tx-8847, rolling back",
        "INFO: Auto-scaling triggered: adding 3 instances to pool",
    ]
    
    COMMIT_MESSAGES = [
        "fix(auth): resolve race condition in token refresh",
        "feat(api): add pagination support for list endpoints",
        "refactor(db): migrate user schema to v3, add indexes",
        "docs(readme): update installation instructions for macOS",
        "test(integration): add coverage for payment webhook",
        "chore(deps): bump lodash from 4.17.20 to 4.17.21",
        "perf(query): optimize JOIN operation, reduce time by 40%",
        "revert: roll back commit abc123 due to regression",
        "ci(pipeline): add smoke tests before production deploy",
        "security(patch): update openssl to fix CVE-2024-XXXX",
    ]
    
    BUG_DESCRIPTIONS = [
        "Usuários relatam timeout intermitente ao fazer upload de arquivos >100MB."
        "O problema ocorre apenas em conexões lentas (<1Mbps).",
        "Botão 'Salvar' não responde após editar campo de descrição por mais de 5 minutos.",
        "Relatório PDF gerado contém caracteres corrompidos em nomes com acentos.",
        "Notificações por email estão sendo duplicadas para usuários com múltiplas roles.",
        "Aplicação crasha ao tentar preview de imagem HEIC no Safari 15.",
        "Dados de cache não invalidam após atualização de perfil, mostrando informação stale.",
        "Search retorna resultados inconsistentes quando query contém hífens.",
        "Exportação para Excel falha silenciosamente quando dados contêm fórmulas.",
        "WebSocket connection dropa após exatamente 60 segundos de inatividade.",
    ]
    
    MONITORING_ALERTS = [
        "[CRITICAL] Service payment-gateway latency p99 > 10s for 5min",
        "[WARNING] Disk usage on /var/log at 92%, expected to reach 95% in 2h",
        "[CRITICAL] Database replication lag on replica-02: 45 seconds",
        "[INFO] Certificate for api.example.com expires in 30 days",
        "[WARNING] Error rate on /api/v2/orders elevated: 5.2% (threshold: 5%)",
        "[CRITICAL] Load balancer health check failing for 2/5 instances",
        "[WARNING] Memory leak detected in service analytics-worker",
        "[INFO] Scheduled maintenance window starting in 60 minutes",
        "[CRITICAL] 5xx error rate spike: 23% of requests failing",
        "[WARNING] Queue depth on jobs-priority exceeding 1000 messages",
    ]
    
    def __init__(self, categories: list[str] | None = None, config: SourceConfig = None):
        super().__init__(config)
        self.categories = categories or ["logs", "commits", "bugs", "alerts"]
        self.name = "domain_tech"
    
    def fetch(self) -> Iterator[TextSample]:
        """Gera amostras de textos técnicos."""
        all_texts = []
        
        if "logs" in self.categories:
            all_texts.extend(self.LOG_MESSAGES)
        if "commits" in self.categories:
            all_texts.extend(self.COMMIT_MESSAGES)
        if "bugs" in self.categories:
            all_texts.extend(self.BUG_DESCRIPTIONS)
        if "alerts" in self.categories:
            all_texts.extend(self.MONITORING_ALERTS)
        
        # Embaralha para variedade
        random.shuffle(all_texts)
        
        # Limita ao max_samples
        for i, text in enumerate(all_texts[:self.config.max_samples]):
            # Determina a categoria
            category = self._detect_category(text)
            
            sample = TextSample(
                text=text,
                source=self.name,
                metadata={
                    "category": category,
                    "domain": "technology",
                    "language": "pt" if any(c in text for c in "ãõçáéíóú") else "en",
                }
            )
            
            if self.filter_sample(sample):
                yield sample
    
    def _detect_category(self, text: str) -> str:
        """Detecta a categoria do texto técnico."""
        text_lower = text.lower()
        
        if any(level in text for level in ["error", "warn", "info", "debug", "fatal"]):
            return "log"
        elif text.startswith("[") and "]" in text:
            return "alert"
        elif any(prefix in text for prefix in ["fix:", "feat:", "refactor:", "docs:", "test:", "chore:", "perf:", "revert:", "ci:", "security:"]):
            return "commit"
        elif any(word in text_lower for word in ["usuários", "users", "relatório", "report", "crash", "falha", "bug"]):
            return "bug"
        return "general"


class MedicalDomainSource(DataSource):
    """
    Fonte de dados especializada em medicina/saúde.
    
    Fornece textos típicos de:
    - Sintomas e diagnósticos
    - Prescrições
    - Relatórios clínicos
    - Terminologia médica
    
    Nota: Todos os dados são sintéticos/anonymized para treinamento.
    """
    
    SYMPTOMS = [
        "Paciente relata dor torácica intensa, iniciada há 2 horas, irradiada para braço esquerdo.",
        "Febre persistente de 39°C há 3 dias, acompanhada de calafrios e mialgia generalizada.",
        "Dor abdominal em quadrante inferior direito, intensidade 8/10, com náuseas.",
        "Dispneia progressiva ao esforço, tosse seca noturna, ortopneia.",
        "Cefaleia frontal pulsátil, piora com movimentos bruscos, fotofobia.",
    ]
    
    DIAGNOSES = [
        "Diagnóstico: Infarto agudo do miocárdio sem supra ST. Troponina elevada.",
        "Pneumonia comunitária moderada. RX mostra consolidação em lobo inferior direito.",
        "Apendicite aguda complicada. Indicada apendectomia laparoscópica urgente.",
        "Insuficiência cardíaca congestiva classe funcional III NYHA.",
        "Enxaqueca com aura visual. Sem alterações neurológicas objetivas.",
    ]
    
    PRESCRIPTIONS = [
        "Prescrição: AAS 100mg 1x ao dia, Clopidogrel 75mg 1x ao dia, Atorvastatina 40mg HS.",
        "Azitromicina 500mg 1x ao dia por 5 dias. Retornar em 7 dias.",
        "Analgésico: Dipirona 1g a cada 6h se dor. Hidratação oral 2L/dia.",
        "Furosemida 40mg 2x ao dia. Monitorar função renal em 1 semana.",
        "Sumatriptano 50mg via oral no início da crise. Máximo 2 doses/24h.",
    ]
    
    def __init__(self, categories: list[str] | None = None, config: SourceConfig = None):
        super().__init__(config)
        self.categories = categories or ["symptoms", "diagnoses", "prescriptions"]
        self.name = "domain_medical"
    
    def fetch(self) -> Iterator[TextSample]:
        """Gera amostras de textos médicos."""
        all_texts = []
        
        if "symptoms" in self.categories:
            all_texts.extend(self.SYMPTOMS)
        if "diagnoses" in self.categories:
            all_texts.extend(self.DIAGNOSES)
        if "prescriptions" in self.categories:
            all_texts.extend(self.PRESCRIPTIONS)
        
        random.shuffle(all_texts)
        
        for text in all_texts[:self.config.max_samples]:
            sample = TextSample(
                text=text,
                source=self.name,
                metadata={
                    "category": self._detect_medical_category(text),
                    "domain": "medical",
                    "synthetic": True,
                }
            )
            
            if self.filter_sample(sample):
                yield sample
    
    def _detect_medical_category(self, text: str) -> str:
        """Detecta a categoria médica."""
        text_lower = text.lower()
        
        if any(w in text_lower for w in ["dor", "febre", "dispneia", "cefaleia", "náusea", "vômito"]):
            return "symptom"
        elif "diagnóstico" in text_lower or "diagnóstico" in text_lower:
            return "diagnosis"
        elif "prescrição" in text_lower or "mg" in text_lower:
            return "prescription"
        return "clinical_note"


class LegalDomainSource(DataSource):
    """
    Fonte de dados especializada em direito/jurídico.
    
    Fornece textos típicos de:
    - Cláusulas contratuais
    - Petições
    - Legislação
    - Pareceres jurídicos
    """
    
    CONTRACT_CLAUSES = [
        "Cláusula 3ª: O CONTRATADO se obriga a prestar os serviços de consultoria "
        "especializada conforme escopo definido no Anexo A, com dedicação exclusiva "
        "durante o prazo contratual.",
        
        "Cláusula 7ª - Da Confidencialidade: As partes se comprometem a manter "
        "estrito sigilo sobre todas as informações técnicas, comerciais e financeiras "
        "a que tiverem acesso em razão da execução deste contrato.",
        
        "Art. 5º O presente contrato poderá ser rescindido por qualquer das partes "
        "mediante notificação prévia de 30 (trinta) dias, sem prejuízo das obrigações "
        "já constituídas até a data da rescisão.",
    ]
    
    LEGAL_PETITIONS = [
        "Vem o autor à presença de Vossa Excelência propor a presente AÇÃO DE "
        "INDENIZAÇÃO POR DANOS MORAIS E MATERIAIS em face do réu, pelos fatos "
        "e fundamentos a seguir expostos.",
        
        "Diante do exposto, requer a concessão de tutela de urgência para suspender "
        "os efeitos do ato administrativo impugnado, até decisão final deste processo.",
        
        "Posto isso, requer-se o julgamento procedente do pedido para condenar o "
        "réu ao pagamento de indenização por danos morais no valor de R$ 50.000,00.",
    ]
    
    LEGAL_OPINIONS = [
        "PARECER JURÍDICO Nº 123/2024: Analisando a controvérsia posta, entendo "
        "que há prescrição intercorrente nos termos do art. 1.074 do CPC/2015, "
        "devendo o processo ser extinto sem resolução de mérito.",
        
        "EMENTA: Agravo de instrumento. Contrato de franquia. Descumprimento de "
        "cláusula de não-competição. Danos materiais comprovados. Recurso improvido.",
    ]
    
    def __init__(self, categories: list[str] | None = None, config: SourceConfig = None):
        super().__init__(config)
        self.categories = categories or ["contracts", "petitions", "opinions"]
        self.name = "domain_legal"
    
    def fetch(self) -> Iterator[TextSample]:
        """Gera amostras de textos jurídicos."""
        all_texts = []
        
        if "contracts" in self.categories:
            all_texts.extend(self.CONTRACT_CLAUSES)
        if "petitions" in self.categories:
            all_texts.extend(self.LEGAL_PETITIONS)
        if "opinions" in self.categories:
            all_texts.extend(self.LEGAL_OPINIONS)
        
        random.shuffle(all_texts)
        
        for text in all_texts[:self.config.max_samples]:
            sample = TextSample(
                text=text,
                source=self.name,
                metadata={
                    "category": self._detect_legal_category(text),
                    "domain": "legal",
                    "formal": True,
                }
            )
            
            if self.filter_sample(sample):
                yield sample
    
    def _detect_legal_category(self, text: str) -> str:
        """Detecta a categoria jurídica."""
        text_lower = text.lower()
        
        if "cláusula" in text_lower or "art." in text_lower or "contratado" in text_lower:
            return "contract"
        elif "ação" in text_lower or "requer" in text_lower or "requer-se" in text_lower:
            return "petition"
        elif "parecer" in text_lower or "ementa" in text_lower:
            return "opinion"
        return "legal_text"
