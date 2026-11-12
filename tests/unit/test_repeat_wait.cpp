/**
 * @file tests/unit/test_repeat_wait.cpp
 * @brief Tests for the encode loop's wait before it repeats a frame.
 */

// test includes
#include "../tests_common.h"

// standard includes
#include <chrono>

// local includes
#include <src/video.h>

namespace {
  using clock_type = std::chrono::steady_clock;
  using std::chrono::microseconds;

  constexpr microseconds frametime {8333};  // minimum frame rate of 120
  constexpr microseconds encode_time {7200};

  /**
   * @brief State of the loop right after a captured frame left the encoder.
   *
   * @param interval Time between the last two captured frames.
   * @param shortest The shorter of the last two such intervals.
   * @return Timing with the frame captured at the epoch and encoded at once.
   */
  video::repeat_timing_t after_captured_frame(microseconds interval, microseconds shortest) {
    video::repeat_timing_t timing {};
    timing.frame_start = clock_type::time_point {};
    timing.last_capture = clock_type::time_point {};
    timing.encode_time = encode_time;
    timing.now = timing.frame_start + encode_time;
    timing.capture_interval = interval;
    timing.shortest_capture_interval = shortest;
    timing.max_frametime = frametime;
    timing.repeat_in_budget = true;
    return timing;
  }
}  // namespace

TEST(RepeatWaitTests, AppAtTheMinimumRateIsLeftAlone) {
  const auto timing = after_captured_frame(frametime, frametime);

  // The next frame is due in 1133 us; the repeat waits a frame time beyond that.
  EXPECT_EQ(video::repeat_wait(timing), frametime + frametime - encode_time);
}

TEST(RepeatWaitTests, AppAtHalfTheRateGetsARepeatOnTheCadence) {
  const auto timing = after_captured_frame(2 * frametime, 2 * frametime);

  EXPECT_EQ(video::repeat_wait(timing), frametime - encode_time);
}

TEST(RepeatWaitTests, NoSecondRepeatBeforeTheAppsNextFrame) {
  auto timing = after_captured_frame(2 * frametime, 2 * frametime);
  timing.frame_start += frametime;  // the repeat
  timing.now = timing.frame_start + encode_time;

  // The app's frame is due at 16666 us, and the wait runs a frame time past it.
  EXPECT_EQ(video::repeat_wait(timing), 3 * frametime - (frametime + encode_time));
}

TEST(RepeatWaitTests, RepeatStartsEarlierWhenTheCadenceSlotIsTooLate) {
  // 66 fps: a repeat on the cadence would end after the app's next frame, one started at once does not.
  const microseconds interval {15000};
  const auto timing = after_captured_frame(interval, interval);

  EXPECT_EQ(video::repeat_wait(timing), microseconds {100});
}

TEST(RepeatWaitTests, OneLongIntervalInAFastAppGetsNoEarlyRepeat) {
  const auto timing = after_captured_frame(2 * frametime, frametime);

  EXPECT_EQ(video::repeat_wait(timing), 3 * frametime - encode_time);
}

TEST(RepeatWaitTests, StoppedAppGetsRepeatsOnTheCadence) {
  auto timing = after_captured_frame(frametime, frametime);
  timing.frame_start += 4 * frametime;  // a repeat, long after the last captured frame
  timing.now = timing.frame_start + encode_time;

  EXPECT_EQ(video::repeat_wait(timing), frametime - encode_time);
}

TEST(RepeatWaitTests, RepeatOutOfBudgetWaitsForTheAppsNextFrame) {
  auto timing = after_captured_frame(2 * frametime, 2 * frametime);
  timing.repeat_in_budget = false;

  EXPECT_EQ(video::repeat_wait(timing), 3 * frametime - encode_time);
}

TEST(RepeatWaitTests, OverdueRepeatDoesNotWait) {
  auto timing = after_captured_frame(frametime, frametime);
  timing.frame_start += 4 * frametime;
  timing.now = timing.frame_start + 2 * frametime;

  EXPECT_EQ(video::repeat_wait(timing), clock_type::duration::zero());
}

TEST(RepeatWaitTests, LongIntervalDoesNotStretchTheWait) {
  // One frame after a long still picture: the app's next frame is due seconds from now.
  const auto timing = after_captured_frame(std::chrono::seconds {5}, frametime);

  EXPECT_EQ(video::repeat_wait(timing), frametime);
}

TEST(RepeatWaitTests, AppThatStopsAfterALongIntervalCountsAsStoppedSoon) {
  auto timing = after_captured_frame(std::chrono::seconds {5}, frametime);
  timing.frame_start += 4 * frametime;  // a repeat, four frame times after that one frame
  timing.now = timing.frame_start + encode_time;

  EXPECT_EQ(video::repeat_wait(timing), frametime - encode_time);
}
