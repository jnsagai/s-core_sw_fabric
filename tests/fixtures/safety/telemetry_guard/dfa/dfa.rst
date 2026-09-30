Telemetry guard DFA
===================

.. document:: Telemetry guard DFA
   :id: doc__telemetry_guard_dfa
   :status: draft
   :version: 1
   :safety: ASIL_B
   :security: NO
   :realizes: wp__sw_component_dfa

Synthetic increment 008 fixture for the telemetry freshness guard; not S-CORE engineering content.

.. list-table:: DFA communication between elements
   :header-rows: 1

   * - ID
     - Violation cause
     - Applicability
     - Rationale
   * - CO_01_01
     - data flow via arguments or shared variables
     - no
     - Not applicable: guard and monitor share no data flow via arguments or shared variables path in this fixture.
   * - CO_01_02
     - corruption, repetition, loss or delay
     - no
     - Not applicable: guard and monitor share no corruption, repetition, loss or delay path in this fixture.
   * - CO_01_03
     - insertion or sequence
     - no
     - Not applicable: guard and monitor share no insertion or sequence path in this fixture.
   * - CO_01_04
     - corruption or inconsistent data
     - no
     - Not applicable: guard and monitor share no corruption or inconsistent data path in this fixture.
   * - CO_01_05
     - asymmetric information to multiple receivers
     - no
     - Not applicable: guard and monitor share no asymmetric information to multiple receivers path in this fixture.
   * - CO_01_06
     - information received by a subset of receivers
     - no
     - Not applicable: guard and monitor share no information received by a subset of receivers path in this fixture.
   * - CO_01_07
     - blocking access to a channel
     - no
     - Not applicable: guard and monitor share no blocking access to a channel path in this fixture.

.. list-table:: DFA shared information inputs
   :header-rows: 1

   * - ID
     - Violation cause
     - Applicability
     - Rationale
   * - SI_01_02
     - configuration data
     - yes
     - Analysed in comp_saf_dfa__telemetry_guard__shared_time_source.
   * - SI_01_03
     - global constants or variables
     - no
     - Not applicable: guard and monitor share no global constants or variables path in this fixture.
   * - SI_01_04
     - basic software passes data to both functions
     - no
     - Not applicable: guard and monitor share no basic software passes data to both functions path in this fixture.
   * - SI_01_05
     - data delivered to more than one function
     - no
     - Not applicable: guard and monitor share no data delivered to more than one function path in this fixture.

.. list-table:: DFA unintended impact
   :header-rows: 1

   * - ID
     - Violation cause
     - Applicability
     - Rationale
   * - UI_01_01
     - memory misallocation and leaks
     - no
     - Not applicable: guard and monitor share no memory misallocation and leaks path in this fixture.
   * - UI_01_02
     - access to foreign memory
     - no
     - Not applicable: guard and monitor share no access to foreign memory path in this fixture.
   * - UI_01_03
     - stack or buffer overflow
     - no
     - Not applicable: guard and monitor share no stack or buffer overflow path in this fixture.
   * - UI_01_04
     - deadlocks
     - no
     - Not applicable: guard and monitor share no deadlocks path in this fixture.
   * - UI_01_05
     - livelocks
     - no
     - Not applicable: guard and monitor share no livelocks path in this fixture.
   * - UI_01_06
     - blocking of execution
     - no
     - Not applicable: guard and monitor share no blocking of execution path in this fixture.
   * - UI_01_07
     - incorrect execution time allocation
     - no
     - Not applicable: guard and monitor share no incorrect execution time allocation path in this fixture.
   * - UI_01_08
     - incorrect execution flow
     - no
     - Not applicable: guard and monitor share no incorrect execution flow path in this fixture.
   * - UI_01_09
     - incorrect synchronization
     - no
     - Not applicable: guard and monitor share no incorrect synchronization path in this fixture.
   * - UI_01_10
     - CPU time depletion
     - no
     - Not applicable: guard and monitor share no CPU time depletion path in this fixture.
   * - UI_01_11
     - memory depletion
     - no
     - Not applicable: guard and monitor share no memory depletion path in this fixture.
   * - UI_01_12
     - other hardware unavailability
     - no
     - Not applicable: guard and monitor share no other hardware unavailability path in this fixture.

DFA
---

.. comp_saf_dfa:: Shared time source
   :id: comp_saf_dfa__telemetry_guard__shared_time_source
   :violates: comp_arc_sta__telemetry_guard__monitor
   :failure_id: SI_01_02
   :failure_effect: A faulty time source or timeout configuration defeats both the guard and its monitor.
   :mitigation_issue: https://github.com/example-org/telemetry-guard/issues/13
   :sufficient: no
   :status: invalid

   Guard and monitor read the same monotonic time source and timeout configuration, so their independence is not demonstrated at component scope. Disposition pending review: allocate to the feature/platform DFA or require a diverse time plausibility check.

