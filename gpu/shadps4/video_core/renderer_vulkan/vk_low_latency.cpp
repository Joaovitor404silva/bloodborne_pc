// SPDX-FileCopyrightText: Copyright 2026 bbport contributors
// SPDX-License-Identifier: GPL-2.0-or-later

#include <array>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <algorithm>
#include <deque>
#include <mutex>
#include <string_view>
#include "common/logging/log.h"
#include "core/emulator_settings.h"
#include "video_core/renderer_vulkan/vk_instance.h"
#include "video_core/renderer_vulkan/vk_low_latency.h"

namespace Vulkan::LowLatency {

namespace {

enum class Mode { Off, Reflex, AntiLag };

struct State {
    Mode mode = Mode::Off;
    bool boost = false;
    u32 max_fps = 0; ///< the frame limit, also given to the driver (it waits before the frame)
    VkDevice device = VK_NULL_HANDLE;

    std::mutex mutex; ///< the swapchain against the markers and the sleep (other threads)
    VkSwapchainKHR swapchain = VK_NULL_HANDLE;
    VkSemaphore sleep_semaphore = VK_NULL_HANDLE; ///< Reflex: timeline the driver signals
    u64 sleep_value = 0;
    VkSwapchainLatencyCreateInfoNV swapchain_info{
        .sType = VK_STRUCTURE_TYPE_SWAPCHAIN_LATENCY_CREATE_INFO_NV,
        .latencyModeEnable = VK_TRUE,
    };

    /// BB_FRAME_STATS=1 or BB_LATENCY_LOG=1: the time from the game starting a frame to its
    /// present, every 5 seconds, also with low latency off (to compare).
    bool measure = false;
    std::mutex measure_mutex;
    std::array<std::pair<u64, std::chrono::steady_clock::time_point>, 64> starts{};
    std::chrono::steady_clock::time_point window{};
    double latency_ms = 0.0, latency_max_ms = 0.0;
    u32 latency_frames = 0;

