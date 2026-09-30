// Synthetic probe: heap-buffer overflow, for real local ASan execution only.
int main() {
    auto* values = new int[1];
    volatile int index = 1;
    values[index] = 42;
    delete[] values;
    return 0;
}
