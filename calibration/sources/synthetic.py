"""
Synthetic data source via LLM.

Generates training texts using structured prompts
to cover the 32 semantic axes in a balanced way.
"""

import os
import time
import json
from typing import Iterator, Callable

from .base import DataSource, TextSample, SourceConfig


class SyntheticSource(DataSource):
    """
    Generates synthetic texts via LLM for training.

    Uses structured prompts to generate texts that cover
different combinations of the 32 semantic axes.

    Example:
        config = SourceConfig(max_samples=100)
        source = SyntheticSource(
            provider="openai",  # or "anthropic", "mock"
            diversity="high",
            config=config
        )
        samples = source.fetch_all()
    """

    # Prompt templates for different text "types"
    PROMPT_TEMPLATES = [
        {
            "name": "technical_fact",
            "prompt": "Gere um fato técnico conciso sobre {topic}. Uma frase direta.",
            "topics": [
                "sistemas distribuídos", "machine learning", "protocolos de rede",
                "bancos de dados", "segurança cibernética", "compiladores",
                "sistemas operacionais", "algoritmos", "estruturas de dados",
            ]
        },
        {
            "name": "process_description",
            "prompt": "Descreva o processo de {process} em 2-3 frases.",
            "processes": [
                "deploy de aplicação", "backup de dados", "autenticação",
                "compilação de código", "recuperação de desastre",
                "escalação de serviço", "integração contínua",
            ]
        },
        {
            "name": "emergency_alert",
            "prompt": "Gere um alerta de emergência sobre {incident}. Tom urgente.",
            "incidents": [
                "servidor offline", "ataque de segurança", "perda de dados",
                "degradação de performance", "falha de rede", "vazamento de memória",
            ]
        },
        {
            "name": "philosophical_question",
            "prompt": "Faça uma pergunta filosófica sobre {concept}. Formatada como pergunta.",
            "concepts": [
                "consciência artificial", "natureza do tempo", "livre-arbítrio",
                "identidade pessoal", "realidade virtual", "ética tecnológica",
            ]
        },
        {
            "name": "future_prediction",
            "prompt": "Prediga como será {topic} daqui a 10 anos. Uma frase.",
            "topics": [
                "computação quântica", "inteligência artificial", "trabalho remoto",
                "cidades inteligentes", "transporte", "medicina",
            ]
        },
        {
            "name": "past_event",
            "prompt": "Descreva brevemente como era {topic} há 20 anos.",
            "topics": [
                "desenvolvimento de software", "internet", "comunicação",
                "armazenamento de dados", "computação móvel",
            ]
        },
        {
            "name": "uncertainty_statement",
            "prompt": "Faça uma declaração incerta/hipotética sobre {topic}. Use 'talvez', 'pode ser', etc.",
            "topics": [
                "futuro da IA", "causa de um bug", "preferência do usuário",
                "resultado de experimento", "solução de problema",
            ]
        },
        {
            "name": "certainty_statement",
            "prompt": "Faça uma declaração definitiva/factual sobre {topic}. Tom assertivo.",
            "topics": [
                "lei da física", "regra de programação", "fato matemático",
                "propriedade de sistema", "comportamento algoritmo",
            ]
        },
        {
            "name": "emotional_expression",
            "prompt": "Expresse uma emoção sobre {situation}. Tom pessoal.",
            "situations": [
                "conclusão de projeto", "descoberta de bug crítico",
                "apresentação bem-sucedida", "falha de sistema",
            ]
        },
        {
            "name": "action_request",
            "prompt": "Peça para alguém executar {action}. Tom direto.",
            "actions": [
                "revisar código", "reiniciar servidor", "atualizar documentação",
                "investigar erro", "implementar feature", "testar alteração",
            ]
        },
    ]
    
    def __init__(
        self,
        provider: str = "mock",
        diversity: str = "medium",
        language: str = "pt",
        config: SourceConfig = None,
    ):
        super().__init__(config)
        self.provider = provider
        self.diversity = diversity
        self.language = language
        self.name = f"synthetic_{provider}"

        # Configure the generator based on the provider
        self._generator = self._get_generator()

    def _get_generator(self) -> Callable[[str], str]:
        """Returns the appropriate generator function."""
        if self.provider == "mock":
            return self._mock_generate
        elif self.provider == "openai":
            return self._openai_generate
        elif self.provider == "anthropic":
            return self._anthropic_generate
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def fetch(self) -> Iterator[TextSample]:
        """Generates synthetic texts."""
        templates = self.PROMPT_TEMPLATES

        # Determine how many texts to generate per template
        texts_per_template = max(1, self.config.max_samples // len(templates))
        
        for template in templates:
            items = template.get("topics") or template.get("processes") or \
                   template.get("incidents") or template.get("concepts") or \
                   template.get("situations") or template.get("actions")
            
            if not items:
                continue
            
            # Select items for this template
            if self.diversity == "high":
                import random
                selected = random.sample(items, min(texts_per_template, len(items)))
            else:
                selected = items[:texts_per_template]

            for item in selected:
                try:
                    # Build the prompt
                    prompt = template["prompt"].format(topic=item)
                    if self.language != "pt":
                        prompt += f"\n\n(Responda em {self.language})"

                    # Generate the text
                    text = self._generator(prompt)

                    if not text or len(text) < 10:
                        continue

                    sample = TextSample(
                        text=text,
                        source=self.name,
                        metadata={
                            "template": template["name"],
                            "topic": item,
                            "provider": self.provider,
                            # Does not include language, to avoid the filter
                        }
                    )

                    if self.filter_sample(sample):
                        yield sample

                        # Delay between generations
                        time.sleep(self.config.request_delay)

                except Exception:
                    continue

    def _mock_generate(self, prompt: str) -> str:
        """Deterministic mock generation based on the prompt hash."""
        import hashlib

        h = hashlib.sha256(prompt.encode()).hexdigest()

        # Response templates based on the prompt type
        if "fato técnico" in prompt or "technical fact" in prompt:
            facts = [
                "O protocolo TCP garante entrega ordenada de pacotes através de handshake triplo.",
                "Algoritmos de consenso distribuído garantem consistência em sistemas tolerantes a falhas.",
                "A complexidade de tempo do quicksort é O(n log n) no caso médio.",
                "Memória virtual permite que processos usem mais RAM do que fisicamente disponível.",
            ]
        elif "alerta" in prompt or "emergency" in prompt:
            facts = [
                "CRÍTICO: Servidor principal offline. Todos os serviços indisponíveis.",
                "ALERTA: Uso de memória em 98%. Reinício iminente necessário.",
                "URGENTE: Possível vazamento de dados detectado no banco principal.",
            ]
        elif "processo" in prompt or "process" in prompt:
            facts = [
                "O deploy automatizado compila o código, executa testes e promove para produção.",
                "Backup incremental salva apenas alterações desde o último backup completo.",
                "Autenticação multifator requer dois fatores independentes para acesso.",
            ]
        elif "filosófica" in prompt or "philosophical" in prompt:
            facts = [
                "Seria a consciência uma propriedade emergente da complexidade suficiente?",
                "Se uma IA passa no teste de Turing, ela possui mente ou apenas simula uma?",
                "O livre-arbítrio é compatível com um universo governado por leis físicas deterministas?",
            ]
        elif "futuro" in prompt or "future" in prompt:
            facts = [
                "Daqui a 10 anos, desenvolvedores provavelmente programarão principalmente via linguagem natural.",
                "Computação quântica provavelmente revolucionará criptografia e simulação molecular.",
            ]
        elif "incerto" in prompt or "uncertain" in prompt:
            facts = [
                "Talvez o problema de performance esteja relacionado ao garbage collection.",
                "Pode ser que os usuários prefiram a versão simplificada da interface.",
                "É possível que o modelo esteja overfitting para o conjunto de treino.",
            ]
        else:
            facts = [
                "Sistemas complexos exigem abordagens multidisciplinares.",
                "A evolução tecnológica acelera exponencialmente.",
                "Dados bem estruturados são ativos valiosos.",
                "Segurança deve ser projetada desde o início.",
            ]
        
        # Seleciona baseado no hash
        idx = int(h[:8], 16) % len(facts)
        return facts[idx]
    
    def _openai_generate(self, prompt: str) -> str:
        """Generation via the OpenAI API."""
        try:
            import openai

            client = openai.OpenAI(
                api_key=self.config.api_keys.get("openai") or os.environ.get("OPENAI_API_KEY")
            )

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": f"You generate short, varied texts for training. Respond in {self.language}."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.8,
                max_tokens=150,
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"OpenAI generation failed: {e}")
            return self._mock_generate(prompt)
    
    def _anthropic_generate(self, prompt: str) -> str:
        """Generation via the Anthropic API."""
        try:
            import anthropic
            
            client = anthropic.Anthropic(
                api_key=self.config.api_keys.get("anthropic") or os.environ.get("ANTHROPIC_API_KEY")
            )
            
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=150,
                messages=[
                    {"role": "user", "content": f"{prompt}\n\n(Responda em {self.language})"}
                ],
                temperature=0.8,
            )
            
            return response.content[0].text.strip()
            
        except Exception as e:
            print(f"Anthropic generation failed: {e}")
            return self._mock_generate(prompt)
