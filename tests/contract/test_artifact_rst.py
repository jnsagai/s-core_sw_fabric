from __future__ import annotations

import pytest

from score_sw_fabric.artifacts.models import ArtifactSemanticError
from score_sw_fabric.artifacts.rst import scan_rst


def test_scanner_preserves_spans_and_ignores_literal_directives() -> None:
    source = """.. document:: Wrapper
   :id: DOC_1
   :status: draft

.. code-block:: rst

   .. fmea:: Example
      :id: EXAMPLE

.. fmea:: Live
   :id: FMEA_1
   :status: valid
"""
    result = scan_rst("index.rst", source, {"document", "fmea"})
    assert [item["native_id"] for item in result["directives"]] == ["DOC_1", "FMEA_1"]
    for item in result["directives"]:
        assert source.encode()[item["start_byte"] : item["end_byte"]]


def test_scanner_rejects_duplicate_options() -> None:
    source = ".. comp_req:: X\n   :id: X\n   :id: Y\n   :status: valid\n"
    with pytest.raises(ArtifactSemanticError, match="Duplicate option"):
        scan_rst("x.rst", source, {"comp_req"})
