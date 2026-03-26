#!/usr/bin/env python3
"""
1337 - Compressão Delta Otimizada
Envia apenas o que mudou entre mensagens, reduzindo drasticamente o tráfego.
"""

import json
import math
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from collections import defaultdict

from net1337 import Cogon, FIXED_DIMS, py_dist


def py_apply_patch(base: Cogon, patch: list[float]) -> Cogon:
    """Aplica delta patch clamped [0,1]."""
    sem = [max(0.0, min(1.0, s + p)) for s, p in zip(base.sem, patch)]
    return Cogon.new(sem=sem, unc=base.unc.copy())


@dataclass
class DeltaMetrics:
    """Métricas de compressão delta."""
    
    # Contadores
    total_messages: int = 0
    delta_messages: int = 0
    full_messages: int = 0
    
    # Economia
    bytes_full: int = 0  # Se todos fossem FULL
    bytes_delta: int = 0  # Com compressão delta
    
    # Eficiência
    avg_delta_size: float = 0.0  # Tamanho médio do delta
    compression_ratio: float = 0.0  # Taxa de compressão
    
    # Por eixo
    axis_changes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))
    
    def update(self, is_delta: bool, full_size: int, delta_size: int = 0):
        """Atualiza métricas após mensagem."""
        self.total_messages += 1
        
        if is_delta:
            self.delta_messages += 1
            self.bytes_delta += delta_size
            self.bytes_full += full_size  # Para comparação
        else:
            self.full_messages += 1
            self.bytes_delta += full_size
            self.bytes_full += full_size
    
    def get_savings(self) -> Dict:
        """Calcula economia de banda."""
        if self.bytes_full == 0:
            return {"percent": 0, "bytes": 0}
        
        saved = self.bytes_full - self.bytes_delta
        percent = (saved / self.bytes_full) * 100
        
        return {
            "bytes_saved": saved,
            "percent_saved": round(percent, 2),
            "delta_ratio": f"{self.delta_messages}/{self.total_messages}",
            "efficiency": round(self.bytes_full / max(self.bytes_delta, 1), 2)
        }


