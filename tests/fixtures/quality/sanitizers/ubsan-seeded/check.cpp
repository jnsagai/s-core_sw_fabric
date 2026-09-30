// Synthetic probe: signed overflow, for real local UBSan execution only.
int main() {
    volatile int value = 2147483647;
    return value + 1;
}
