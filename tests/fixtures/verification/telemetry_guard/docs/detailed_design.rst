Telemetry guard detailed design
===============================

.. document:: Telemetry guard detailed design
   :id: doc__telemetry_guard_detailed_design
   :status: draft
   :version: 1
   :safety: ASIL_B
   :security: NO
   :realizes: wp__sw_implementation

Synthetic increment 009 fixture; not S-CORE engineering content.

Description
-----------

The component evaluates the freshness of the newest telemetry sample against a configured
timeout. Time is injected as monotonic nanoseconds so that tests control the clock; the guard
never reads a clock itself. Out-of-order samples never move the newest sample time backwards.

Rationale Behind Decomposition into Units
*****************************************

A single unit keeps the verdict logic in one place with no shared state; the header declares the
interface and the source file implements it.

Static Diagrams for Unit Interactions
-------------------------------------

.. uml::

   @startuml
   class FreshnessGuard {
     +OnSample(sample_time)
     +Evaluate(now) : Verdict
   }
   enum Verdict { NoData Valid Stale Invalid InvalidConfig }
   FreshnessGuard --> Verdict
   @enduml

Units within the Component
--------------------------

- ``src/telemetry_guard.h``: interface of ``FreshnessGuard`` and ``Verdict``.
- ``src/telemetry_guard.cpp``: verdict logic.
