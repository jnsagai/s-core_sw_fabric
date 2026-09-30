Telemetry guard architecture
============================

.. document:: Telemetry guard architecture
   :id: doc__telemetry_guard_architecture
   :status: draft
   :version: 1
   :safety: ASIL_B
   :security: NO
   :realizes: wp__component_arch

Synthetic increment 008 fixture for the telemetry freshness guard; not S-CORE engineering content.

.. comp_arc_sta:: Freshness guard
   :id: comp_arc_sta__telemetry_guard__guard
   :status: valid
   :safety: ASIL_B

   Static view: sample buffer and verdict output.

.. comp_arc_dyn:: Evaluate sample
   :id: comp_arc_dyn__telemetry_guard__evaluate
   :status: valid
   :safety: ASIL_B

   The guard reads the newest sample and returns a verdict.

