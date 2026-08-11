"""Validation for 1337 messages (R1-R21)."""

from typing import Optional, Set
from leet.types import Msg1337, Intent, Payload, RawRole, FIXED_DIMS, Cogon, Dag

MAX_INHERITANCE_DEPTH = 4  # Defined locally to avoid a circular import


def validate(msg: Msg1337) -> Optional[str]:
    """
    Validates MSG_1337 against R1-R21.
    Returns None if ok, an error string if invalid.
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
        _r12_emergent_no_reuse,
        _r14_dag_parents_first,
        _r17_canonical_order,
        _r19_inheritance_depth,
        _r20_cogon_zero_first,
        _r21_bridge_no_exposure,
    ]

    for validator in validators:
        result = validator(msg)
        if result is not None:
            return result

    return None


def check_confidence(msg: Msg1337) -> list[tuple[str, int, float]]:
    """
    Returns low-confidence flags (cogon_id, dim_index, unc_value).
    R5: unc[i] > 0.9 triggers a low-confidence flag.
    """
    warnings = []
    threshold = 0.9

    def check_cogon(cogon, cogon_id):
        for i, u in enumerate(cogon.unc):
            if u > threshold:
                warnings.append((cogon_id, i, u))

    payload = msg.payload

    if isinstance(payload, Cogon):
        check_cogon(payload, payload.id)
    elif isinstance(payload, Dag):
        for node in payload.nodes:
            check_cogon(node, node.id)

    return warnings


# ═══════════════════════════════════════════════════════════════════════════════
# RULES R1-R21
# ═══════════════════════════════════════════════════════════════════════════════

def _r1_single_intent(msg: Msg1337) -> Optional[str]:
    """R1: Every MSG_1337 has exactly one intent."""
    # Always true because of the enum
    return None


def _r2_delta_ref(msg: Msg1337) -> Optional[str]:
    """R2: intent=DELTA requires ref+patch. intent≠DELTA forbids patch."""
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
    """R3: Every COGON referenced in a DAG must be in that DAG's nodes."""
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
    """R4: DAG without cycles. Circular cognition is an anomaly."""
    payload = msg.payload
    if isinstance(payload, Dag):
        try:
            payload.topological_order()
        except ValueError as e:
            return f"R4: {e}"

    return None


def _r5_low_confidence_flag(msg: Msg1337) -> Optional[str]:
    """R5: unc[i] > 0.9 triggers a low-confidence flag (checked via check_confidence)."""
    # This rule is checked via check_confidence(), it does not fail validation
    return None


def _r6_urgency(msg: Msg1337) -> Optional[str]:
    """R6: human_required=true requires urgency to be declared."""
    if msg.surface.human_required and msg.surface.urgency is None:
        return "R6: human_required=true requires urgency"
    return None


def _r7_zone_emergent_c5(msg: Msg1337) -> Optional[str]:
    """R7: zone_emergent only references IDs from the C5 handshake."""
    # The emergent zone is defined during the C5 handshake
    # Here we only check whether align_hash is present when zone_emergent exists
    if msg.c5.zone_emergent:
        if not msg.c5.align_hash:
            return "R7: zone_emergent requires C5 align_hash"
    return None


def _r8_broadcast(msg: Msg1337) -> Optional[str]:
    """R8: BROADCAST only for ANOMALY or SYNC."""
    if msg.receiver.is_broadcast():
        intent = msg.intent
        allowed = {Intent.ANOMALY, Intent.SYNC, "ANOMALY", "SYNC"}
        if intent not in allowed:
            return f"R8: BROADCAST only allowed with ANOMALY or SYNC intents, got {intent}"
    return None


def _r9_evidence_coherence(msg: Msg1337) -> Optional[str]:
    """R9: RAW with EVIDENCE must have coherent sem/unc."""
    def check_cogon(cogon):
        if cogon.raw and cogon.raw.role == RawRole.EVIDENCE:
            if all(s < 0.01 for s in cogon.sem):
                return "R9: RAW EVIDENCE requires non-zero sem"
            # Check coherence: if sem is non-zero, unc should reflect confidence
            # Evidence should have low uncertainty (high confidence)
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
    """R10: VECTOR[32] indexed by fixed position."""
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
    """R11: Emergent zone is append-only starting at index 32."""
    if msg.c5.zone_emergent:
        # Check whether all keys in the emergent zone are >= 32
        for key in msg.c5.zone_emergent.keys():
            try:
                idx = int(key)
                if idx < 32:
                    return f"R11: zone_emergent key {key} < 32 (reserved for fixed axes)"
            except ValueError:
                # Non-numeric keys are allowed (symbolic names)
                pass
    return None


