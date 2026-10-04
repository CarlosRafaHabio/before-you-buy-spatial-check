"""F2/F3/F5 regressions against the real host admission API."""
from copy import copy, deepcopy
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import pickle
import subprocess
import sys
from threading import Barrier
import unittest

from spatial_check import evaluate
from spatial_check.contracts import RESULT_SCHEMA, validate
from spatial_check.engine import CONFLICT, NO_CONFLICT, UNVERIFIED
from spatial_check.trust import HostIntake, LifecycleRegistry, TrustError, claim_from_data
from spatial_check.units import InputError, decimal_value, normalize
from tests.helpers import base, change

ROOT = Path(__file__).resolve().parents[1]


def admit(host, evidence, confirmation_ref="event-1"):
    return host.confirm(claim_from_data(evidence), case_id=evidence["case_id"],
                        revision=evidence["revision"], room_identity=evidence["room_identity"],
                        item_identity=evidence["item_identity"], confirmation_ref=confirmation_ref)


class NumericAdmissionTests(unittest.TestCase):
    def check_accepted(self, value, expected_cm, status):
        q, e = base()
        change(e, "rw", value=100)
        change(e, "iw", value=value, unit="mm")
        result = evaluate(q, admit(HostIntake(), e))
        self.assertEqual(result["status"], status)
        self.assertEqual(normalize(value, "mm", "assembled_width"), Decimal(expected_cm))
        self.assertEqual(next(x["value"] for x in result["normalized"]
                              if x["field"] == "item.width"), expected_cm)
        self.assertEqual(validate(result, RESULT_SCHEMA), [])

    def check_ambiguous(self, value):
        q, e = base()
        change(e, "iw", value=value, unit="mm")
        claim = claim_from_data(e)
        with self.assertRaisesRegex(TrustError, "Ambiguous numeric representation") as error:
            admit(HostIntake(), e)
        self.assertIn(repr(value), str(error.exception))
        self.assertEqual(json.loads(claim.payload), e)  # No silent canonicalization.
        self.assertEqual(evaluate(q, claim)["status"], UNVERIFIED)
        with self.assertRaises(InputError):
            decimal_value(value)

    def test_F5_1_dot_200_rejected(self):
        self.check_ambiguous("1.200")

    def test_F5_1_comma_200_rejected(self):
        self.check_ambiguous("1,200")

    def test_F5_1200_mm_conflicts(self):
        self.check_accepted("1200", "120", CONFLICT)

    def test_F5_1_dot_2_mm_remains_decimal(self):
        self.check_accepted("1.2", "0.12", NO_CONFLICT)

    def test_F5_1_comma_2_mm_remains_decimal(self):
        self.check_accepted("1,2", "0.12", NO_CONFLICT)

    def test_F5_small_decimal_remains_exact(self):
        self.check_accepted("0.000001", "0.0000001", NO_CONFLICT)

    def test_other_conventional_single_groups_rejected(self):
        for value in ("12.345", "123,456", "-1.200", "001,200"):
            with self.subTest(value=value):
                self.check_ambiguous(value)

    def test_explicit_decimal_forms_preserved(self):
        for value, expected in (("3.20", "3.2"), ("3,20", "3.2"),
                                ("0.001", "0.001"), ("0,001", "0.001"),
                                ("100.000001", "100.000001")):
            with self.subTest(value=value):
                self.assertEqual(decimal_value(value), Decimal(expected))

    def test_explicit_clarification_requires_new_claim(self):
        q, e = base()
        change(e, "rw", value=100)
        change(e, "iw", value="1.200", unit="mm")
        host = HostIntake()
        with self.assertRaises(TrustError):
            admit(host, e)
        change(e, "iw", value="1200")  # Explicit external clarification, no guessing.
        self.assertEqual(evaluate(q, admit(host, e, "clarified-event"))["status"], CONFLICT)

    def test_failed_ambiguous_revision_does_not_revoke_current(self):
        q, e = base()
        host = HostIntake()
        old = admit(host, e)
        e["revision"] = "r2"
        change(e, "iw", value="1.200")
        with self.assertRaises(TrustError):
            admit(host, e)
        self.assertEqual(evaluate(q, old)["status"], NO_CONFLICT)

    def test_scientific_notation_still_unverified(self):
        q, e = base()
        change(e, "iw", value="1e-7")
        result = evaluate(q, admit(HostIntake(), e))
        self.assertEqual(result["status"], UNVERIFIED)
        self.assertIn("UNUSABLE_EVIDENCE", [x["code"] for x in result["blockers"]])


