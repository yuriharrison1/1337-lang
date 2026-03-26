"""Validation for 1337 messages (R1-R21)."""

from typing import Optional
from leet.types import Msg1337, Intent, Payload, RawRole, FIXED_DIMS


def validate(msg: Msg1337) -> Optional[str]:
    """
    Valida MSG_1337 contra R1-R21.
    Retorna None se ok, string de erro se inválido.
    """
    validators = [
        _r1_single_intent,
        _r2_delta_ref,
        _r4_no_cycles,
        _r6_urgency,
        _r8_broadcast,
        _r9_evidence_coherence,
        _r10_vector_dims,
    ]
    
    for validator in validators:
        result = validator(msg)
        if result is not None:
            return result
    
    return None


def check_confidence(msg: Msg1337) -> list[tuple[str, int, float]]:
    """
    Retorna flags de baixa confiança (cogon_id, dim_index, unc_value).
    """
    warnings = []
    threshold = 0.9
    
    def check_cogon(cogon, cogon_id):
        for i, u in enumerate(cogon.unc):
            if u > threshold:
                warnings.append((cogon_id, i, u))
    
    if isinstance(msg.payload, Payload):
        payload = msg.payload
    else:
        payload = msg.payload
        
    if hasattr(payload, 'sem'):  # Cogon
        check_cogon(payload, payload.id)
    elif hasattr(payload, 'nodes'):  # Dag
        for node in payload.nodes:
            check_cogon(node, node.id)
    
    return warnings


def _r1_single_intent(msg: Msg1337) -> Optional[str]:
    """R1: Todo MSG_1337 tem exatamente um intent."""
    # Sempre verdadeiro devido ao enum
    return None


def _r2_delta_ref(msg: Msg1337) -> Optional[str]:
    """R2: intent=DELTA exige ref+patch. intent≠DELTA proíbe patch."""
    intent = msg.intent
    is_delta = intent == Intent.DELTA if isinstance(intent, Intent) else intent == "DELTA"
    
    if is_delta:
        if msg.ref_hash is None or msg.patch is None:
            return "R2: DELTA intent requires ref_hash and patch"
    else:
        if msg.patch is not None:
            return "R2: Non-DELTA intent must not have patch"
    
    return None


def _r4_no_cycles(msg: Msg1337) -> Optional[str]:
    """R4: DAG sem ciclos."""
    from leet.types import Dag
    
    payload = msg.payload
    if isinstance(payload, Dag):
        try:
            payload.topological_order()
        except ValueError as e:
            return f"R4: {e}"
    
    return None


def _r6_urgency(msg: Msg1337) -> Optional[str]:
    """R6: human_required=true exige urgency declarado."""
    if msg.surface.human_required and msg.surface.urgency is None:
        return "R6: human_required=true requires urgency"
    return None


def _r8_broadcast(msg: Msg1337) -> Optional[str]:
    """R8: BROADCAST só para ANOMALY ou SYNC."""
    if msg.receiver.is_broadcast():
        intent = msg.intent
        allowed = {Intent.ANOMALY, Intent.SYNC, "ANOMALY", "SYNC"}
        if intent not in allowed:
            return f"R8: BROADCAST only allowed with ANOMALY or SYNC intents, got {intent}"
    return None


def _r9_evidence_coherence(msg: Msg1337) -> Optional[str]:
    """R9: RAW com EVIDENCE deve ter sem não-zero."""
    def check_cogon(cogon):
        if cogon.raw and cogon.raw.role == RawRole.EVIDENCE:
            if all(s < 0.01 for s in cogon.sem):
                return "R9: RAW EVIDENCE requires non-zero sem"
        return None
    
    from leet.types import Dag
    payload = msg.payload
    if isinstance(payload, Dag):
        for node in payload.nodes:
            result = check_cogon(node)
            if result:
                return result
    else:
        return check_cogon(payload)
    
    return None


def _r10_vector_dims(msg: Msg1337) -> Optional[str]:
    """R10: VECTOR[32] indexado por posição fixa."""
    def check_cogon(cogon):
        if len(cogon.sem) != FIXED_DIMS:
            return f"R10: sem has {len(cogon.sem)} dims, expected {FIXED_DIMS}"
        if len(cogon.unc) != FIXED_DIMS:
            return f"R10: unc has {len(cogon.unc)} dims, expected {FIXED_DIMS}"
        return None
    
    from leet.types import Dag
    payload = msg.payload
    if isinstance(payload, Dag):
        for node in payload.nodes:
            result = check_cogon(node)
            if result:
                return result
    else:
        return check_cogon(payload)
    
    return None
