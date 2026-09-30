Telemetry guard FMEA
====================

.. document:: Telemetry guard FMEA
   :id: doc__telemetry_guard_fmea
   :status: draft
   :version: 1
   :safety: ASIL_B
   :security: NO
   :realizes: wp__sw_component_fmea

Synthetic increment 008 fixture for the telemetry freshness guard; not S-CORE engineering content.

.. list-table:: Fault models for the evaluate sequence
   :header-rows: 1

   * - ID
     - Failure mode
     - Applicability
     - Rationale
   * - MF_01_01
     - sample not received
     - yes
     - Analysed in comp_saf_fmea__telemetry_guard__sample_lost.
   * - MF_01_02
     - sample received too late
     - yes
     - Analysed in comp_saf_fmea__telemetry_guard__late_sample.
   * - MF_01_03
     - sample received too early
     - no
     - Not applicable: the single-reader evaluate sequence has no received too early path in this fixture.
   * - MF_01_04
     - sample not received by all recipients
     - no
     - Not applicable: the single-reader evaluate sequence has no not received by all recipients path in this fixture.
   * - MF_01_05
     - sample corrupted
     - no
     - Not applicable: the single-reader evaluate sequence has no corrupted path in this fixture.
   * - MF_01_06
     - sample not sent
     - no
     - Not applicable: the single-reader evaluate sequence has no not sent path in this fixture.
   * - MF_01_07
     - sample sent unintentionally
     - no
     - Not applicable: the single-reader evaluate sequence has no sent unintentionally path in this fixture.
   * - CO_01_01
     - minimum constraint violated
     - no
     - Not applicable: the single-reader evaluate sequence has no constraint violated path in this fixture.
   * - CO_01_02
     - maximum constraint violated
     - no
     - Not applicable: the single-reader evaluate sequence has no constraint violated path in this fixture.
   * - EX_01_01
     - wrong verdict calculated
     - yes
     - Analysed in comp_saf_fmea__telemetry_guard__wrong_verdict.
   * - EX_01_02
     - processing too slow
     - no
     - Not applicable: the single-reader evaluate sequence has no too slow path in this fixture.
   * - EX_01_03
     - processing too fast
     - no
     - Not applicable: the single-reader evaluate sequence has no too fast path in this fixture.
   * - EX_01_04
     - loss of execution
     - no
     - Not applicable: the single-reader evaluate sequence has no of execution path in this fixture.
   * - EX_01_05
     - processing changes to arbitrary process
     - no
     - Not applicable: the single-reader evaluate sequence has no changes to arbitrary process path in this fixture.
   * - EX_01_06
     - processing not complete
     - no
     - Not applicable: the single-reader evaluate sequence has no not complete path in this fixture.

FMEA
----

.. code-block:: rst

   .. comp_saf_fmea:: Example only
      :id: comp_saf_fmea__example__ignored
      :fault_id: MF_01_06

.. comp_saf_fmea:: Sample lost
   :id: comp_saf_fmea__telemetry_guard__sample_lost
   :violates: comp_arc_dyn__telemetry_guard__evaluate
   :fault_id: MF_01_01
   :failure_effect: The consumer receives no verdict update.
   :mitigated_by: comp_req__telemetry_guard__report_missing
   :sufficient: no
   :status: invalid

   Draft argument: reporting NoData makes the missing sample visible. Pending safety review.

.. comp_saf_fmea:: Late sample
   :id: comp_saf_fmea__telemetry_guard__late_sample
   :violates: comp_arc_dyn__telemetry_guard__evaluate
   :fault_id: MF_01_02
   :failure_effect: An outdated sample is reported as Valid.
   :sufficient: no
   :status: invalid

   No mechanism detects sample age in this architecture. A mitigation is required.

.. comp_saf_fmea:: Wrong verdict
   :id: comp_saf_fmea__telemetry_guard__wrong_verdict
   :violates: comp_arc_dyn__telemetry_guard__evaluate
   :fault_id: EX_01_01
   :failure_effect: The consumer acts on an incorrect verdict.
   :mitigated_by: aou_req__telemetry_guard__consumer_check
   :sufficient: no
   :status: invalid

   Draft argument relies on the consumer assumption. Pending safety review.

