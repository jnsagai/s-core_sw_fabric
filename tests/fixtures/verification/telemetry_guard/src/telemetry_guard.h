// Synthetic increment 009 fixture; not S-CORE engineering content.
// req-Id: comp_req__telemetry_guard__report_missing, comp_req__telemetry_guard__stale_detection
// req-Id: comp_req__telemetry_guard__reject_invalid_config, comp_req__telemetry_guard__reject_future_sample
#ifndef SCORE_TELEMETRY_GUARD_H
#define SCORE_TELEMETRY_GUARD_H

#include <cstdint>

namespace score
{
namespace telemetry_guard
{

using Nanoseconds = std::uint64_t;

enum class Verdict : std::uint8_t
{
    kNoData,
    kValid,
    kStale,
    kInvalid,
    kInvalidConfig,
};

class FreshnessGuard final
{
  public:
    explicit FreshnessGuard(Nanoseconds timeout) noexcept;

    void OnSample(Nanoseconds sample_time) noexcept;

    Verdict Evaluate(Nanoseconds now) const noexcept;

  private:
    Nanoseconds timeout_;
    Nanoseconds newest_sample_;
    bool has_sample_;
};

}  // namespace telemetry_guard
}  // namespace score

#endif  // SCORE_TELEMETRY_GUARD_H
