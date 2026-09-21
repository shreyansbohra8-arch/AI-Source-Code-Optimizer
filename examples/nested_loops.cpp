// Example 1: Nested loops
// Demonstrates O(n^2) behavior counting pairs (i, j) whose sum is divisible by 7.
#include <iostream>
using namespace std;

int main() {
    int n = 2000;
    long long count = 0;
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < n; j++) {
            if ((i + j) % 7 == 0) {
                count++;
            }
        }
    }
    cout << count << endl;
    return 0;
}
