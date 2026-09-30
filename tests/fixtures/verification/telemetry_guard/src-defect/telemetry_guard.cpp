// Synthetic increment 009 fixture; not S-CORE engineering content.
// req-Id: comp_req__telemetry_guard__report_missing
// req-Id: comp_req__telemetry_guard__stale_detection
// req-Id: comp_req__telemetry_guard__reject_invalid_config
// req-Id: comp_req__telemetry_guard__reject_future_sample
#include "telemetry_guard.h"

namespace score
{
namespace telemetry_guard
{

FreshnessGuard::FreshnessGuard(const Nanoseconds timeout) noexcept
    : timeout_{timeout}, newest_sample_{0U}, has_sample_{false}
{
}

void FreshnessGuard::OnSample(const Nanoseconds sample_time) noexcept
{
    if ((!has_sample_) || (sample_time > newest_sample_))
    {
        newest_sample_ = sample_time;
        has_sample_ = true;
    }
}

Verdict FreshnessGuard::Evaluate(const Nanoseconds now) const noexcept
{
    Verdict verdict{Verdict::kValid};
    if (timeout_ == 0U)
    {
        verdict = Verdict::kInvalidConfig;
    }
    else if (!has_sample_)
    {
        verdict = Verdict::kNoData;
    }
    else if (newest_sample_ > now)
    {
        verdict = Verdict::kInvalid;
    }
    else if ((now - newest_sample_) >= timeout_)
    {
        verdict = Verdict::kStale;
    }
    else
    {
        verdict = Verdict::kValid;
    }
    return verdict;
}

}  // namespace telemetry_guard
}  // namespace score
