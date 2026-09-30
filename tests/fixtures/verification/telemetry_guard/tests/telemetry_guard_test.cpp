// Synthetic increment 009 fixture; not S-CORE engineering content.
#include "telemetry_guard.h"

#include <gtest/gtest.h>

namespace score
{
namespace telemetry_guard
{
namespace
{

constexpr Nanoseconds kTimeout{100U};

class FreshnessGuardTest : public ::testing::Test
{
  protected:
    void Describe(const char* verifies, const char* ids, const char* test_type,
                  const char* technique, const char* description)
    {
        RecordProperty(verifies, ids);
        RecordProperty("TestType", test_type);
        RecordProperty("DerivationTechnique", technique);
        RecordProperty("Description", description);
    }

    FreshnessGuard guard_{kTimeout};
};

TEST_F(FreshnessGuardTest, NoDataBeforeFirstSample)
{
    Describe("FullyVerifies", "comp_req__telemetry_guard__report_missing", "requirements-based",
             "requirements-analysis", "Evaluation before any sample reports NoData.");
    EXPECT_EQ(guard_.Evaluate(0U), Verdict::kNoData);
    EXPECT_EQ(guard_.Evaluate(1000U), Verdict::kNoData);
}

TEST_F(FreshnessGuardTest, NoDataAtMaximumEvaluationTime)
{
    Describe("PartiallyVerifies", "comp_req__telemetry_guard__report_missing", "requirements-based",
             "boundary-values", "Without a sample, the maximum clock value still reports NoData.");
    EXPECT_EQ(guard_.Evaluate(UINT64_MAX), Verdict::kNoData);
}

TEST_F(FreshnessGuardTest, ReceivedSampleDoesNotReportNoData)
{
    Describe("PartiallyVerifies", "comp_req__telemetry_guard__report_missing", "requirements-based",
             "error-guessing", "A received sample cannot be mistaken for missing data.");
    guard_.OnSample(0U);
    EXPECT_NE(guard_.Evaluate(0U), Verdict::kNoData);
}

TEST_F(FreshnessGuardTest, FreshSampleIsValid)
{
    Describe("PartiallyVerifies", "comp_req__telemetry_guard__stale_detection",
             "requirements-based", "equivalence-classes", "A sample younger than the timeout is Valid.");
    guard_.OnSample(1000U);
    EXPECT_EQ(guard_.Evaluate(1050U), Verdict::kValid);
}

TEST_F(FreshnessGuardTest, AgeEqualToTimeoutIsValid)
{
    Describe("PartiallyVerifies", "comp_req__telemetry_guard__stale_detection",
             "requirements-based", "boundary-values", "A sample exactly at the timeout is still Valid.");
    guard_.OnSample(1000U);
    EXPECT_EQ(guard_.Evaluate(1000U + kTimeout), Verdict::kValid);
}

TEST_F(FreshnessGuardTest, AgeAboveTimeoutIsStale)
{
    Describe("PartiallyVerifies", "comp_req__telemetry_guard__stale_detection",
             "requirements-based", "boundary-values", "One nanosecond past the timeout is Stale.");
    guard_.OnSample(1000U);
    EXPECT_EQ(guard_.Evaluate(1000U + kTimeout + 1U), Verdict::kStale);
}

TEST_F(FreshnessGuardTest, OutOfOrderSampleKeepsNewest)
{
    Describe("PartiallyVerifies", "comp_req__telemetry_guard__stale_detection",
             "requirements-based", "error-guessing", "An older sample does not reset freshness backwards.");
    guard_.OnSample(1000U);
    guard_.OnSample(500U);
    EXPECT_EQ(guard_.Evaluate(1000U + kTimeout), Verdict::kValid);
}

TEST_F(FreshnessGuardTest, ZeroTimeoutIsInvalidConfig)
{
    Describe("FullyVerifies", "comp_req__telemetry_guard__reject_invalid_config",
             "requirements-based", "boundary-values", "A zero timeout reports InvalidConfig.");
    FreshnessGuard guard{0U};
    EXPECT_EQ(guard.Evaluate(0U), Verdict::kInvalidConfig);
    guard.OnSample(0U);
    EXPECT_EQ(guard.Evaluate(0U), Verdict::kInvalidConfig);
}

TEST_F(FreshnessGuardTest, ZeroTimeoutPrecedesFutureSample)
{
    Describe("PartiallyVerifies", "comp_req__telemetry_guard__reject_invalid_config",
             "requirements-based", "error-guessing", "Invalid configuration takes precedence over a future sample.");
    FreshnessGuard guard{0U};
    guard.OnSample(100U);
    EXPECT_EQ(guard.Evaluate(0U), Verdict::kInvalidConfig);
}

TEST_F(FreshnessGuardTest, NonzeroTimeoutIsUsable)
{
    Describe("PartiallyVerifies", "comp_req__telemetry_guard__reject_invalid_config",
             "requirements-based", "boundary-values", "The smallest nonzero timeout is usable.");
    FreshnessGuard guard{1U};
    guard.OnSample(0U);
    EXPECT_EQ(guard.Evaluate(0U), Verdict::kValid);
}

TEST_F(FreshnessGuardTest, FutureSampleIsInvalid)
{
    Describe("FullyVerifies", "comp_req__telemetry_guard__reject_future_sample", "fault-injection",
             "error-guessing", "A sample later than the evaluation time reports Invalid.");
    guard_.OnSample(2000U);
    EXPECT_EQ(guard_.Evaluate(1999U), Verdict::kInvalid);
}

TEST_F(FreshnessGuardTest, EqualSampleTimeIsNotFuture)
{
    Describe("PartiallyVerifies", "comp_req__telemetry_guard__reject_future_sample",
             "requirements-based", "boundary-values", "A sample at evaluation time is not future data.");
    guard_.OnSample(100U);
    EXPECT_EQ(guard_.Evaluate(100U), Verdict::kValid);
}

TEST_F(FreshnessGuardTest, FutureSampleStillInvalidAfterOlderSample)
{
    Describe("PartiallyVerifies", "comp_req__telemetry_guard__reject_future_sample",
             "fault-injection", "error-guessing", "An older sample cannot mask a future newest sample.");
    guard_.OnSample(200U);
    guard_.OnSample(100U);
    EXPECT_EQ(guard_.Evaluate(199U), Verdict::kInvalid);
}

}  // namespace
}  // namespace telemetry_guard
}  // namespace score