class LifecycleScopeTests(unittest.TestCase):
    def test_same_host_r1_r2_r1_rejected(self):
        _, e = base()
        host = HostIntake()
        old = deepcopy(e)
        admit(host, e)
        e["revision"] = "r2"
        admit(host, e)
        with self.assertRaises(TrustError):
            admit(host, old)

    def test_same_host_changed_revision_content_rejected(self):
        _, e = base()
        host = HostIntake()
        admit(host, e)
        change(e, "rw", value=250)
        with self.assertRaises(TrustError):
            admit(host, e)

    def test_two_default_hosts_are_explicitly_independent_domains(self):
        q, e = base()
        change(e, "iw", value=280)
        a, b = HostIntake(), HostIntake()
        ra = admit(a, e)
        change(e, "rw", value=250)
        rb = admit(b, e)
        first, second = evaluate(q, ra), evaluate(q, rb)
        self.assertNotEqual(a.domain_id, b.domain_id)
        self.assertNotEqual(first["admission"]["domain_id"], second["admission"]["domain_id"])
        self.assertEqual((first["status"], second["status"]), (NO_CONFLICT, CONFLICT))
        e["revision"] = "r2"
        admit(a, e)
        self.assertEqual(evaluate(q, ra)["status"], UNVERIFIED)
        self.assertEqual(evaluate(q, rb)["status"], CONFLICT)

    def test_shared_registry_refuses_divergent_same_revision(self):
        _, e = base()
        registry = LifecycleRegistry()
        a, b = HostIntake(registry), HostIntake(registry)
        self.assertEqual(a.domain_id, registry.domain_id)
        self.assertEqual(a.domain_id, b.domain_id)
        admit(a, e)
        change(e, "rw", value=250)
        with self.assertRaises(TrustError):
            admit(b, e)

    def test_shared_registry_revision_invalidates_both_hosts(self):
        q, e = base()
        registry = LifecycleRegistry()
        a, b = HostIntake(registry), HostIntake(registry)
        ra, rb = admit(a, e), admit(b, e)
        old = deepcopy(e)
        e["revision"] = "r2"
        admit(a, e)
        for receipt in (ra, rb):
            self.assertEqual(evaluate(q, receipt)["status"], UNVERIFIED)
        with self.assertRaises(TrustError):
            admit(b, old)

    def test_shared_registry_revocation_invalidates_both_hosts(self):
        q, e = base()
        registry = LifecycleRegistry()
        a, b = HostIntake(registry), HostIntake(registry)
        ra, rb = admit(a, e), admit(b, e)
        a.revoke(e["case_id"])
        for receipt in (ra, rb):
            self.assertEqual(evaluate(q, receipt)["status"], UNVERIFIED)

    def test_shared_registry_concurrent_divergent_admissions_are_atomic(self):
        _, e = base()
        other = deepcopy(e)
        change(other, "rw", value=250)
        registry = LifecycleRegistry()
        barrier = Barrier(2)
        def attempt(data):
            host = HostIntake(registry)
            barrier.wait(timeout=5)
            try:
                return admit(host, data)
            except TrustError:
                return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            receipts = list(pool.map(attempt, (e, other)))
        self.assertEqual(sum(r is not None for r in receipts), 1)

    def test_registry_cannot_be_cloned_or_restored(self):
        registry = LifecycleRegistry()
        for operation in (copy, deepcopy, pickle.dumps):
            with self.subTest(operation=operation), self.assertRaises(TypeError):
                operation(registry)
        host = HostIntake(registry)
        for operation in (deepcopy, pickle.dumps):
            with self.subTest(host_operation=operation), self.assertRaises(TypeError):
                operation(host)
        self.assertEqual(copy(host).domain_id, host.domain_id)  # Shallow copy shares authority.
        with self.assertRaises(TypeError):
            HostIntake({"domain_id": registry.domain_id})

    def test_new_process_can_readmit_old_claim_no_persistence(self):
        q, e = base()
        host = HostIntake()
        old = deepcopy(e)
        admit(host, e)
        e["revision"] = "r2"
        admit(host, e)
        with self.assertRaises(TrustError):
            admit(host, old)
        code = '''import json,sys
from spatial_check import evaluate
from spatial_check.trust import HostIntake,claim_from_data
q,e=json.loads(sys.stdin.read())
h=HostIntake()
r=h.confirm(claim_from_data(e),case_id=e['case_id'],revision=e['revision'],
room_identity=e['room_identity'],item_identity=e['item_identity'],confirmation_ref='new-process')
print(json.dumps(evaluate(q,r)))
'''
        run = subprocess.run([sys.executable, "-B", "-c", code], input=json.dumps([q, old]),
                             cwd=ROOT, text=True, capture_output=True, check=True)
        self.assertEqual(json.loads(run.stdout)["status"], NO_CONFLICT)


