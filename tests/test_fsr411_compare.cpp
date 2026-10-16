// SPDX-License-Identifier: GPL-2.0-or-later
// Headless comparison of the same production wrappers used by the game.
#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <fstream>
#include <numeric>
#include <stdexcept>
#include <string_view>
#include <vector>
#include "video_core/renderer_vulkan/vk_instance.h"
#include "video_core/renderer_vulkan/vk_scheduler.h"
#include "video_core/renderer_vulkan/vk_fsr4vk.h"
#include "video_core/renderer_vulkan/vk_fsr411_native.h"
#include "video_core/texture_cache/image.h"
#include <vk_mem_alloc.h>

using namespace Vulkan;
extern "C" void runtime_restart() { std::abort(); }
static uint16_t Half(float f) { return std::bit_cast<uint16_t>(static_cast<_Float16>(f)); }
int main(int argc, char** argv) {
    try {
        const bool async = argc > 1 && std::string_view(argv[1]) == "async";
        const bool native = async || (argc > 1 && std::string_view(argv[1]) == "dx12");
        u32 rw = 1280, rh = 720, ow = 1920, oh = 1080;
        if (argc > 3) { std::sscanf(argv[2], "%ux%u", &rw, &rh); std::sscanf(argv[3], "%ux%u", &ow, &oh); }
        const bool hdr = argc < 5 || std::string_view(argv[4]) != "ldr";
        const int count = argc > 5 ? std::atoi(argv[5]) : 180;
        if (count <= 0 || !rw || !rh || !ow || !oh || rw > 3840 || ow > 3840 || rh > 2160 || oh > 2160)
            throw std::runtime_error("use positive frame counts and dimensions up to 3840x2160");
        const char* batch_setting = std::getenv("BB_FSR411_BATCH_SIZE");
        const int batch_size = batch_setting ? std::atoi(batch_setting) : 1;
        if (batch_size < 1 || batch_size > 64)
            throw std::runtime_error("BB_FSR411_BATCH_SIZE must be 1..64");
        const bool pipeline = std::getenv("BB_FSR411_PIPELINE_TEST") != nullptr || batch_size > 1;
        const bool vary = std::getenv("BB_FSR411_VARY_INPUT") != nullptr;
        const bool vary_motion = std::getenv("BB_FSR411_VARY_MOTION") != nullptr;
        const bool switch_preset = std::getenv("BB_FSR411_SWITCH_PRESET") != nullptr;
        Instance instance(0, false);
        VULKAN_HPP_DEFAULT_DISPATCHER.init(instance.GetInstance());
        VULKAN_HPP_DEFAULT_DISPATCHER.init(instance.GetDevice());
        const auto device = instance.GetDevice();
        Scheduler scheduler(instance);
        std::array<VideoCore::UniqueImage, 4> images;
        std::array<vk::UniqueImageView, 4> views;
        const std::array formats{vk::Format::eR16G16B16A16Sfloat, vk::Format::eR32Sfloat,
                                 vk::Format::eR16G16Sfloat, vk::Format::eR16G16B16A16Sfloat};
        for (u32 i = 0; i < 4; ++i) {
            images[i] = VideoCore::UniqueImage(device, instance.GetAllocator());
            images[i].Create({.imageType = vk::ImageType::e2D, .format = formats[i],
                .extent = {i == 3 ? ow : rw, i == 3 ? oh : rh, 1}, .mipLevels = 1, .arrayLayers = 1,
                .samples = vk::SampleCountFlagBits::e1, .tiling = vk::ImageTiling::eOptimal,
                .usage = vk::ImageUsageFlagBits::eSampled | vk::ImageUsageFlagBits::eStorage |
                         vk::ImageUsageFlagBits::eTransferSrc | vk::ImageUsageFlagBits::eTransferDst});
            views[i] = Check(device.createImageViewUnique({.image = vk::Image(images[i]), .viewType = vk::ImageViewType::e2D,
                .format = formats[i], .subresourceRange = {vk::ImageAspectFlagBits::eColor, 0, 1, 0, 1}}));
        }
        const size_t pixels = size_t(rw) * rh, upload_size = pixels * 16;
        VkBuffer staging{}; VmaAllocation allocation{}; VmaAllocationInfo allocation_info{};
        VkBufferCreateInfo buffer{VK_STRUCTURE_TYPE_BUFFER_CREATE_INFO};
        buffer.size = std::max(upload_size, size_t(ow) * oh * 8);
        buffer.usage = VK_BUFFER_USAGE_TRANSFER_SRC_BIT | VK_BUFFER_USAGE_TRANSFER_DST_BIT;
        VmaAllocationCreateInfo host{};
        host.usage = VMA_MEMORY_USAGE_AUTO;
        host.flags = VMA_ALLOCATION_CREATE_HOST_ACCESS_RANDOM_BIT | VMA_ALLOCATION_CREATE_MAPPED_BIT;
        if (vmaCreateBuffer(instance.GetAllocator(), &buffer, &host, &staging, &allocation, &allocation_info) != VK_SUCCESS)
            throw std::runtime_error("staging allocation failed");
        auto* data = static_cast<uint8_t*>(allocation_info.pMappedData);
        auto* color = reinterpret_cast<uint16_t*>(data);
        auto* depth = reinterpret_cast<float*>(data + pixels * 8);
        auto* motion = reinterpret_cast<uint16_t*>(data + pixels * 12);
        for (size_t y = 0; y < rh; ++y) for (size_t x = 0; x < rw; ++x) {
            const size_t i = y * rw + x;
            color[i * 4] = Half(float(x) / rw);
            color[i * 4 + 1] = Half(float(y) / rh);
            color[i * 4 + 2] = Half(((x / 16 + y / 16) & 1) ? .8f : .2f);
            color[i * 4 + 3] = Half(1);
            depth[i] = .99f + .009f * float(y) / rh; // forward depth for both wrappers
            motion[i * 2] = motion[i * 2 + 1] = 0;
        }
        vmaFlushAllocation(instance.GetAllocator(), allocation, 0, VK_WHOLE_SIZE);
        auto cmd = scheduler.CommandBuffer();
        std::array<vk::ImageMemoryBarrier2, 4> barriers{};
        for (u32 i = 0; i < 4; ++i) barriers[i] = {
            .srcStageMask = vk::PipelineStageFlagBits2::eAllCommands,
            .dstStageMask = vk::PipelineStageFlagBits2::eTransfer,
            .dstAccessMask = vk::AccessFlagBits2::eTransferWrite,
            .oldLayout = vk::ImageLayout::eUndefined, .newLayout = vk::ImageLayout::eGeneral,
            .image = vk::Image(images[i]), .subresourceRange = {vk::ImageAspectFlagBits::eColor, 0, 1, 0, 1}};
        cmd.pipelineBarrier2({.imageMemoryBarrierCount = 4, .pImageMemoryBarriers = barriers.data()});
        const std::array<size_t, 3> offsets{0, pixels * 8, pixels * 12};
        for (u32 i = 0; i < 3; ++i) {
            vk::BufferImageCopy copy{.bufferOffset = offsets[i], .imageSubresource = {vk::ImageAspectFlagBits::eColor, 0, 0, 1},
                                     .imageExtent = {rw, rh, 1}};
            cmd.copyBufferToImage(staging, vk::Image(images[i]), vk::ImageLayout::eGeneral, copy);
        }
        for (auto& b : barriers) {
            b.srcStageMask = vk::PipelineStageFlagBits2::eTransfer; b.srcAccessMask = vk::AccessFlagBits2::eTransferWrite;
            b.dstStageMask = vk::PipelineStageFlagBits2::eAllCommands;
            b.dstAccessMask = vk::AccessFlagBits2::eMemoryRead | vk::AccessFlagBits2::eMemoryWrite;
            b.oldLayout = vk::ImageLayout::eGeneral;
        }
        cmd.pipelineBarrier2({.imageMemoryBarrierCount = 4, .pImageMemoryBarriers = barriers.data()});
        scheduler.Finish();
        Fsr4Upscaler::Frame frame{};
        frame.color = {vk::Image(images[0]), *views[0], rw, rh, formats[0]};
        frame.depth = {vk::Image(images[1]), *views[1], rw, rh, formats[1]};
        frame.motion = {vk::Image(images[2]), *views[2], rw, rh, formats[2]};
        frame.output = {vk::Image(images[3]), *views[3], ow, oh, formats[3]};
        frame.render_width = rw; frame.render_height = rh; frame.hdr = hdr;
        frame.preset = rw == ow ? 0 : 1; frame.frame_ms = 16.6667f;
        frame.near_plane = .05f; frame.far_plane = 3000; frame.vertical_fov = 1.22f;
        frame.auto_exposure = true;
        frame.sharpen = std::getenv("BB_FSR411_COMPARE_SHARPEN") != nullptr;
        frame.sharpness = .5f;
        Fsr4Vk fsr_vk(instance, scheduler);
        Fsr411Native fsr_dx(instance, scheduler);
        auto query = Check(device.createQueryPoolUnique({.queryType = vk::QueryType::eTimestamp, .queryCount = 2}));
        const float period = instance.GetPhysicalDevice().getProperties().limits.timestampPeriod;
        std::vector<double> gpu_times, wall_times;
        for (int i = 0; i < count + 16; ++i) {
            frame.cmdbuf = scheduler.CommandBuffer(); frame.reset = i == 0;
            if (switch_preset) frame.preset = (i / 24) % 2 == 0 ? 1 : 2;
            if (vary) {
                // Alternate solid and patterned inputs on the GPU. No host-side staging
                // writes race with queued reads, and a stale cross-API input is visible.
                const vk::ImageMemoryBarrier2 writable{
                    .srcStageMask = vk::PipelineStageFlagBits2::eAllCommands,
                    .srcAccessMask = vk::AccessFlagBits2::eMemoryRead | vk::AccessFlagBits2::eMemoryWrite,
                    .dstStageMask = vk::PipelineStageFlagBits2::eTransfer,
                    .dstAccessMask = vk::AccessFlagBits2::eTransferWrite,
                    .oldLayout = vk::ImageLayout::eGeneral, .newLayout = vk::ImageLayout::eGeneral,
                    .srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
                    .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
                    .image = vk::Image(images[0]),
                    .subresourceRange = {vk::ImageAspectFlagBits::eColor,0,1,0,1}};
                frame.cmdbuf.pipelineBarrier2({.imageMemoryBarrierCount=1,.pImageMemoryBarriers=&writable});
                if (i & 1) {
                    const vk::ClearColorValue value{std::array<float,4>{float(i%13)/13.f,.25f,.75f,1.f}};
                    frame.cmdbuf.clearColorImage(vk::Image(images[0]),vk::ImageLayout::eGeneral,value,writable.subresourceRange);
                } else {
                    const vk::BufferImageCopy copy{.imageSubresource={vk::ImageAspectFlagBits::eColor,0,0,1},.imageExtent={rw,rh,1}};
                    frame.cmdbuf.copyBufferToImage(staging,vk::Image(images[0]),vk::ImageLayout::eGeneral,copy);
                }
                frame.jitter[0]=float(i%8)/8.f-.5f;
                frame.jitter[1]=float(i%7)/7.f-.5f;
            }
            if (vary_motion) {
                const vk::ImageMemoryBarrier2 writable{
                    .srcStageMask = vk::PipelineStageFlagBits2::eAllCommands,
                    .srcAccessMask = vk::AccessFlagBits2::eMemoryRead | vk::AccessFlagBits2::eMemoryWrite,
                    .dstStageMask = vk::PipelineStageFlagBits2::eTransfer,
                    .dstAccessMask = vk::AccessFlagBits2::eTransferWrite,
                    .oldLayout = vk::ImageLayout::eGeneral, .newLayout = vk::ImageLayout::eGeneral,
                    .srcQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
                    .dstQueueFamilyIndex = VK_QUEUE_FAMILY_IGNORED,
                    .image = vk::Image(images[2]),
                    .subresourceRange = {vk::ImageAspectFlagBits::eColor,0,1,0,1}};
                frame.cmdbuf.pipelineBarrier2({.imageMemoryBarrierCount=1,.pImageMemoryBarriers=&writable});
                const vk::ClearColorValue value{std::array<float,4>{
                    float(i%5-2)*.75f, float(i%7-3)*.25f, 0.f, 0.f}};
                frame.cmdbuf.clearColorImage(vk::Image(images[2]),vk::ImageLayout::eGeneral,value,writable.subresourceRange);
            }
            const auto start = std::chrono::steady_clock::now();
            // Native dispatch submits this buffer, so only the all-Vulkan path uses these timestamps.
            if (!native && !pipeline) { frame.cmdbuf.resetQueryPool(*query, 0, 2); frame.cmdbuf.writeTimestamp(vk::PipelineStageFlagBits::eTopOfPipe, *query, 0); }
            const bool ok = native ? fsr_dx.Record(frame, async) : fsr_vk.Record(frame);
            if (!ok) throw std::runtime_error(native ? fsr_dx.Error() : fsr_vk.Problem());
            if (!native && !pipeline) frame.cmdbuf.writeTimestamp(vk::PipelineStageFlagBits::eBottomOfPipe, *query, 1);
            if (pipeline) {
                if ((i + 1) % batch_size == 0) scheduler.Flush();
            }
            else scheduler.Finish();
            const double wall = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
            if (i >= 16) wall_times.push_back(wall);
            if (!native && !pipeline && i >= 16) {
                std::array<uint64_t, 2> results{};
                const auto result = device.getQueryPoolResults(*query, 0, 2, sizeof(results), results.data(), sizeof(uint64_t), vk::QueryResultFlagBits::e64 | vk::QueryResultFlagBits::eWait);
                if (result != vk::Result::eSuccess) throw std::runtime_error("timestamp readback failed");
                gpu_times.push_back((results[1] - results[0]) * double(period) / 1e6);
            }
        }
        cmd = scheduler.CommandBuffer();
        vk::MemoryBarrier2 ready{.srcStageMask = vk::PipelineStageFlagBits2::eAllCommands,
            .srcAccessMask = vk::AccessFlagBits2::eMemoryWrite, .dstStageMask = vk::PipelineStageFlagBits2::eTransfer,
            .dstAccessMask = vk::AccessFlagBits2::eTransferRead};
        cmd.pipelineBarrier2({.memoryBarrierCount = 1, .pMemoryBarriers = &ready});
        vk::BufferImageCopy read{.imageSubresource = {vk::ImageAspectFlagBits::eColor, 0, 0, 1}, .imageExtent = {ow, oh, 1}};
        cmd.copyImageToBuffer(vk::Image(images[3]), vk::ImageLayout::eGeneral, staging, read);
        scheduler.Finish();
        vmaInvalidateAllocation(instance.GetAllocator(), allocation, 0, VK_WHOLE_SIZE);
        float lo = INFINITY, hi = -INFINITY; size_t invalid = 0;
        const auto* halves = reinterpret_cast<const _Float16*>(data);
        uint64_t hash = 14695981039346656037ull;
        for (size_t b = 0; b < size_t(ow) * oh * 8; ++b) {
            hash ^= data[b]; hash *= 1099511628211ull;
        }
        std::printf("OUTPUT hash=%016llx pipeline=%d\n", (unsigned long long)hash, pipeline);
        for (size_t i = 0; i < size_t(ow) * oh; ++i) for (size_t c = 0; c < 3; ++c) {
            float value = float(halves[i * 4 + c]);
            invalid += !std::isfinite(value); lo = std::min(lo, value); hi = std::max(hi, value);
        }
        const auto mean = [](const auto& values) { return std::accumulate(values.begin(), values.end(), 0.) / values.size(); };
        std::printf("RESULT backend=%s render=%ux%u output=%ux%u color=%s frames=%d wall_ms=%.4f gpu_ms=%.4f min=%.6f max=%.6f nonfinite=%zu\n",
                    native ? (async ? "async" : "dx12") : "fsr4vk", rw,rh,ow,oh,hdr ? "hdr" : "ldr",count,mean(wall_times),gpu_times.empty() ? 0 : mean(gpu_times),lo,hi,invalid);
        if (const char* dump = std::getenv("BB_FSR411_BENCH_DUMP")) {
            std::ofstream file(dump, std::ios::binary); file.write(reinterpret_cast<const char*>(data), size_t(ow) * oh * 8);
        }
        vmaDestroyBuffer(instance.GetAllocator(), staging, allocation);
        if (invalid || hi - lo < .05f) throw std::runtime_error("output contains invalid or constant pixels");
        std::puts("PASS: production FSR 4.1.1 wrapper rendered finite nonconstant GPU output");
        return 0;
    } catch (const std::exception& e) { std::fprintf(stderr, "FAIL: %s\n", e.what()); return 1; }
}
