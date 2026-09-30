# Catalogue data model (implemented subset)

The v1 typed shapes are in the package catalogue/models.py and
process_source/models.py, with serialization schemas under repository schemas/.
The detailed contract is in [catalogue.md](contracts/catalogue.md): SourceRef and
ExportManifest establish provenance; NativeType defines source constraints; NativeEntity
captures process definitions/documents; Relation preserves typed native edges; Catalogue
contains the derived deterministic view. No independently writable engineering content.

InstanceIdentity, SubjectManifest, EvidenceManifest, Approval and GateResult in
[forward-boundaries.md](contracts/forward-boundaries.md) are **not implemented in 001**.
