Component fixture
=================

.. document:: Component work product
   :id: DOC_COMPONENT_{{ID}}
   :status: draft
   :realizes: WP_COMPONENT_{{ID}}

   Manual wrapper prose that must remain byte exact.

.. comp_req:: Deterministic component
   :id: COMP_REQ_{{ID}}
   :status: valid
   :version: 1
   :derived_from: FEAT_REQ_{{ID}}
   :fully_verifies: TEST_CASE_{{ID}}

   The component shall preserve native identities.

.. interface:: Stable interface
   :id: INTERFACE_{{ID}}
   :status: valid
   :version: 1
   :belongs_to: COMP_REQ_{{ID}}

   The interface is explicitly reviewed in this fixture.

.. test_case:: Component verification
   :id: TEST_CASE_{{ID}}
   :status: valid
   :version: 1
   :fully_verifies: COMP_REQ_{{ID}}

   Verify deterministic output.
