# Retained quality profile transport

`s-core-quality-legacy-v1.yaml` preserves the exact primary profile bytes before installed-context
consolidation. SHA-256: `720a64d14ecc193e034a45e3c68dffed27df1d23837b886268af55acd1413ec9`.
It is a candidate policy, not adopted engineering policy or eligibility evidence. Existing sealed
records/packets are unchanged. The legacy native-import example selects this byte-identical copy
and keeps its original artifact profile bindings. Current execution/coverage examples select the
new main profile and new outputs; no historical output is relabelled as current evidence.
