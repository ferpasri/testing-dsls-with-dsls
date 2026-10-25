"""Record miniTESTAR testing information while delegating its original steps."""
from functools import wraps

from TESTARsteps import TESTARSteps
from miniTESTAR import testar
from playwright_backend import PlaywrightBackend
from testar_evidence import Oracle
from testar_evidence_playwright import AvailableAction
from testar_evidence_playwright.sync_api import evidence_for


class EvidenceRecordingSteps:
    def __init__(self, steps):
        self.steps = steps
        self._available_descriptions = None

    @property
    def performance(self):
        return self.steps.performance

    @property
    def actionable_element_count(self):
        return self.steps.actionable_element_count

    def begin_sequence(self, url):
        self._available_descriptions = None
        self.steps.begin_sequence(url)

    def derive_actions(self):
        descriptions = self.steps.derive_actions()
        self.record_available_actions(descriptions)
        return descriptions

    def select_action(self, possible_actions):
        # A skipped target can remove choices before the loop selects again.
        if possible_actions != self._available_descriptions:
            self.record_available_actions(possible_actions)
        return self.steps.select_action(possible_actions)

    def execute_action(self, action, value=None):
        result = self.steps.execute_action(action, value=value)
        if result.status == 'execution_skipped' and self._available_descriptions is not None:
            # EVIDENCE - available actions: retain the loop's reduced list after a skipped target.
            self.record_available_actions([
                description for description in self._available_descriptions
                if description['selector'] != action['selector']
            ])
        return result

    def check_oracles(self, findings, sequence, attempt):
        original_oracles = self.steps.oracles
        self.steps.oracles = [self._recording_oracle(oracle) for oracle in original_oracles]
        try:
            # Keep TESTARSteps' original finding handling and interactive error pause.
            return self.steps.check_oracles(findings, sequence, attempt)
        finally:
            self.steps.oracles = original_oracles

    def end_sequence(self):
        self.steps.end_sequence()

    def _available_action(self, description):
        return AvailableAction(description['kind'], 'miniTESTAR ' + description['kind'],
                               self.steps.session.page.locator(description['selector']),
                               description['parameters'])

    def record_available_actions(self, descriptions):
        # EVIDENCE - available actions: retain eligible choices, including unexecuted ones.
        # These passed selection filters; reachability is still checked before execution.
        recorder = evidence_for(self.steps.session.page)
        recorder.record_available_actions(
            [self._available_action(description) for description in descriptions], scope='eligible')
        # Keep the tool's available-action list separate from automatically recorded browser operations.
        recorder.capture()
        self._available_descriptions = list(descriptions)

    def _recording_oracle(self, oracle):
        @wraps(oracle)
        def check(page):
            try:
                result = oracle(page)
            except AssertionError as error:
                self._record_oracle_failure(oracle, 'failed', error)
                raise
            except Exception as error:
                self._record_oracle_failure(oracle, 'error', error)
                raise
            self.record_oracle_result(oracle, 'passed', None)
            return result
        return check

    def _record_oracle_failure(self, oracle, status, error):
        try:
            self.record_oracle_result(oracle, status, error)
        except Exception as recording_error:
            error.add_note('Evidence recording also failed: ' + str(recording_error))

    def record_oracle_result(self, oracle, status, error):
        recorder = evidence_for(self.steps.session.page)
        # EVIDENCE - oracle outcome: record this callback's result without running it again.
        # Generic callbacks target the observation, without claiming widget-property coverage.
        recorder.capture()
        identity = getattr(oracle, '__module__', '') + '.' + getattr(oracle, '__qualname__', type(oracle).__name__)
        recorder.checks.record_result(Oracle('minitestar:oracle:' + identity),
                                      getattr(oracle, '__name__', type(oracle).__name__), status,
                                      None if error is None else str(error))


def testar_with_evidence(url, num_runs, length_sequence, filter_elements, preparations, oracles,
                         *, backend=None, measure_timings=False, max_failures=5):
    # EVIDENCE - integration entry point: keep the original TESTAR loop and wrap its steps.
    if backend is None:
        backend = PlaywrightBackend()
    steps = EvidenceRecordingSteps(TESTARSteps(backend=backend, filters=filter_elements,
                                              preparations=preparations, oracles=oracles))
    return testar(url, num_runs, length_sequence, filter_elements, preparations, oracles,
                  backend=backend, measure_timings=measure_timings, max_failures=max_failures,
                  steps=steps)
