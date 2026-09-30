Telemetry guard requirements
============================

.. document:: Telemetry guard requirements
   :id: doc__telemetry_guard_requirements
   :status: draft
   :version: 1
   :safety: ASIL_B
   :security: NO
   :realizes: wp__requirements_comp

Synthetic increment 008 fixture for the telemetry freshness guard; not S-CORE engineering content.

.. comp_req:: Report missing sample
   :id: comp_req__telemetry_guard__report_missing
   :status: valid
   :safety: ASIL_B
   :reqtype: Functional

   The guard shall report ``NoData`` when no sample was received since start.

.. aou_req:: Consumer validates verdict
   :id: aou_req__telemetry_guard__consumer_check
   :status: valid
   :safety: ASIL_B

   The consumer shall treat any verdict other than ``Valid`` as unusable.

.. comp_req:: Detect stale sample
   :id: comp_req__telemetry_guard__stale_detection
   :status: valid
   :safety: ASIL_B
   :reqtype: Functional

   The guard shall report ``Stale`` when the newest sample is older than the configured timeout on the monotonic clock.

