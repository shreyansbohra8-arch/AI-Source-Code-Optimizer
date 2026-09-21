// Example 5: Dead / unused code
// `unusedVariable` is never read, and the `cout` line after `return -1;`
// is unreachable.
#include <iostream>
using namespace std;

int main() {
    int unusedVariable = 42;
    long long sum = 0;
    for (int i = 0; i < 500000; i++) {
        sum += i;
        if (sum < 0) {
            return -1;
            cout << "unreachable" << endl;
        }
    }
    cout << sum << endl;
    return 0;
}
