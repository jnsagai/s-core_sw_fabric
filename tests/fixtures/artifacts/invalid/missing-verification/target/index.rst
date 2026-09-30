Component fixture
=================

.. document:: Component work product
   :id: DOC_COMPONENT_001
   :status: draft
   :realizes: WP_COMPONENT_001

   Manual wrapper prose that must remain byte exact.

.. comp_req:: Deterministic component
   :id: COMP_REQ_001
   :status: valid
   :version: 1
   :derived_from: FEAT_REQ_001

   The component shall preserve native identities.

.. interface:: Stable interface
   :id: INTERFACE_001
   :status: valid
   :version: 1
   :belongs_to: COMP_REQ_001

   The interface is explicitly reviewed in this fixture.

.. test_case:: Component verification
   :id: TEST_CASE_001
   :status: valid
   :version: 1

   Verify deterministic output.
