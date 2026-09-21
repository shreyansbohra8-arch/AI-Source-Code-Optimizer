// Example 2: Redundant computation
// computeExpensive(42) is called with the SAME argument on every iteration,
// re-doing identical work each time.
#include <iostream>
#include <cmath>
using namespace std;

double computeExpensive(int x) {
    double result = 0;
    for (int i = 0; i < 500; i++) {
        result += sqrt((double)(x + i));
    }
    return result;
}

int main() {
    int n = 3000;
    double total = 0;
    for (int i = 0; i < n; i++) {
        total += computeExpensive(42) * i;
    }
    cout << total << endl;
    return 0;
}
