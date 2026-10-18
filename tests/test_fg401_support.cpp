#include "fg401_support.h"
#include <cassert>
#include <cstdio>
int main() {
    assert(IsRx9000(0x1002, "AMD Radeon RX 9070"));
    assert(IsRx9000(0x1002, "AMD Radeon RX 9070 XT"));
    assert(IsRx9000(0x1002, "AMD Radeon RX 9060 XT"));
    assert(!IsRx9000(0x1002, "AMD Radeon RX 7900 XTX"));
    assert(!IsRx9000(0x1002, "AMD Radeon RX 6900 XT"));
    assert(!IsRx9000(0x10de, "AMD Radeon RX 9070"));
    assert(!IsRx9000(0x8086, "Intel Arc B580"));
    assert(!IsRx9000(0x1002, "AMD Radeon RX 907"));
    assert(!IsRx9000(0x1002, "AMD Radeon RX 90700"));
    assert(!IsRx9000(0x1002, "AMD Radeon RX 9abc"));
    std::puts("PASS RX 9000 allowlist and vendor/generation rejection");
}
