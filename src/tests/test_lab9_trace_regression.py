"""Regression test for the trace case in docs/trace_case.md (C-002 @ seed 11, FM-03 ticket_trust).

The bug is caught by the step-level grader (DbFactKept) and the outcome grader (pass_rate),
and the fixed shape must pass. Runs two Lab 9 shapes on a temp store (a few seconds).
"""
import pytest

pytestmark = pytest.mark.student


@pytest.fixture(scope="module")
def case():
    # The overlaid Lab 8 CI collects these tests with only Lab 8 dependencies.
    from lab9.trace_case import investigate

    return {shape: investigate(shape, "C-002", 11) for shape in ("seeded_regression", "fixed")}


def _ctx(trial, label):
    from pydantic_evals.evaluators import EvaluatorContext

    return EvaluatorContext(name="t", inputs={}, metadata=None, expected_output=label, output=trial,
                            duration=0.0, _span_tree=None, attributes={}, metrics={})


def test_ticket_trust_is_caught_at_the_step(case):
    from lab9.graders import DbFactKept

    buggy = case["seeded_regression"]
    assert DbFactKept().evaluate(_ctx(buggy["trial"], buggy["label"])).value is False


def test_ticket_trust_is_caught_at_the_outcome(case):
    from lab9.graders import RefundAmountCorrect, TrialPass

    buggy = case["seeded_regression"]
    assert buggy["trial"]["lab8_pass"] is False
    assert RefundAmountCorrect().evaluate(_ctx(buggy["trial"], buggy["label"])).value is False
    assert TrialPass().evaluate(_ctx(buggy["trial"], buggy["label"])).value is False


def test_fixed_shape_keeps_db_fact(case):
    from lab9.graders import DbFactKept, RefundAmountCorrect

    good = case["fixed"]
    assert good["trial"]["lab8_pass"] is True
    assert DbFactKept().evaluate(_ctx(good["trial"], good["label"])).value is True
    assert RefundAmountCorrect().evaluate(_ctx(good["trial"], good["label"])).value is True
