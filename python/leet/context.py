"""
Context-Aware Projection for 1337.

Este módulo implementa ajuste de projeção semântica baseado em contexto
de conversação, permitindo que o sistema adapte as projeções conforme
o domínio e histórico da interação.

O contexto é representado como um COGON acumulativo que enfatiza ou
atenua certos eixos semânticos baseado no histórico recente.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Optional, Callable
from collections import deque

from leet.types import Cogon, FIXED_DIMS
from leet.operators import blend, dist
from leet.axes import (
    CANONICAL_AXES, AxisGroup,
    A0_VIA, A1_CORRESPONDENCIA, A2_VIBRACAO, A3_POLARIDADE,
    A4_RITMO, A5_CAUSA_EFEITO, A6_GENERO, A7_SISTEMA,
    A8_ESTADO, A9_PROCESSO, A10_RELACAO, A11_SINAL,
    A12_ESTABILIDADE, A13_VALENCIA_ONTOLOGICA,
    B1_VERIFICABILIDADE, B2_TEMPORALIDADE, B3_COMPLETUDE,
    B4_CAUSALIDADE, B5_REVERSIBILIDADE, B6_CARGA,
    B7_ORIGEM, B8_VALENCIA_EPISTEMICA,
    C1_URGENCIA, C2_IMPACTO, C3_ACAO, C4_VALOR,
    C5_ANOMALIA, C6_AFETO, C7_DEPENDENCIA, C8_VETOR_TEMPORAL,
    C9_NATUREZA, C10_VALENCIA_ACAO,
)


@dataclass
class ContextProfile:
    """
    Perfil de contexto que representa um domínio ou estado conversacional.
    
    Um perfil enfatiza certos eixos semânticos e atenua outros,
    criando uma "lente" através da qual textos são projetados.
    """
    name: str
    description: str
    # Vetor de ajuste para cada eixo (0.5 = neutro, >0.5 = enfatizar, <0.5 = atenuar)
    axis_weights: list[float] = field(default_factory=lambda: [0.5] * FIXED_DIMS)
    # Temperatura da projeção (quanto maior, mais extremos os valores)
    temperature: float = 1.0
    # Eixos que são especialmente relevantes neste contexto
    dominant_axes: list[int] = field(default_factory=list)
    # Metadata
    created_at: float = field(default_factory=time.time)
    usage_count: int = 0
    
    def __post_init__(self):
        if len(self.axis_weights) != FIXED_DIMS:
            raise ValueError(f"axis_weights must have {FIXED_DIMS} elements")
        self.axis_weights = [max(0.0, min(1.0, w)) for w in self.axis_weights]
        self.temperature = max(0.1, min(2.0, self.temperature))
    
    def to_cogon(self) -> Cogon:
        """Converte este perfil em um COGON de ajuste."""
        # sem = pesos ajustados para ficar em [0, 1]
        sem = [0.5 + (w - 0.5) * self.temperature for w in self.axis_weights]
        # unc = menor para eixos dominantes (mais confiança)
        unc = [0.3 if i in self.dominant_axes else 0.5 for i in range(FIXED_DIMS)]
        return Cogon.new(sem=sem, unc=unc)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "axis_weights": self.axis_weights,
            "temperature": self.temperature,
            "dominant_axes": self.dominant_axes,
            "created_at": self.created_at,
            "usage_count": self.usage_count,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> ContextProfile:
        return cls(
            name=d["name"],
            description=d["description"],
            axis_weights=d.get("axis_weights", [0.5] * FIXED_DIMS),
            temperature=d.get("temperature", 1.0),
            dominant_axes=d.get("dominant_axes", []),
            created_at=d.get("created_at", time.time()),
            usage_count=d.get("usage_count", 0),
        )


class ContextManager:
    """
    Gerenciador de contexto para projeções 1337.
    
    Mantém um histórico de COGONs recentes e computa um contexto acumulado
    que pode ser usado para ajustar novas projeções.
    """
    
    # Perfis de contexto pré-definidos para domínios comuns
    BUILTIN_PROFILES: dict[str, ContextProfile] = {
        "technical": ContextProfile(
            name="technical",
            description="Contexto técnico/engineering - foco em sistemas, processos, estados",
            axis_weights=[
                0.5, 0.5, 0.4, 0.5,  # A0-A3: neutro
                0.5, 0.7, 0.6, 0.9,  # A4-A7: sistema, causalidade ativa
                0.9, 0.9, 0.7, 0.8,  # A8-A11: estado, processo, sinal
                0.6, 0.5,            # A12-A13: estabilidade moderada
                0.8, 0.6, 0.7, 0.8,  # B1-B4: verificável, causal
                0.7, 0.6, 0.8, 0.6,  # B5-B8: reversibilidade, origem observada
                0.5, 0.8, 0.7, 0.5,  # C1-C4: impacto alto, ação
                0.7, 0.4, 0.8, 0.5,  # C5-C8: anomalia detectável, dependência
                0.5, 0.5,            # C9-C10: neutro
            ],
            temperature=1.1,
            dominant_axes=[A7_SISTEMA, A8_ESTADO, A9_PROCESSO, B1_VERIFICABILIDADE, C2_IMPACTO],
        ),
        
        "emergency": ContextProfile(
            name="emergency",
            description="Contexto de emergência/crise - urgência, anomalia, ação",
            axis_weights=[
                0.6, 0.5, 0.8, 0.7,  # A0-A3: vibração alta (mudança)
                0.6, 0.9, 0.8, 0.7,  # A4-A7: causalidade ativa
                0.9, 0.9, 0.6, 0.9,  # A8-A11: estado crítico, sinal
                0.2, 0.3,            # A12-A13: instabilidade, valência negativa
                0.7, 0.9, 0.9, 0.8,  # B1-B4: verificável, temporal, completo
                0.4, 0.9, 0.9, 0.2,  # B5-B8: irreversível, carga alta, evidência negativa
                1.0, 1.0, 1.0, 0.9,  # C1-C4: urgência máxima, impacto, ação
                1.0, 0.9, 0.7, 0.9,  # C5-C10: anomalia máxima, afeto, futuro
                0.8, 0.2,            # C9-C10: ação/verbo, alerta
            ],
            temperature=1.3,
            dominant_axes=[C1_URGENCIA, C2_IMPACTO, C3_ACAO, C5_ANOMALIA, A9_PROCESSO],
        ),
        
        "philosophical": ContextProfile(
            name="philosophical",
            description="Contexto filosófico/conceitual - abstração, correspondência, natureza",
            axis_weights=[
                0.9, 0.9, 0.7, 0.8,  # A0-A3: via alta, correspondência, polaridade
                0.6, 0.6, 0.7, 0.8,  # A4-A7: ritmo, causalidade, sistema
                0.5, 0.6, 0.8, 0.7,  # A8-A11: relação, sinal alto
                0.5, 0.5,            # A12-A13: estabilidade neutra
                0.4, 0.3, 0.3, 0.4,  # B1-B4: menos verificável, temporal difuso
                0.5, 0.8, 0.4, 0.5,  # B5-B8: carga cognitiva alta, origem inferida
                0.2, 0.3, 0.4, 0.8,  # C1-C4: sem urgência, alto valor
                0.3, 0.5, 0.6, 0.5,  # C5-C8: sem anomalia
                0.3, 0.5,            # C9-C10: substantivo/estado
            ],
            temperature=0.9,
            dominant_axes=[A0_VIA, A1_CORRESPONDENCIA, A10_RELACAO, C4_VALOR],
        ),
        
        "planning": ContextProfile(
            name="planning",
            description="Contexto de planejamento - futuro, processo, reversibilidade",
            axis_weights=[
                0.5, 0.6, 0.6, 0.5,  # A0-A3: neutro
                0.7, 0.8, 0.7, 0.8,  # A4-A7: ritmo, causalidade ativa, sistema
                0.5, 0.9, 0.7, 0.6,  # A8-A11: processo alto, relação
                0.6, 0.7,            # A12-A13: estabilidade, valência positiva
                0.6, 0.8, 0.4, 0.7,  # B1-B4: temporal definido, causalidade
                0.9, 0.7, 0.6, 0.7,  # B5-B8: alta reversibilidade (planos mudam)
                0.5, 0.6, 0.8, 0.7,  # C1-C4: ação alta, valor
                0.3, 0.4, 0.5, 1.0,  # C5-C8: sem anomalia, vetor temporal = futuro
                0.7, 0.8,            # C9-C10: verbo/ação, intenção positiva
            ],
            temperature=1.0,
            dominant_axes=[A9_PROCESSO, B5_REVERSIBILIDADE, C3_ACAO, C8_VETOR_TEMPORAL],
        ),
        
        "social": ContextProfile(
            name="social",
            description="Contexto social/interpessoal - afeto, relação, comunicação",
            axis_weights=[
                0.5, 0.5, 0.6, 0.5,  # A0-A3: neutro
                0.5, 0.5, 0.6, 0.7,  # A4-A7: gênero ativo, sistema social
                0.5, 0.5, 0.9, 0.8,  # A8-A11: relação alta, sinal
                0.5, 0.6,            # A12-A13: neutro, levemente positivo
                0.4, 0.5, 0.4, 0.4,  # B1-B4: subjetivo
                0.5, 0.5, 0.4, 0.5,  # B5-B8: inferido
                0.3, 0.4, 0.5, 0.8,  # C1-C4: sem urgência, alto valor pessoal
                0.2, 0.9, 0.6, 0.5,  # C5-C10: baixa anomalia, alto afeto
                0.4, 0.6,            # C9-C10: neutro
            ],
            temperature=0.95,
            dominant_axes=[A10_RELACAO, A11_SINAL, C4_VALOR, C6_AFETO],
        ),
    }
    
    def __init__(self, window_size: int = 10, decay_factor: float = 0.8):
        """
        Args:
            window_size: Número de COGONs recentes a manter no histórico
            decay_factor: Fator de decaimento para COGONs antigos (0-1)
        """
        self.window_size = window_size
        self.decay_factor = decay_factor
        self.history: deque[Cogon] = deque(maxlen=window_size)
        self.current_profile: Optional[ContextProfile] = None
        self.custom_profiles: dict[str, ContextProfile] = {}
        self._context_cogon: Optional[Cogon] = None
        self._last_update: float = 0
    
    def set_profile(self, profile_name: str) -> ContextProfile:
        """Define o perfil de contexto ativo."""
        if profile_name in self.BUILTIN_PROFILES:
            self.current_profile = self.BUILTIN_PROFILES[profile_name]
        elif profile_name in self.custom_profiles:
            self.current_profile = self.custom_profiles[profile_name]
        else:
            raise ValueError(f"Perfil '{profile_name}' não encontrado. "
                           f"Disponíveis: {list(self.BUILTIN_PROFILES.keys()) + list(self.custom_profiles.keys())}")
        
        self.current_profile.usage_count += 1
        self._invalidate_cache()
        return self.current_profile
    
    def add_to_history(self, cogon: Cogon) -> None:
        """Adiciona um COGON ao histórico de contexto."""
        self.history.append(cogon)
        self._invalidate_cache()
    
    def get_context_cogon(self, alpha: float = 0.3) -> Optional[Cogon]:
        """
        Computa o COGON de contexto atual.
        
        Este COGON representa o "estado mental" acumulado da conversa
        e pode ser usado para ajustar novas projeções via BLEND.
        
        Args:
            alpha: Peso do contexto ao fazer blend (0 = ignorar contexto, 1 = só contexto)
        
        Returns:
            COGON representando o contexto acumulado, ou None se não há histórico
        """
        # Verifica cache
        if self._context_cogon is not None:
            return self._context_cogon
        
        if not self.history and self.current_profile is None:
            return None
        
        # Começa com o perfil atual se houver
        if self.current_profile is not None:
            base = self.current_profile.to_cogon()
        else:
            # Começa com COGON neutro
            base = Cogon.new(sem=[0.5] * FIXED_DIMS, unc=[0.5] * FIXED_DIMS)
        
        # Incorpora histórico com decaimento
        if self.history:
            weights = [self.decay_factor ** i for i in range(len(self.history))]
            total_weight = sum(weights)
            
            # Computa média ponderada dos sem/unc do histórico
            hist_sem = [0.0] * FIXED_DIMS
            hist_unc = [0.0] * FIXED_DIMS
            
            for i, cogon in enumerate(reversed(self.history)):
                w = weights[i] / total_weight
                for j in range(FIXED_DIMS):
                    hist_sem[j] += cogon.sem[j] * w
                    hist_unc[j] += cogon.unc[j] * w
            
            hist_cogon = Cogon.new(sem=hist_sem, unc=hist_unc)
            
            # BLEND entre perfil e histórico
            base = blend(base, hist_cogon, alpha=0.5)
        
        self._context_cogon = base
        self._last_update = time.time()
        return base
    
    def adjust_projection(
        self,
        sem: list[float],
        unc: list[float],
        context_alpha: float = 0.2,
    ) -> tuple[list[float], list[float]]:
        """
        Ajusta uma projeção baseada no contexto atual.
        
        Args:
            sem: Vetor semântico original (32 dims)
            unc: Vetor de incerteza original (32 dims)
            context_alpha: Quanto misturar o contexto (0-1)
        
        Returns:
            (sem_ajustado, unc_ajustado)
        """
        context_cogon = self.get_context_cogon()
        if context_cogon is None or context_alpha <= 0:
            return sem, unc
        
        # Cria COGON da projeção original
        original = Cogon.new(sem=sem, unc=unc)
        
        # BLEND com contexto
        adjusted = blend(original, context_cogon, alpha=1 - context_alpha)
        
        return adjusted.sem, adjusted.unc
    
    def detect_context_drift(self, threshold: float = 0.5) -> Optional[str]:
        """
        Detecta se o contexto mudou significativamente.
        
        Compara o COGON mais recente com o contexto acumulado.
        Se a distância for alta, sugere mudança de contexto.
        
        Returns:
            Mensagem descrevendo a drift detectada, ou None
        """
        if len(self.history) < 2:
            return None
        
        recent = self.history[-1]
        context = self.get_context_cogon()
        if context is None:
            return None
        
        distance = dist(recent, context)
        if distance > threshold:
            return f"Context drift detected: distance={distance:.3f} > {threshold}"
        return None
    
    def auto_select_profile(self, sample_text: str, project_fn: Callable[[str], tuple[list[float], list[float]]]) -> ContextProfile:
        """
        Seleciona automaticamente o perfil mais adequado para um texto.
        
        Args:
            sample_text: Texto amostra para análise
            project_fn: Função de projeção (texto -> (sem, unc))
        
        Returns:
            Perfil mais adequado
        """
        sem, unc = project_fn(sample_text)
        sample_cogon = Cogon.new(sem=sem, unc=unc)
        
        best_profile = None
        best_score = float('inf')
        
        all_profiles = {**self.BUILTIN_PROFILES, **self.custom_profiles}
        
        for name, profile in all_profiles.items():
            profile_cogon = profile.to_cogon()
            distance = dist(sample_cogon, profile_cogon)
            if distance < best_score:
                best_score = distance
                best_profile = profile
        
        return best_profile
    
    def create_custom_profile(
        self,
        name: str,
        description: str,
        sample_texts: list[str],
        project_fn: Callable[[str], tuple[list[float], list[float]]],
        temperature: float = 1.0,
    ) -> ContextProfile:
        """
        Cria um perfil de contexto customizado baseado em textos de exemplo.
        
        Args:
            name: Nome do perfil
            description: Descrição
            sample_texts: Textos representativos do domínio
            project_fn: Função de projeção
            temperature: Temperatura da projeção
        
        Returns:
            Novo perfil criado
        """
        if len(sample_texts) == 0:
            raise ValueError("Pelo menos um texto de exemplo é necessário")
        
        # Projeta todos os textos
        cogons = []
        for text in sample_texts:
            sem, unc = project_fn(text)
            cogons.append(Cogon.new(sem=sem, unc=unc))
        
        # Computa média
        avg_sem = [0.0] * FIXED_DIMS
        for cogon in cogons:
            for i in range(FIXED_DIMS):
                avg_sem[i] += cogon.sem[i] / len(cogons)
        
        # Converte para pesos (inverso: sem alto -> peso alto)
        axis_weights = [min(1.0, max(0.0, s)) for s in avg_sem]
        
        # Eixos dominantes = top 5
        dominant = sorted(range(FIXED_DIMS), key=lambda i: avg_sem[i], reverse=True)[:5]
        
        profile = ContextProfile(
            name=name,
            description=description,
            axis_weights=axis_weights,
            temperature=temperature,
            dominant_axes=dominant,
        )
        
        self.custom_profiles[name] = profile
        return profile
    
    def export_profile(self, name: str, path: str) -> None:
        """Exporta um perfil para JSON."""
        if name in self.BUILTIN_PROFILES:
            profile = self.BUILTIN_PROFILES[name]
        elif name in self.custom_profiles:
            profile = self.custom_profiles[name]
        else:
            raise ValueError(f"Perfil '{name}' não encontrado")
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)
    
    def import_profile(self, path: str) -> ContextProfile:
        """Importa um perfil de JSON."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        profile = ContextProfile.from_dict(data)
        self.custom_profiles[profile.name] = profile
        return profile
    
    def get_stats(self) -> dict:
        """Retorna estatísticas do contexto atual."""
        return {
            "history_size": len(self.history),
            "window_size": self.window_size,
            "current_profile": self.current_profile.name if self.current_profile else None,
            "custom_profiles": list(self.custom_profiles.keys()),
            "available_profiles": list(self.BUILTIN_PROFILES.keys()),
            "context_drift": self.detect_context_drift(),
        }
    
    def _invalidate_cache(self) -> None:
        """Invalida o cache do contexto."""
        self._context_cogon = None


# Instância global para uso conveniente
_default_manager: Optional[ContextManager] = None


def get_context_manager() -> ContextManager:
    """Retorna o gerenciador de contexto padrão (singleton)."""
    global _default_manager
    if _default_manager is None:
        _default_manager = ContextManager()
    return _default_manager


def set_context_profile(profile_name: str) -> ContextProfile:
    """Define o perfil de contexto ativo globalmente."""
    return get_context_manager().set_profile(profile_name)


def adjust_with_context(
    sem: list[float],
    unc: list[float],
    context_alpha: float = 0.2,
) -> tuple[list[float], list[float]]:
    """Ajusta uma projeção usando o contexto global."""
    return get_context_manager().adjust_projection(sem, unc, context_alpha)