class AdmissionTraceTests(unittest.TestCase):
    def test_shared_registry_receipt_sequence_spans_hosts(self):
        q, e = base()
        registry = LifecycleRegistry()
        a = evaluate(q, admit(HostIntake(registry), e))
        b = evaluate(q, admit(HostIntake(registry), e))
        self.assertEqual(a["admission"]["domain_id"], b["admission"]["domain_id"])
        self.assertNotEqual(a["admission"]["receipt_id"], b["admission"]["receipt_id"])

    def test_same_content_different_confirmation_events_distinguishable(self):
        q, e = base()
        host = HostIntake()
        a, b = evaluate(q, admit(host, e, "event-A")), evaluate(q, admit(host, e, "event-B"))
        self.assertNotEqual(a["admission"]["receipt_id"], b["admission"]["receipt_id"])
        self.assertEqual(a["admission"]["confirmation_ref"], "event-A")
        self.assertEqual(b["admission"]["confirmation_ref"], "event-B")
        self.assertEqual(a["input_digest"], b["input_digest"])
        self.assertEqual(a["admission"]["evidence_digest"], b["admission"]["evidence_digest"])
        self.assertEqual({k: v for k, v in a.items() if k != "admission"},
                         {k: v for k, v in b.items() if k != "admission"})

    def test_repeated_confirmation_ref_is_not_receipt_identity(self):
        q, e = base()
        host = HostIntake()
        a, b = evaluate(q, admit(host, e)), evaluate(q, admit(host, e))
        self.assertEqual(a["admission"]["confirmation_ref"], b["admission"]["confirmation_ref"])
        self.assertNotEqual(a["admission"]["receipt_id"], b["admission"]["receipt_id"])

    def test_authoritative_scope_and_digests(self):
        q, e = base()
        result = evaluate(q, admit(HostIntake(), e))
        canonical = json.dumps(e, sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        combined = json.dumps([q, e], sort_keys=True, ensure_ascii=True, allow_nan=False, separators=(",", ":"))
        self.assertEqual(result["admission"]["evidence_digest"], hashlib.sha256(canonical.encode()).hexdigest())
        self.assertEqual(result["input_digest"], hashlib.sha256(combined.encode()).hexdigest())
        for key in ("case_id", "revision", "room_identity", "item_identity"):
            self.assertEqual(result["admission"][key], e[key])
        self.assertEqual(validate(result, RESULT_SCHEMA), [])

    def test_request_cannot_override_admission(self):
        q, e = base()
        receipt = admit(HostIntake(), e, "real-event")
        q["admission"] = {"confirmation_ref": "forged-event"}
        result = evaluate(q, receipt)
        self.assertEqual(result["status"], UNVERIFIED)
        self.assertEqual(result["admission"]["confirmation_ref"], "real-event")
        self.assertEqual(validate(result, RESULT_SCHEMA), [])

    def test_raw_input_cannot_supply_admission(self):
        q, e = base()
        e["admission"] = {"receipt_id": "forged"}
        result = evaluate(q, e)
        self.assertIsNone(result["admission"])
        self.assertEqual(result["status"], UNVERIFIED)

    def test_returned_admission_mutation_cannot_change_issuer_record(self):
        q, e = base()
        receipt = admit(HostIntake(), e, "real-event")
        first = evaluate(q, receipt)
        first["admission"]["confirmation_ref"] = "forged-event"
        self.assertEqual(evaluate(q, receipt)["admission"]["confirmation_ref"], "real-event")

    def test_same_receipt_full_result_remains_deterministic(self):
        q, e = base()
        receipt = admit(HostIntake(), e)
        first = evaluate(q, receipt)
        for _ in range(30):
            self.assertEqual(evaluate(q, receipt), first)

    def test_revoked_receipt_does_not_report_current_admission(self):
        q, e = base()
        host = HostIntake()
        receipt = admit(host, e)
        host.revoke(e["case_id"])
        result = evaluate(q, receipt)
        self.assertEqual(result["status"], UNVERIFIED)
        self.assertIsNone(result["admission"])
