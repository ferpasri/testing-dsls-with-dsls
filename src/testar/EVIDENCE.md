# Intermediate evidence integration

The basic Playwright facade already captures pages, executed browser operations, and their outcomes. The intermediate integration adds available actions, links executions to those available actions, records compound actions as single executions, and records oracle callback outcomes. The demo entry points use `testar_with_evidence(...)`, which wraps the original `TESTARSteps` in `EvidenceRecordingSteps`. Search for `# EVIDENCE` in `evidence_steps.py` to find the recording points. The TESTAR loop delegates to the wrapper through its existing `steps=` argument.

## 1. Available actions: what could be selected

The wrapper's `record_available_actions(...)` method converts miniTESTAR's discovered action descriptions into `AvailableAction` values and passes them to the adapter's method of the same name. The evidence retains the list, including unselected available actions, their planning parameters, and widget bindings when available.

The list has scope `eligible`: it contains the available actions miniTESTAR offers to its selection process after applying its selectors and filters. Reachability is checked after selection. If a target is skipped, the wrapper records the reduced available-action list before the next selection.

## 2. Execution links and compound actions

The default facade already records browser operations and their outcomes. The wrapper uses `perform(..., available_action=...)` to connect an execution to an available action reported by miniTESTAR.

A **compound action** is one miniTESTAR action made up of several browser operations. For example, on the ParaBank login page, typing `john` into the Username field and then pressing Enter can form one compound action. The integration records one execution for that compound action, linked to the selected available action. The browser operations inside it do not create separate execution records.

`capture()` captures the resulting recorded state and buffers its observation for writing to the trace. Generated input, such as `john`, is recorded when supplied to the operation; password values are redacted by the adapter.

## 3. Oracle outcomes: what was checked and what the oracle reported

The wrapper decorates the callbacks and delegates to the original `TESTARSteps.check_oracles(...)`, which runs each callback once and retains its finding/error handling. `record_oracle_result(...)` then captures the page and records whether the callback passed, failed, or encountered an error, including its reported error when present.

An ordinary callback does not identify individual checked widgets or properties. Its summary therefore targets the observation and has an unknown observed value. An oracle using the facade's `expect` can additionally record detailed native checks. Explicit expected values, observed values, and widget/property targets can be supplied through `evidence_for(page).checks.evaluate(...)`.

The backend has a generic `action_runner` hook that delegates actual operations after reachability checks and input generation. The wrapper installs its compound-action recorder there; the backend contains no intermediate evidence-recording logic.

The facade continues to record preparation operations and manages the trace start, end, and required identifiers.

See the [package installation instructions](packages/README.md). The facade writes traces under its default `target/traces` directory.
