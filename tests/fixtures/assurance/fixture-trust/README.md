# Increment 005 fixture trust material

This directory contains a deterministic test public key and signed test vector. Its private
seed exists only in `tests/assurance_support.py`, is public test data, and is never a production
credential. The profile is restricted to `fixture_contract`; every production assessment rejects
it regardless of signature validity. These records do not demonstrate a protected collector or
authenticated person.
