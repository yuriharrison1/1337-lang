"""Semantic operators for 1337."""

import math
from typing import Optional
from leet.types import Cogon, FIXED_DIMS


def blend(c1: Cogon, c2: Cogon, alpha: float) -> Cogon:
    """
    Fusão semântica interpolada.
    
    sem = α·c1.sem + (1-α)·c2.sem
    unc = max(c1.unc, c2.unc)  # incerteza conservadora
    """
    sem = [alpha * s1 + (1 - alpha) * s2 
           for s1, s2 in zip(c1.sem, c2.sem)]
    unc = [max(u1, u2) for u1, u2 in zip(c1.unc, c2.unc)]
    return Cogon.new(sem=sem, unc=unc)


def delta(prev: Cogon, curr: Cogon) -> list[float]:
    """Diferença semântica entre dois estados (ponto a ponto)."""
    return [c - p for p, c in zip(prev.sem, curr.sem)]


def dist(c1: Cogon, c2: Cogon) -> float:
    """
    Distância cosseno ponderada por (1-unc).
    
    Dimensões incertas (unc alta) pesam menos.
    Retorna valor entre 0 (idênticos) e 1 (ortogonais/opostos).
    """
    # Peso = 1 - max(unc_a, unc_b)
    weights = [1 - max(u1, u2) for u1, u2 in zip(c1.unc, c2.unc)]
    
    # Produto interno ponderado
    dot = sum(w * s1 * s2 for w, s1, s2 in zip(weights, c1.sem, c2.sem))
    
    # Normas ponderadas
    norm1 = math.sqrt(sum(w * s * s for w, s in zip(weights, c1.sem)))
    norm2 = math.sqrt(sum(w * s * s for w, s in zip(weights, c2.sem)))
    
    if norm1 == 0 or norm2 == 0:
        return 1.0  # máxima distância se um é zero
    
    cosine = dot / (norm1 * norm2)
    # Clamp para evitar erros numéricos
    cosine = max(-1.0, min(1.0, cosine))
    
    # Retorna 1 - similaridade (distância)
    return 1.0 - cosine


def focus(cogon: Cogon, dims: list[int]) -> Cogon:
    """
    Projeta COGON em subconjunto de dimensões.
    
    Dimensões selecionadas mantêm valores.
    Dimensões não-selecionadas: sem=0, unc=1.0 (máxima incerteza)
    """
    dim_set = set(dims)
    sem = [s if i in dim_set else 0.0 for i, s in enumerate(cogon.sem)]
    unc = [u if i in dim_set else 1.0 for i, u in enumerate(cogon.unc)]
    return Cogon.new(sem=sem, unc=unc)


def anomaly_score(cogon: Cogon, history: list[Cogon]) -> float:
    """
    Distância média do centroide histórico.
    
    Retorna 1.0 se histórico vazio.
    """
    if not history:
        return 1.0
    
    # Calcula centroide
    n = len(history)
    centroid_sem = [sum(h.sem[i] for h in history) / n for i in range(FIXED_DIMS)]
    centroid_unc = [sum(h.unc[i] for h in history) / n for i in range(FIXED_DIMS)]
    
    centroid = Cogon.new(sem=centroid_sem, unc=centroid_unc)
    
    # Distância do cogon ao centroide
    return dist(cogon, centroid)


def apply_patch(base: Cogon, patch: list[float]) -> Cogon:
    """
    Aplica delta patch clamped [0,1].
    
    sem_result[i] = clamp(base.sem[i] + patch[i], 0, 1)
    """
    sem = [max(0.0, min(1.0, s + p)) for s, p in zip(base.sem, patch)]
    return Cogon.new(sem=sem, unc=base.unc.copy())