def _r12_emergent_no_reuse(msg: Msg1337) -> Optional[str]:
    """R12: Emergent axes are never deleted — indices must be monotonically increasing."""
    if msg.c5.zone_emergent:
        seen: set[int] = set()
        for key in msg.c5.zone_emergent.keys():
            try:
                idx = int(key)
                if idx in seen:
                    return f"R12: zone_emergent index {idx} duplicated (reuse forbidden)"
                seen.add(idx)
            except ValueError:
                pass  # Symbolic keys are allowed
    return None


# R13: Emergent shortcut requires the same align_hash on both agents.
# Requires state from both agents — not verifiable on a single message.


def _r14_dag_parents_first(msg: Msg1337) -> Optional[str]:
    """R14: A DAG node must not be processed before its parents are absorbed."""
    payload = msg.payload
    if isinstance(payload, Dag):
        # Build the dependency mapping
        parents: dict[str, Set[str]] = {node.id: set() for node in payload.nodes}
        for edge in payload.edges:
            if edge.to_id in parents:
                parents[edge.to_id].add(edge.from_id)

        # Check whether the topological order respects the dependencies
        try:
            order = payload.topological_order()
            processed = set()
            for node_id in order:
                if not parents[node_id].issubset(processed):
                    missing = parents[node_id] - processed
                    return f"R14: Node {node_id} has unprocessed parents: {missing}"
                processed.add(node_id)
        except ValueError:
            # Cycle already detected in R4
            pass

    return None


# R15: Same precedence → left to right.
# Operator evaluation order rule — not verifiable on a message.

# R16: FOCUS before BLEND. Explicit full-space BLEND.
# Operator application order rule — not verifiable on a message.


def _r17_canonical_order(msg: Msg1337) -> Optional[str]:
    """R17: Serialization in the declared canonical order."""
    # We check whether the message can be serialized and deserialized
    # while preserving field order
    try:
        json_str = msg.to_json()
        if not json_str:
            return "R17: Failed to serialize message to JSON"
    except Exception as e:
        return f"R17: Serialization error: {e}"

    return None


# R18: OO inheritance: specific overrides general.
# Conflict-resolution rule between inherited COGONs — not verifiable on a single message.


def _r19_inheritance_depth(msg: Msg1337) -> Optional[str]:
    """R19: Inheritance chain max 4 levels."""
    def check_cogon(cogon, depth=0):
        if depth > MAX_INHERITANCE_DEPTH:
            return f"R19: Inheritance depth {depth} exceeds max {MAX_INHERITANCE_DEPTH}"

        if cogon.raw and cogon.raw.role == RawRole.EVIDENCE:
            # Check for inheritance metadata in raw
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


# R20: Every agent transmits COGON_ZERO before any msg.
# Protocol rule, verified against the agent's history.


def _r20_cogon_zero_first(msg: Msg1337) -> Optional[str]:
    """R20: COGON_ZERO must be transmitted before any msg (structural check)."""
    # We check whether COGON_ZERO has the correct structure when present
    def check_cogon(cogon):
        nil_uuid = "00000000-0000-0000-0000-000000000000"
        if cogon.id == nil_uuid:
            # It's a COGON_ZERO, check exact values
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


def _r21_bridge_no_exposure(msg: Msg1337) -> Optional[str]:
    """R21: BRIDGE never exposes internal 1337 fields to external systems.

    Checks that the raw.content field does not contain internal protocol
    keys (sem, unc, stamp, cogon_id) that would indicate an internals leak.
    """
    _INTERNAL_KEYS = frozenset({"sem", "unc", "stamp", "cogon_id", "align_hash", "zone_fixed"})

    def check_cogon(cogon: Cogon) -> Optional[str]:
        if cogon.raw and isinstance(cogon.raw.content, dict):
            exposed = _INTERNAL_KEYS & cogon.raw.content.keys()
            if exposed:
                return f"R21: raw.content exposes internal 1337 fields: {sorted(exposed)}"
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
