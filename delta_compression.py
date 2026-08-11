#!/usr/bin/env python3
"""
1337 - Optimized Delta Compression
Sends only what changed between messages, drastically reducing traffic.
"""

import json
import math
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from collections import defaultdict

from net1337 import Cogon, FIXED_DIMS, py_dist


def py_apply_patch(base: Cogon, patch: list[float]) -> Cogon:
    """Applies a delta patch, clamped to [0,1]."""
    sem = [max(0.0, min(1.0, s + p)) for s, p in zip(base.sem, patch)]
    return Cogon.new(sem=sem, unc=base.unc.copy())


@dataclass
class DeltaMetrics:
    """Delta compression metrics."""

    # Counters
    total_messages: int = 0
    delta_messages: int = 0
    full_messages: int = 0

    # Savings
    bytes_full: int = 0  # If everything were FULL
    bytes_delta: int = 0  # With delta compression

    # Efficiency
    avg_delta_size: float = 0.0  # Average delta size
    compression_ratio: float = 0.0  # Compression ratio

    # Per axis
    axis_changes: Dict[int, int] = field(default_factory=lambda: defaultdict(int))

    def update(self, is_delta: bool, full_size: int, delta_size: int = 0):
        """Updates metrics after a message."""
        self.total_messages += 1

        if is_delta:
            self.delta_messages += 1
            self.bytes_delta += delta_size
            self.bytes_full += full_size  # For comparison
        else:
            self.full_messages += 1
            self.bytes_delta += full_size
            self.bytes_full += full_size

    def get_savings(self) -> Dict:
        """Computes bandwidth savings."""
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
    Delta Compressor for 1337.

    Strategy:
    1. Compare the current COGON with a reference (previous or baseline)
    2. If change < threshold, send DELTA
    3. If change >= threshold or timeout, send FULL
    """

    def __init__(self, threshold: float = 0.3, max_delta_chain: int = 5):
        """
        Args:
            threshold: Minimum difference to use DELTA (0.0-1.0)
            max_delta_chain: Maximum chained deltas before falling back to FULL
        """
        self.threshold = threshold
        self.max_delta_chain = max_delta_chain
        self.metrics = DeltaMetrics()

        # Cache: agent_id -> last full COGON
        self.baselines: Dict[str, Cogon] = {}

        # Chained-delta counter
        self.delta_chains: Dict[str, int] = defaultdict(int)

    def compute_delta(self, current: Cogon, reference: Cogon) -> List[float]:
        """
        Computes the delta vector: what needs to change in the reference to reach current.

        Delta[i] = current.sem[i] - reference.sem[i]
        """
        return [c - r for c, r in zip(current.sem, reference.sem)]

    def apply_delta(self, reference: Cogon, delta: List[float]) -> Cogon:
        """
        Applies the delta to the reference to reconstruct current.
        """
        new_sem = [max(0.0, min(1.0, r + d)) for r, d in zip(reference.sem, delta)]
        return Cogon.new(sem=new_sem, unc=reference.unc.copy())

    def should_use_delta(self, current: Cogon, reference: Cogon, agent_id: str) -> Tuple[bool, float]:
        """
        Decides whether to use DELTA or FULL.

        Returns:
            (use_delta, distance)
        """
        # Compute distance
        distance = py_dist(current, reference)

        # If the change is small enough, use DELTA
        if distance < self.threshold:
            # Check the delta chain
            if self.delta_chains[agent_id] < self.max_delta_chain:
                return True, distance

        # Reset the chain if falling back to FULL
        self.delta_chains[agent_id] = 0
        return False, distance

    def compress(self, agent_id: str, current: Cogon) -> Dict:
        """
        Compresses a COGON using delta whenever possible.

        Returns:
            {
                "type": "FULL" | "DELTA",
                "payload": Cogon | List[float],
                "ref_id": str | None,  # ID of the reference COGON
                "distance": float,
                "savings_bytes": int
            }
        """
        # Check whether a baseline exists
        if agent_id not in self.baselines:
            # First message: FULL
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

            # Count significant per-axis changes
            for i, d in enumerate(delta):
                if abs(d) > 0.05:  # Significant-change threshold
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
            # FULL - update the baseline
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
        Reconstructs a COGON from a compressed payload.
        """
        if compressed["type"] == "FULL":
            cogon = compressed["payload"]
            self.baselines[agent_id] = cogon  # Update the baseline
            return cogon
        else:
            # DELTA
            delta = compressed["payload"]
            reference = self.baselines.get(agent_id)

            if reference is None:
                raise ValueError(f"No baseline for agent {agent_id}")

            current = self.apply_delta(reference, delta)
            return current

    def _estimate_size(self, cogon: Cogon) -> int:
        """Estimates the byte size of a COGON."""
        # JSON serialization estimate
        data = {
            "id": cogon.id,
            "sem": cogon.sem,  # 32 floats
            "unc": cogon.unc,  # 32 floats
            "stamp": cogon.stamp
        }
        return len(json.dumps(data))

    def _estimate_delta_size(self, delta: List[float]) -> int:
        """Estimates the delta size."""
        # Delta: only non-zero values, or all of them?
        # Optimization: send only indices where |delta| > epsilon
        significant = [(i, d) for i, d in enumerate(delta) if abs(d) > 0.01]

        if not significant:
            return 10  # Minimum: empty header

        # Format: {"indices": [...], "values": [...]}
        data = {
            "indices": [i for i, _ in significant],
            "values": [round(d, 4) for _, d in significant]
        }
        return len(json.dumps(data))

    def get_report(self) -> Dict:
        """Generates a full compression report."""
        savings = self.metrics.get_savings()

        # Top axes that change the most
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
    """Network with smart delta compression."""

    def __init__(self, base_network, compressor: DeltaCompressor):
        self.network = base_network
        self.compressor = compressor
        self.message_log: List[Dict] = []

    def send_message(self, agent_id: str, cogon: Cogon, text: str = "") -> Dict:
        """Sends a message with delta compression."""
        # Compress
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
        """Receives and decompresses a message."""
        return self.compressor.decompress(agent_id, compressed)

    def simulate_conversation(self, agent_cogons: List[Tuple[str, Cogon, str]]):
        """
        Simulates a conversation with delta compression.

        Args:
            agent_cogons: List of (agent_id, cogon, text)
        """
        print("\n" + "=" * 70)
        print("   📦 SIMULATION WITH DELTA COMPRESSION")
        print("=" * 70)
        print(f"\nConfig: threshold={self.compressor.threshold}, "
              f"max_chain={self.compressor.max_delta_chain}")
        print()

        for i, (agent_id, cogon, text) in enumerate(agent_cogons):
            compressed = self.send_message(agent_id, cogon, text)

            # Display
            msg_type = compressed["type"]
            dist = compressed["distance"]
            savings = compressed["savings_bytes"]

            icon = "Δ" if msg_type == "DELTA" else "◆"
            color = "🟢" if msg_type == "DELTA" else "🔵"

            print(f"[{i+1:2}] {color} {icon} {agent_id:15} | "
                  f"{msg_type:5} | dist={dist:.3f} | saved={savings:4}b")

            if text:
                print(f"     \"{text[:60]}{'...' if len(text) > 60 else ''}\"")

        # Report
        print("\n" + "=" * 70)
        print("   📊 COMPRESSION REPORT")
        print("=" * 70)

        report = self.compressor.get_report()

        print(f"\nSummary:")
        print(f"  Total messages: {report['summary']['total_messages']}")
        print(f"  DELTA: {report['summary']['delta_messages']} "
              f"({report['summary']['delta_percentage']}%)")
        print(f"  FULL:  {report['summary']['full_messages']}")

        print(f"\nSavings:")
        print(f"  Bytes saved: {report['savings']['bytes_saved']:,}")
        print(f"  Percentage: {report['savings']['percent_saved']}%")
        print(f"  Compression ratio: {report['savings']['efficiency']}:1")

        print(f"\nMost-changing axes:")
        for axis_info in report['top_changing_axes']:
            axis_name = self._get_axis_name(axis_info['axis'])
            print(f"  [{axis_info['axis']:2}] {axis_name:20} {axis_info['changes']:3} changes")

    def _get_axis_name(self, idx: int) -> str:
        """Returns the axis name."""
        axes_names = [
            "PATH", "CORRESPONDENCE", "VIBRATION", "POLARITY", "RHYTHM",
            "CAUSE_EFFECT", "GENUS", "SYSTEM", "STATE", "PROCESS",
            "RELATION", "SIGNAL", "STABILITY", "ONTOLOGICAL_VALENCE",
            "VERIFIABILITY", "TEMPORALITY", "COMPLETENESS", "CAUSALITY",
            "REVERSIBILITY", "CHARGE", "ORIGIN", "EPISTEMIC_VALENCE",
            "URGENCY", "IMPACT", "ACTION", "VALUE", "ANOMALY",
            "AFFECT", "DEPENDENCY", "TEMPORAL_VECTOR", "NATURE", "ACTION_VALENCE"
        ]
        return axes_names[idx] if idx < len(axes_names) else f"AXIS_{idx}"


