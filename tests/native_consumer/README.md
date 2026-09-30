# Disposable native process consumer probe

This is the exact minimal Bazel consumer that built process_description 2.1.2
with docs-as-code 8.2.0 and rules_python 1.8.5/Python 3.12 on 2026-09-27.
The checked-in MODULE.bazel.lock records registry file hashes. Use Bazel 8.7.0
through Bazelisk 1.29.0 (or the same pinned Bazel binary).

Copy this directory into a disposable workspace. Copy the process/ directory
from pinned process_description commit
98d1d5f42dad412a09a888ea25e59c62fa6371ce into that workspace. The
docs_check command expects process/ and the root BUILD sentinel; neither
source files nor generated virtual environments should be written into the
read-only reference checkout.

Run from the disposable workspace:

~~~
bazel --batch --output_user_root=/tmp/score-native-bazel build @score_process_description//:needs_json --jobs=2 --verbose_failures --lockfile_mode=error
bazel --batch --output_user_root=/tmp/score-native-bazel run @score_process_description//:docs_check --jobs=2 --verbose_failures --lockfile_mode=error
~~~

The first build may download several GiB of toolchains/dependencies. Use a
bounded disposable output cache and enough disk headroom. The registry URLs
in .bazelrc are mutable; --lockfile_mode=error rejects metadata drift from
the checked-in lock. Compare the resolved process source bytes to the pinned
checkout before claiming source provenance. The resulting export is under
bazel-bin/external/score_process_description+/needs_json/_build/needs/needs.json.
See the 001 acceptance record and evidence logs for exact observed results.