    u64 frame = 1; ///< the frame the game works on (game render thread)
    std::mutex queue_mutex;
    std::deque<u64> submitted; ///< submitted, not flipped yet (game thread to GPU thread)
};

State state;

std::string_view Setting() {
    const char* env = std::getenv("BB_LOW_LATENCY");
    return env ? std::string_view{env} : std::string_view{};
}

void Marker(VkLatencyMarkerNV marker, u64 id) {
    std::scoped_lock lock{state.mutex};
    if (!state.swapchain) {
        return;
    }
    const VkSetLatencyMarkerInfoNV info{
        .sType = VK_STRUCTURE_TYPE_SET_LATENCY_MARKER_INFO_NV,
        .presentID = id,
        .marker = marker,
    };
    VULKAN_HPP_DEFAULT_DISPATCHER.vkSetLatencyMarkerNV(state.device, state.swapchain, &info);
}

void AntiLag(VkAntiLagStageAMD stage, u64 id) {
    const VkAntiLagPresentationInfoAMD presentation{
        .sType = VK_STRUCTURE_TYPE_ANTI_LAG_PRESENTATION_INFO_AMD,
        .stage = stage,
        .frameIndex = id,
    };
    const VkAntiLagDataAMD data{
        .sType = VK_STRUCTURE_TYPE_ANTI_LAG_DATA_AMD,
        .mode = VK_ANTI_LAG_MODE_ON_AMD,
        .maxFPS = state.max_fps,
        .pPresentationInfo = &presentation,
    };
    VULKAN_HPP_DEFAULT_DISPATCHER.vkAntiLagUpdateAMD(state.device, &data);
}

// Reflex: the driver signals the semaphore when the next frame should begin.
void ReflexSleep() {
    u64 value = 0;
    {
        std::scoped_lock lock{state.mutex};
        if (!state.swapchain) {
            return;
        }
        value = ++state.sleep_value;
        const VkLatencySleepInfoNV info{
            .sType = VK_STRUCTURE_TYPE_LATENCY_SLEEP_INFO_NV,
            .signalSemaphore = state.sleep_semaphore,
            .value = value,
        };
        if (VULKAN_HPP_DEFAULT_DISPATCHER.vkLatencySleepNV(state.device, state.swapchain, &info) !=
            VK_SUCCESS) {
            return;
        }
    }
    // Bounded: nothing is presented while the window is minimized.
    const VkSemaphoreWaitInfo wait{
        .sType = VK_STRUCTURE_TYPE_SEMAPHORE_WAIT_INFO,
        .semaphoreCount = 1,
        .pSemaphores = &state.sleep_semaphore,
        .pValues = &value,
    };
    VULKAN_HPP_DEFAULT_DISPATCHER.vkWaitSemaphores(state.device, &wait, 100'000'000);
}

bool Active() {
    return state.mode != Mode::Off || state.measure;
}

const char* ModeName() {
    switch (state.mode) {
    case Mode::Reflex:
        return state.boost ? "NVIDIA Reflex + Boost" : "NVIDIA Reflex";
    case Mode::AntiLag:
        return "AMD Anti-Lag 2";
    default:
        return "low latency off";
    }
}

bool Flag(const char* name) {
    const char* env = std::getenv(name);
    return env && env[0] == '1';
}

} // namespace

bool Wanted() {
    const auto setting = Setting();
    return setting == "on" || setting == "boost";
}

void Init(const Instance& instance) {
    state.measure = Flag("BB_FRAME_STATS") || Flag("BB_LATENCY_LOG");
    if (!Wanted()) {
        return;
    }
    state.device = instance.GetDevice();
    state.boost = Setting() == "boost";
    state.max_fps = EmulatorSettings.GetFrameLimit();
    if (instance.IsNvLowLatencyEnabled()) {
        const VkSemaphoreTypeCreateInfo type{
            .sType = VK_STRUCTURE_TYPE_SEMAPHORE_TYPE_CREATE_INFO,
            .semaphoreType = VK_SEMAPHORE_TYPE_TIMELINE,
        };
        const VkSemaphoreCreateInfo info{
            .sType = VK_STRUCTURE_TYPE_SEMAPHORE_CREATE_INFO,
            .pNext = &type,
        };
        if (VULKAN_HPP_DEFAULT_DISPATCHER.vkCreateSemaphore(state.device, &info, nullptr,
                                                            &state.sleep_semaphore) ==
            VK_SUCCESS) {
            state.mode = Mode::Reflex;
        }
    } else if (instance.IsAmdAntiLagEnabled()) {
        state.mode = Mode::AntiLag;
    }
    switch (state.mode) {
    case Mode::Reflex:
        std::printf("Low latency: NVIDIA Reflex%s\n", state.boost ? " + Boost" : "");
        break;
    case Mode::AntiLag:
        std::printf("Low latency: AMD Anti-Lag 2\n");
        break;
    case Mode::Off:
        std::printf("Low latency: not available with this GPU or driver (needs NVIDIA Reflex, "
                    "VK_NV_low_latency2, or AMD Anti-Lag 2, VK_AMD_anti_lag)\n");
        break;
    }
}

const void* SwapchainCreateNext() {
    return state.mode == Mode::Reflex ? &state.swapchain_info : nullptr;
}

void OnSwapchain(vk::SwapchainKHR swapchain) {
    if (state.mode != Mode::Reflex) {
        return;
    }
    std::scoped_lock lock{state.mutex};
    state.swapchain = swapchain;
    if (!swapchain) {
        // A game thread waiting for the old swapchain's signal goes on.
        const VkSemaphoreSignalInfo signal{
            .sType = VK_STRUCTURE_TYPE_SEMAPHORE_SIGNAL_INFO,
            .semaphore = state.sleep_semaphore,
            .value = ++state.sleep_value,
        };
        VULKAN_HPP_DEFAULT_DISPATCHER.vkSignalSemaphore(state.device, &signal);
        return;
    }
    const VkLatencySleepModeInfoNV mode{
        .sType = VK_STRUCTURE_TYPE_LATENCY_SLEEP_MODE_INFO_NV,
        .lowLatencyMode = VK_TRUE,
        .lowLatencyBoost = state.boost ? VK_TRUE : VK_FALSE,
        .minimumIntervalUs = state.max_fps ? 1'000'000 / state.max_fps : 0,
    };
    const auto result =
        VULKAN_HPP_DEFAULT_DISPATCHER.vkSetLatencySleepModeNV(state.device, swapchain, &mode);
    if (result != VK_SUCCESS) {
        LOG_WARNING(Render_Vulkan, "Reflex: the driver did not take the sleep mode ({})",
                    static_cast<int>(result));
    }
}

void FrameSubmitted() {
    if (!Active()) {
        return;
    }
    const u64 frame = state.frame;
    if (state.mode == Mode::Reflex) {
        Marker(VK_LATENCY_MARKER_SIMULATION_END_NV, frame);
        Marker(VK_LATENCY_MARKER_RENDERSUBMIT_START_NV, frame);
    }
    {
        std::scoped_lock lock{state.queue_mutex};
        // Flips that never came (a frame the game dropped) must not hold the ids back.
        while (state.submitted.size() >= 8) {
            state.submitted.pop_front();
        }
        state.submitted.push_back(frame);
    }

    const u64 next = state.frame = frame + 1;
    if (state.mode == Mode::Reflex) {
        ReflexSleep();
        Marker(VK_LATENCY_MARKER_SIMULATION_START_NV, next);
        Marker(VK_LATENCY_MARKER_INPUT_SAMPLE_NV, next);
    } else if (state.mode == Mode::AntiLag) {
        AntiLag(VK_ANTI_LAG_STAGE_INPUT_AMD, next); // waits in the driver
    }
    if (state.measure) {
        std::scoped_lock lock{state.measure_mutex};
        state.starts[next % state.starts.size()] = {next, std::chrono::steady_clock::now()};
    }
}

u64 RenderSubmitEnd() {
    if (!Active()) {
        return 0;
    }
    u64 id = 0;
    {
        std::scoped_lock lock{state.queue_mutex};
        if (!state.submitted.empty()) {
            id = state.submitted.front();
            state.submitted.pop_front();
        }
    }
    if (id && state.mode == Mode::Reflex) {
        Marker(VK_LATENCY_MARKER_RENDERSUBMIT_END_NV, id);
    }
    return id;
}

void PresentStart(u64 id) {
    if (!id) {
        return;
    }
    if (state.mode == Mode::Reflex) {
        Marker(VK_LATENCY_MARKER_PRESENT_START_NV, id);
    } else if (state.mode == Mode::AntiLag) {
        AntiLag(VK_ANTI_LAG_STAGE_PRESENT_AMD, id);
    }
}

void PresentEnd(u64 id) {
    if (id && state.mode == Mode::Reflex) {
        Marker(VK_LATENCY_MARKER_PRESENT_END_NV, id);
    }
    if (!id || !state.measure) {
        return;
    }
    const auto now = std::chrono::steady_clock::now();
    std::scoped_lock lock{state.measure_mutex};
    const auto& [start_id, start] = state.starts[id % state.starts.size()];
    if (start_id == id) {
        const double ms = std::chrono::duration<double, std::milli>(now - start).count();
        state.latency_ms += ms;
        state.latency_max_ms = std::max(state.latency_max_ms, ms);
        ++state.latency_frames;
    }
    if (state.window == std::chrono::steady_clock::time_point{}) {
        state.window = now;
    }
    if (now - state.window >= std::chrono::seconds(5)) {
        if (state.latency_frames) {
            std::printf("Latency: %.1f ms from the game starting a frame to its present (worst "
                        "%.1f ms, %u frames, %s)\n",
                        state.latency_ms / state.latency_frames, state.latency_max_ms,
                        state.latency_frames, ModeName());
        }
        state.window = now;
        state.latency_ms = state.latency_max_ms = 0.0;
        state.latency_frames = 0;
    }
}

} // namespace Vulkan::LowLatency