# ═══════════════════════════════════════════════════════════════════════════════
# DEMONSTRATION
# ═══════════════════════════════════════════════════════════════════════════════

def demo_delta_compression():
    """Demonstrates delta compression with simulated data."""

    print("=" * 70)
    print("   🧪 DEMONSTRATION: 1337 Delta Compression")
    print("=" * 70)

    # Create the compressor
    compressor = DeltaCompressor(threshold=0.3, max_delta_chain=5)
    network = SmartDeltaNetwork(None, compressor)

    # Simulate a conversation between agents
    # Each agent keeps refining its position on "Eros"

    messages = []

    # Socrates - initial position
    s1 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    s1.sem[0] = 0.8   # high PATH
    s1.sem[22] = 0.6  # medium URGENCY
    messages.append(("Socrates", s1, "Eros is the pursuit of Beauty itself"))

    # Socrates - refinement (small change = DELTA)
    s2 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    s2.sem[0] = 0.85  # PATH slightly higher
    s2.sem[22] = 0.65 # URGENCY rose
    messages.append(("Socrates", s2, "Refining: Eros seeks what it lacks"))

    # Socrates - another refinement (DELTA)
    s3 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    s3.sem[0] = 0.9
    s3.sem[22] = 0.7
    s3.sem[13] = 0.8  # ONTOLOGICAL VALENCE
    messages.append(("Socrates", s3, "Eros is a daimon, an intermediary"))

    # Aristophanes - different position (FULL, large distance)
    a1 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    a1.sem[2] = 0.9   # high VIBRATION
    a1.sem[10] = 0.8  # RELATION
    a1.sem[22] = 0.9  # high URGENCY
    messages.append(("Aristophanes", a1, "Eros is longing for the sphere!"))

    # Aristophanes - refinement (DELTA)
    a2 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    a2.sem[2] = 0.95
    a2.sem[10] = 0.85
    messages.append(("Aristophanes", a2, "The lost half, Zeus split us apart"))

    # Pinocchio - entry (FULL, completely different)
    p1 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    p1.sem[8] = 0.9   # STATE
    p1.sem[9] = 0.8   # PROCESS
    p1.sem[30] = 0.7  # NATURE
    messages.append(("Pinocchio", p1, "I want to be a real boy!"))

    # Pinocchio - small change (DELTA)
    p2 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    p2.sem[8] = 0.95
    p2.sem[9] = 0.85
    messages.append(("Pinocchio", p2, "My nose grows when I lie..."))

    # Socrates - returns (FULL, long silence)
    s4 = Cogon.new(sem=[0.5]*32, unc=[0.1]*32)
    s4.sem[0] = 0.95  # PATH
    s4.sem[13] = 0.9  # VALENCE
    s4.sem[21] = 0.8  # EPISTEMIC VALENCE
    messages.append(("Socrates", s4, "Returning: Eros is the son of Poros and Penia"))

    # More refinements...
    for i in range(10):
        agent = ["Socrates", "Aristophanes", "Pinocchio"][i % 3]
        base = [0.5]*32

        # Small variations
        base[0] = 0.5 + (i * 0.02)  # PATH increasing
        base[22] = 0.5 + (i * 0.03)  # URGENCY

        c = Cogon.new(sem=base, unc=[0.1]*32)
        messages.append((agent, c, f"Refinement {i+1} on the topic"))

    # Run the simulation
    network.simulate_conversation(messages)

    print("\n" + "=" * 70)
    print("✅ Demonstration complete!")
    print("=" * 70)


if __name__ == "__main__":
    demo_delta_compression()
