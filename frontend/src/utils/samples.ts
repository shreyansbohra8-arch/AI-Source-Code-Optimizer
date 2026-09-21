export interface SampleProgram {
  name: string;
  code: string;
}

export const SAMPLE_PROGRAMS: SampleProgram[] = [
  {
    name: "Nested loops (pair sum)",
    code: `#include <iostream>
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
`,
  },
  {
    name: "Redundant computation in loop",
    code: `#include <iostream>
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
`,
  },
  {
    name: "Loop invariant call",
    code: `#include <iostream>
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
`,
  },
  {
    name: "Constant expression / propagation",
    code: `#include <iostream>
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
`,
  },
  {
    name: "Dead / unused code",
    code: `#include <iostream>
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
`,
  },
];