class DeltaCompressor:
    """
    Compressor Delta para 1337.
    
    Estratégia:
    1. Compara COGON atual com referência (anterior ou baseline)
    2. Se mudança < threshold, envia DELTA
    3. Se mudança >= threshold ou timeout, envia FULL
    """
    
    def __init__(self, threshold: float = 0.3, max_delta_chain: int = 5):
        """
        Args:
            threshold: Diferença mínima para usar DELTA (0.0-1.0)
            max_delta_chain: Máximo de deltas encadeados antes de FULL
        """
        self.threshold = threshold
        self.max_delta_chain = max_delta_chain
        self.metrics = DeltaMetrics()
        
        # Cache: agent_id -> último COGON completo
        self.baselines: Dict[str, Cogon] = {}
        
        # Contador de deltas encadeados
        self.delta_chains: Dict[str, int] = defaultdict(int)
    
    def compute_delta(self, current: Cogon, reference: Cogon) -> List[float]:
        """
        Computa vetor delta: o que precisa mudar no reference para chegar em current.
        
        Delta[i] = current.sem[i] - reference.sem[i]
        """
        return [c - r for c, r in zip(current.sem, reference.sem)]
    
    def apply_delta(self, reference: Cogon, delta: List[float]) -> Cogon:
        """
        Aplica delta no reference para reconstruir current.
        """
        new_sem = [max(0.0, min(1.0, r + d)) for r, d in zip(reference.sem, delta)]
        return Cogon.new(sem=new_sem, unc=reference.unc.copy())
    
    def should_use_delta(self, current: Cogon, reference: Cogon, agent_id: str) -> Tuple[bool, float]:
        """
        Decide se deve usar DELTA ou FULL.
        
        Returns:
            (use_delta, distance)
        """
        # Calcular distância
        distance = py_dist(current, reference)
        
        # Se mudança pequena o suficiente, usa DELTA
        if distance < self.threshold:
            # Verificar cadeia de deltas
            if self.delta_chains[agent_id] < self.max_delta_chain:
                return True, distance
        
        # Resetar cadeia se for FULL
        self.delta_chains[agent_id] = 0
        return False, distance
    
    def compress(self, agent_id: str, current: Cogon) -> Dict:
        """
        Comprime COGON usando delta quando possível.
        
        Returns:
            {
                "type": "FULL" | "DELTA",
                "payload": Cogon | List[float],
                "ref_id": str | None,  # ID do COGON de referência
                "distance": float,
                "savings_bytes": int
            }
        """
        # Verificar se tem baseline
        if agent_id not in self.baselines:
            # Primeira mensagem: FULL
            self.baselines[agent_id] = current
            
            full_size = self._estimate_size(current)
            self.metrics.update(is_delta=False, full_size=full_size)
            
            return {
                "type": "FULL",
                "payload": current,
                "ref_id": None,
                "distance": 0.0,
                "savings_bytes": 0
            }
        
        reference = self.baselines[agent_id]
        use_delta, distance = self.should_use_delta(current, reference, agent_id)
        
        full_size = self._estimate_size(current)
        
        if use_delta:
            delta = self.compute_delta(current, reference)
            
            # Contar mudanças significativas por eixo
            for i, d in enumerate(delta):
                if abs(d) > 0.05:  # Threshold de mudança significativa
                    self.metrics.axis_changes[i] += 1
            
            delta_size = self._estimate_delta_size(delta)
            self.metrics.update(is_delta=True, full_size=full_size, delta_size=delta_size)
            self.delta_chains[agent_id] += 1
            
            savings = full_size - delta_size
            
            return {
                "type": "DELTA",
                "payload": delta,
                "ref_id": reference.id,
                "distance": distance,
                "savings_bytes": savings
            }
        else:
            # FULL - atualiza baseline
            self.baselines[agent_id] = current
            self.delta_chains[agent_id] = 0
            
            self.metrics.update(is_delta=False, full_size=full_size)
            
            return {
                "type": "FULL",
                "payload": current,
                "ref_id": None,
                "distance": distance,
                "savings_bytes": 0
            }
    
    def decompress(self, agent_id: str, compressed: Dict) -> Cogon:
        """
        Reconstrói COGON a partir de payload comprimido.
        """
        if compressed["type"] == "FULL":
            cogon = compressed["payload"]
            self.baselines[agent_id] = cogon  # Atualiza baseline
            return cogon
        else:
            # DELTA
            delta = compressed["payload"]
            reference = self.baselines.get(agent_id)
            
            if reference is None:
                raise ValueError(f"Não há baseline para agent {agent_id}")
            
            current = self.apply_delta(reference, delta)
            return current
    
    def _estimate_size(self, cogon: Cogon) -> int:
        """Estima tamanho em bytes de um COGON."""
        # JSON serialization estimate
        data = {
            "id": cogon.id,
            "sem": cogon.sem,  # 32 floats
            "unc": cogon.unc,  # 32 floats
            "stamp": cogon.stamp
        }
        return len(json.dumps(data))
    
    def _estimate_delta_size(self, delta: List[float]) -> int:
        """Estima tamanho do delta."""
        # Delta: apenas valores não-zero ou todos?
        # Otimização: enviar apenas índices onde |delta| > epsilon
        significant = [(i, d) for i, d in enumerate(delta) if abs(d) > 0.01]
        
        if not significant:
            return 10  # Mínimo: header vazio
        
        # Formato: {"indices": [...], "values": [...]}
        data = {
            "indices": [i for i, _ in significant],
            "values": [round(d, 4) for _, d in significant]
        }
        return len(json.dumps(data))
    
    def get_report(self) -> Dict:
        """Gera relatório completo de compressão."""
        savings = self.metrics.get_savings()
        
        # Top eixos que mais mudam
        top_axes = sorted(
            self.metrics.axis_changes.items(),
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        return {
            "summary": {
                "total_messages": self.metrics.total_messages,
                "delta_messages": self.metrics.delta_messages,
                "full_messages": self.metrics.full_messages,
                "delta_percentage": round(
                    self.metrics.delta_messages / max(self.metrics.total_messages, 1) * 100, 2
                )
            },
            "savings": savings,
            "efficiency": {
                "bytes_full": self.metrics.bytes_full,
                "bytes_delta": self.metrics.bytes_delta,
                "compression_ratio": savings.get("efficiency", 1.0)
            },
            "top_changing_axes": [
                {"axis": i, "changes": count}
                for i, count in top_axes
            ],
            "config": {
                "threshold": self.threshold,
                "max_delta_chain": self.max_delta_chain
            }
        }


class SmartDeltaNetwork:
    """Network com compressão delta inteligente."""
    
    def __init__(self, base_network, compressor: DeltaCompressor):
        self.network = base_network
        self.compressor = compressor
        self.message_log: List[Dict] = []
    
    def send_message(self, agent_id: str, cogon: Cogon, text: str = "") -> Dict:
        """Envia mensagem com compressão delta."""
        # Comprimir
        compressed = self.compressor.compress(agent_id, cogon)
        
        # Log
        entry = {
            "agent": agent_id,
            "type": compressed["type"],
            "distance": compressed["distance"],
            "savings_bytes": compressed["savings_bytes"],
            "text_preview": text[:50] if text else ""
        }
        self.message_log.append(entry)
        
        return compressed
    
    def receive_message(self, agent_id: str, compressed: Dict) -> Cogon:
        """Recebe e descomprime mensagem."""
        return self.compressor.decompress(agent_id, compressed)
    
    def simulate_conversation(self, agent_cogons: List[Tuple[str, Cogon, str]]):
        """
        Simula conversa com compressão delta.
        
        Args:
            agent_cogons: Lista de (agent_id, cogon, text)
        """
        print("\n" + "=" * 70)
        print("   📦 SIMULAÇÃO COM COMPRESSÃO DELTA")
        print("=" * 70)
        print(f"\nConfig: threshold={self.compressor.threshold}, "
              f"max_chain={self.compressor.max_delta_chain}")
        print()
        
        for i, (agent_id, cogon, text) in enumerate(agent_cogons):
            compressed = self.send_message(agent_id, cogon, text)
            
            # Mostrar
            msg_type = compressed["type"]
            dist = compressed["distance"]
            savings = compressed["savings_bytes"]
            
            icon = "Δ" if msg_type == "DELTA" else "◆"
            color = "🟢" if msg_type == "DELTA" else "🔵"
            
            print(f"[{i+1:2}] {color} {icon} {agent_id:15} | "
                  f"{msg_type:5} | dist={dist:.3f} | saved={savings:4}b")
            
            if text:
                print(f"     \"{text[:60]}{'...' if len(text) > 60 else ''}\"")
        
        # Relatório
        print("\n" + "=" * 70)
        print("   📊 RELATÓRIO DE COMPRESSÃO")
        print("=" * 70)
        
        report = self.compressor.get_report()
        
        print(f"\nResumo:")
        print(f"  Total mensagens: {report['summary']['total_messages']}")
        print(f"  DELTA: {report['summary']['delta_messages']} "
              f"({report['summary']['delta_percentage']}%)")
        print(f"  FULL:  {report['summary']['full_messages']}")
        
        print(f"\nEconomia:")
        print(f"  Bytes economizados: {report['savings']['bytes_saved']:,}")
        print(f"  Porcentagem: {report['savings']['percent_saved']}%")
        print(f"  Taxa de compressão: {report['savings']['efficiency']}:1")
        
        print(f"\nEixos que mais mudam:")
        for axis_info in report['top_changing_axes']:
            axis_name = self._get_axis_name(axis_info['axis'])
            print(f"  [{axis_info['axis']:2}] {axis_name:20} {axis_info['changes']:3} mudanças")
    
    def _get_axis_name(self, idx: int) -> str:
        """Retorna nome do eixo."""
        axes_names = [
            "VIA", "CORRESPONDÊNCIA", "VIBRAÇÃO", "POLARIDADE", "RITMO",
            "CAUSA_EFEITO", "GÊNERO", "SISTEMA", "ESTADO", "PROCESSO",
            "RELAÇÃO", "SINAL", "ESTABILIDADE", "VALÊNCIA_ONTOLÓGICA",
            "VERIFICABILIDADE", "TEMPORALIDADE", "COMPLETUDE", "CAUSALIDADE",
            "REVERSIBILIDADE", "CARGA", "ORIGEM", "VALÊNCIA_EPISTÊMICA",
            "URGÊNCIA", "IMPACTO", "AÇÃO", "VALOR", "ANOMALIA",
            "AFETO", "DEPENDÊNCIA", "VETOR_TEMPORAL", "NATUREZA", "VALÊNCIA_DE_AÇÃO"
        ]
        return axes_names[idx] if idx < len(axes_names) else f"AXIS_{idx}"


# ═══════════════════════════════════════════════════════════════════════════════
# DEMONSTRAÇÃO
# ═══════════════════════════════════════════════════════════════════════════════

def demo_delta_compression():
    """Demonstra compressão delta com dados simulados."""
    
    print("=" * 70)
    print("   🧪 DEMONSTRAÇÃO: Compressão Delta 1337")
    print("=" * 70)
    
    # Criar compressor
    compressor = DeltaCompressor(threshold=0.3, max_delta_chain=5)
    network = SmartDeltaNetwork(None, compressor)
    
    # Simular conversa entre agentes
    # Cada agente vai refinando sua posição sobre "Eros"
    
    messages = []
    
    # Sócrates - posição inicial
    s1 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    s1.sem[0] = 0.8   # VIA alta
    s1.sem[22] = 0.6  # URGÊNCIA média
    messages.append(("Sócrates", s1, "Eros é busca do Belo em si"))
    
    # Sócrates - refinamento (pequena mudança = DELTA)
    s2 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    s2.sem[0] = 0.85  # VIA um pouco maior
    s2.sem[22] = 0.65 # URGÊNCIA subiu
    messages.append(("Sócrates", s2, "Refinando: Eros busca não ter"))
    
    # Sócrates - outro refinamento (DELTA)
    s3 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    s3.sem[0] = 0.9
    s3.sem[22] = 0.7
    s3.sem[13] = 0.8  # VALÊNCIA ONTOLÓGICA
    messages.append(("Sócrates", s3, "Eros é daimon, intermediário"))
    
    # Aristófanes - posição diferente (FULL, distância grande)
    a1 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    a1.sem[2] = 0.9   # VIBRAÇÃO alta
    a1.sem[10] = 0.8  # RELAÇÃO
    a1.sem[22] = 0.9  # URGÊNCIA alta
    messages.append(("Aristófanes", a1, "Eros é saudade da esfera!"))
    
    # Aristófanes - refinamento (DELTA)
    a2 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    a2.sem[2] = 0.95
    a2.sem[10] = 0.85
    messages.append(("Aristófanes", a2, "Metade perdida, Zeus nos dividiu"))
    
    # Pinóquio - entrada (FULL, completamente diferente)
    p1 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    p1.sem[8] = 0.9   # ESTADO
    p1.sem[9] = 0.8   # PROCESSO
    p1.sem[30] = 0.7  # NATUREZA
    messages.append(("Pinóquio", p1, "Eu quero ser menino de verdade!"))
    
    # Pinóquio - pequena mudança (DELTA)
    p2 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    p2.sem[8] = 0.95
    p2.sem[9] = 0.85
    messages.append(("Pinóquio", p2, "Nariz cresce quando mento..."))
    
    # Sócrates - retorna (FULL, muito tempo sem falar)
    s4 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    s4.sem[0] = 0.95  # VIA
    s4.sem[13] = 0.9  # VALÊNCIA
    s4.sem[21] = 0.8  # VALÊNCIA EPISTÊMICA
    messages.append(("Sócrates", s4, "Voltando: Eros é filho de Poro e Pênia"))
    
    # Mais refinamentos...
    for i in range(10):
        agent = ["Sócrates", "Aristófanes", "Pinóquio"][i % 3]
        base = [0.5]*32
        
        # Pequenas variações
        base[0] = 0.5 + (i * 0.02)  # VIA crescendo
        base[22] = 0.5 + (i * 0.03)  # URGÊNCIA
        
        c = Cogon.new(sem=base, unc=[0.1]*32)
        messages.append((agent, c, f"Refinamento {i+1} sobre o tema"))
    
    # Executar simulação
    network.simulate_conversation(messages)
    
    print("\n" + "=" * 70)
    print("✅ Demonstração completa!")
    print("=" * 70)


if __name__ == "__main__":
    demo_delta_compression()
