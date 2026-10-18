// SPDX-License-Identifier: GPL-2.0-or-later
#pragma once
#include <cstdint>
#include <string>
#include <string_view>
struct Fg401Support {
    bool supported{};
    std::string reason;
};
inline bool IsRx9000(uint32_t vendor, std::string_view name) {
    if (vendor != 0x1002)
        return false;
    const auto pos = name.find("RX 9");
    if (pos == std::string_view::npos || pos + 7 > name.size())
        return false;
    for (size_t i = pos + 3; i < pos + 7; ++i)
        if (name[i] < '0' || name[i] > '9')
            return false;
    return pos + 7 == name.size() || name[pos + 7] == ' ';
}
bool Fg401WindowsSupported();
Fg401Support ProbeFg401(const uint8_t luid[8]);
