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

   Evaluates sample age against a timeout.

.. comp_arc_sta:: Freshness monitor
   :id: comp_arc_sta__telemetry_guard__monitor
   :status: valid
   :safety: ASIL_B

   Supervises the guard. Reads the same monotonic time source and timeout configuration as the guard.

