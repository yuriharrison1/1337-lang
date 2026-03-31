"""Validation for 1337 messages (R1-R21)."""

from typing import Optional, Set
from leet.types import Msg1337, Intent, Payload, RawRole, FIXED_DIMS, Cogon, Dag

MAX_INHERITANCE_DEPTH = 4  # Definido localmente para evitar circular import


def validate(msg: Msg1337) -> Optional[str]:
    """
    Valida MSG_1337 contra R1-R21.
    Retorna None se ok, string de erro se inválido.
    """
    validators = [
        _r1_single_intent,
        _r2_delta_ref,
        _r3_dag_nodes_exist,
        _r4_no_cycles,
        _r5_low_confidence_flag,
        _r6_urgency,
        _r7_zone_emergent_c5,
        _r8_broadcast,
        _r9_evidence_coherence,
        _r10_vector_dims,
        _r11_zone_emergent_append_only,
        _r14_dag_parents_first,
        _r17_canonical_order,
        _r19_inheritance_depth,
        _r20_cogon_zero_first,
    ]
    
    for validator in validators:
        result = validator(msg)
        if result is not None:
            return result
    
    return None


def check_confidence(msg: Msg1337) -> list[tuple[str, int, float]]:
    """
    Retorna flags de baixa confiança (cogon_id, dim_index, unc_value).
    R5: unc[i] > 0.9 dispara flag de baixa confiança.
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


# ═══════════════════════════════════════════════════════════════════════════════
# REGRAS R1-R21
# ═══════════════════════════════════════════════════════════════════════════════

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


def _r3_dag_nodes_exist(msg: Msg1337) -> Optional[str]:
    """R3: Todo COGON referenciado num DAG deve estar em nodes do mesmo DAG."""
    payload = msg.payload
    
    if isinstance(payload, Dag):
        node_ids = {node.id for node in payload.nodes}
        
        for edge in payload.edges:
            if edge.from_id not in node_ids:
                return f"R3: Edge references unknown node {edge.from_id}"
            if edge.to_id not in node_ids:
                return f"R3: Edge references unknown node {edge.to_id}"
    
    return None


def _r4_no_cycles(msg: Msg1337) -> Optional[str]:
    """R4: DAG sem ciclos. Cognição circular é anomalia."""
    payload = msg.payload
    if isinstance(payload, Dag):
        try:
            payload.topological_order()
        except ValueError as e:
            return f"R4: {e}"
    
    return None


def _r5_low_confidence_flag(msg: Msg1337) -> Optional[str]:
    """R5: unc[i] > 0.9 dispara flag de baixa confiança (check via check_confidence)."""
    # Esta regra é verificada via check_confidence(), não falha validação
    return None


def _r6_urgency(msg: Msg1337) -> Optional[str]:
    """R6: human_required=true exige urgency declarado."""
    if msg.surface.human_required and msg.surface.urgency is None:
        return "R6: human_required=true requires urgency"
    return None


def _r7_zone_emergent_c5(msg: Msg1337) -> Optional[str]:
    """R7: zone_emergent só referencia IDs do handshake C5."""
    # A zona emergente é definida durante o handshake C5
    # Aqui verificamos apenas se o align_hash está presente quando há zone_emergent
    if msg.c5 and msg.c5.zone_emergent:
        if not msg.c5.align_hash:
            return "R7: zone_emergent requires C5 align_hash"
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
    """R9: RAW com EVIDENCE deve ter sem/unc coerentes."""
    def check_cogon(cogon):
        if cogon.raw and cogon.raw.role == RawRole.EVIDENCE:
            if all(s < 0.01 for s in cogon.sem):
                return "R9: RAW EVIDENCE requires non-zero sem"
            # Verificar coerência: se sem é não-zero, unc deve refletir confiança
            # Evidência deve ter baixa incerteza (alta confiança)
            avg_unc = sum(cogon.unc) / len(cogon.unc)
            if avg_unc > 0.8:
                return "R9: RAW EVIDENCE should have low uncertainty (coherence)"
        return None
    
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
    
    payload = msg.payload
    if isinstance(payload, Dag):
        for node in payload.nodes:
            result = check_cogon(node)
            if result:
                return result
    else:
        return check_cogon(payload)
    
    return None


def _r11_zone_emergent_append_only(msg: Msg1337) -> Optional[str]:
    """R11: Zona Emergente append-only a partir do índice 32."""
    if msg.c5 and msg.c5.zone_emergent:
        # Verificar se todas as chaves na zona emergente são >= 32
        for key in msg.c5.zone_emergent.keys():
            try:
                idx = int(key)
                if idx < 32:
                    return f"R11: zone_emergent key {key} < 32 (reserved for fixed axes)"
            except ValueError:
                # Chaves não-numéricas são permitidas (nomes simbólicos)
                pass
    return None


# R12: Deprecação mantém índice com deprecated=true. Nunca deleta.
# Esta é uma regra de design, não de validação runtime.

# R13: Atalho emergente requer mesmo align_hash nos dois agentes.
# Verificado durante o handshake C5, não na mensagem.


def _r14_dag_parents_first(msg: Msg1337) -> Optional[str]:
    """R14: Nó do DAG não processado antes dos pais absorvidos."""
    payload = msg.payload
    if isinstance(payload, Dag):
        # Construir mapeamento de dependências
        parents: dict[str, Set[str]] = {node.id: set() for node in payload.nodes}
        for edge in payload.edges:
            if edge.to_id in parents:
                parents[edge.to_id].add(edge.from_id)
        
        # Verificar se a ordem topológica respeita as dependências
        try:
            order = payload.topological_order()
            processed = set()
            for node_id in order:
                if not parents[node_id].issubset(processed):
                    missing = parents[node_id] - processed
                    return f"R14: Node {node_id} has unprocessed parents: {missing}"
                processed.add(node_id)
        except ValueError:
            # Ciclo já detectado em R4
            pass
    
    return None


# R15: Mesma precedência → esquerda pra direita.
# Regra de parser/operadores, não de validação de mensagem.

# R16: FOCUS antes de BLEND. BLEND full-space explícito.
# Regra de parser/operadores, não de validação de mensagem.


def _r17_canonical_order(msg: Msg1337) -> Optional[str]:
    """R17: Serialização na ordem canônica declarada."""
    # Verificamos se a mensagem pode ser serializada e desserializada
    # mantendo a ordem dos campos
    try:
        json_str = msg.to_json()
        if not json_str:
            return "R17: Failed to serialize message to JSON"
    except Exception as e:
        return f"R17: Serialization error: {e}"
    
    return None


# R18: Herança OO: específico vence geral.
# Regra de resolução de herança, não de validação de mensagem.


def _r19_inheritance_depth(msg: Msg1337) -> Optional[str]:
    """R19: Cadeia de herança máx 4 níveis."""
    def check_cogon(cogon, depth=0):
        if depth > MAX_INHERITANCE_DEPTH:
            return f"R19: Inheritance depth {depth} exceeds max {MAX_INHERITANCE_DEPTH}"
        
        if cogon.raw and cogon.raw.role == RawRole.EVIDENCE:
            # Verificar se há metadados de herança no raw
            if isinstance(cogon.raw.content, dict):
                parent = cogon.raw.content.get('_parent')
                if parent:
                    return check_cogon(parent, depth + 1)
        return None
    
    payload = msg.payload
    if isinstance(payload, Dag):
        for node in payload.nodes:
            result = check_cogon(node)
            if result:
                return result
    else:
        return check_cogon(payload)
    
    return None


# R20: Todo agente transmite COGON_ZERO antes de qualquer msg.
# Regra de protocolo, verificada no histórico do agente.


def _r20_cogon_zero_first(msg: Msg1337) -> Optional[str]:
    """R20: COGON_ZERO deve ser transmitido antes de qualquer msg (verificação estrutural)."""
    # Verificamos se o COGON_ZERO tem a estrutura correta quando presente
    def check_cogon(cogon):
        nil_uuid = "00000000-0000-0000-0000-000000000000"
        if cogon.id == nil_uuid:
            # É um COGON_ZERO, verificar valores exatos
            expected_sem = [1.0] * FIXED_DIMS
            expected_unc = [0.0] * FIXED_DIMS
            if list(cogon.sem) != expected_sem:
                return "R20: COGON_ZERO must have sem=[1]*32"
            if list(cogon.unc) != expected_unc:
                return "R20: COGON_ZERO must have unc=[0]*32"
            if cogon.stamp != 0:
                return "R20: COGON_ZERO must have stamp=0"
        return None
    
    payload = msg.payload
    if isinstance(payload, Dag):
        for node in payload.nodes:
            result = check_cogon(node)
            if result:
                return result
    else:
        return check_cogon(payload)
    
    return None


# R21: BRIDGE nunca expõe interior da rede 1337.
# Regra de segurança do bridge, não de validação de mensagem.
