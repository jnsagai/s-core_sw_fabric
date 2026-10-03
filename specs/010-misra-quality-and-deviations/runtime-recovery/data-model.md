# Derived supervision evidence

Policy binds native run/root/server, frozen executable/control hashes, observer
state directory, repair command and worker/start grace. Private state is internal.
Ready/heartbeat receipts bind policy digest, run ID, PID/start time and boot ID.
Incident binds native observation and source/control hashes, fault fingerprint,
claim, repair process identity, verified changes and optional successor run/root.
State transitions: observing -> incident_claimed -> preserving -> repair_requested
-> verifying -> preparing_successor -> launching_successor -> replaced, or blocked.
No record modifies native Fabro status or authenticates an engineering approval.
