// Example 3: Loop-invariant computation
// expensiveConstant() does not depend on the loop variable `i` at all,
// so it can be hoisted out of the loop and computed once.
// Sizes are deliberately kept small (3,000 inner iterations x 30,000 outer
// iterations = ~90 million operations, ~0.08s) so the demo runs in well
// under 1 second while still producing a clearly measurable (~97%) speedup
// once the call is hoisted out of the loop.
#include <iostream>
using namespace std;

int expensiveConstant() {
    long long acc = 0;
    for (int i = 0; i < 3000; i++) acc += i % 3;
    return (int)(acc % 1000);
}

int main() {
    int n = 30000;
    long long total = 0;
    for (int i = 0; i < n; i++) {
        total += expensiveConstant() + i;
    }
    cout << total << endl;
    return 0;
}
