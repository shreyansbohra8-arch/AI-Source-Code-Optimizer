// Example 4: Constant expression / constant propagation
// `a`, `b`, and `c` are all compile-time constants and could be folded.
#include <iostream>
using namespace std;

int main() {
    int a = 2 + 3;
    int b = a * 10;
    int c = 100 - 1;
    long long total = 0;
    for (int i = 0; i < 1000000; i++) {
        total += (a + b + c) % 5;
    }
    cout << total << endl;
    return 0;
}
