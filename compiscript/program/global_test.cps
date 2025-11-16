// Test Examples for Compiscript Compiler

// OPERACIONES ARITMÉTICAS Y ASIGNACIONES


let a: integer = 2 + 3 * 4;        // Precedencia: 2 + (3*4) = 14
let b: integer = 10 - a / 2;       // División: (10 - 14/2) = 3
let c: integer = (1 + 2) + (3 + 4); // Paréntesis: 3 + 7 = 10

print(a);
print(b);
print(c);

// Function to add two integers
function sum(a: integer, b: integer): integer {
    return a + b;
}

// Recursive factorial function
function factorial(n: integer): integer {
    if (n <= 1) {
        return 1;
    }
    return n * factorial(n - 1);
}

function main(): integer {
    // 1. Simple Variable Declarations and Assignments
    let x: integer = 10;
    let y: integer = 20;
    let z: integer = x + y;
    print(z); // Expected: 30

    // 2. Arithmetic Operations
    let a: integer = 10;
    let b: integer = 3;
    let c: integer = (a * 2) + (b * 3); // c = 20 + 9 = 29
    print(c); // Expected: 29
    let d: integer = a / b; // d = 10 / 3 = 3
    print(d); // Expected: 3
    let e: integer = a % b; // e = 10 % 3 = 1
    print(e); // Expected: 1

    // 3. If-Else Statement
    if (x < 15) {
        print(1); // Expected: 1
        if (y > 15) {
            print(2); // Expected: 2
        } else {
            print(99); // Not Expected
        }
    } else {
        print(98); // Not Expected
    }

    // 4. While Loop
    let i: integer = 0;
    while (i < 5) {
        if (i % 2 == 0) { // Check if i is even
            print(i); // Expected: 0, 2, 4
        }
        i = i + 1;
    }

    // 5. Function Call
    let result_sum: integer = sum(15, 25);
    print(result_sum); // Expected: 40

    // 6. Recursive Function Call (Factorial)
    let fact_4: integer = factorial(4); // 4 * 3 * 2 * 1 = 24
    print(fact_4); // Expected: 24
    let fact_0: integer = factorial(0); // Base case: 1
    print(fact_0); // Expected: 1

    return 0;
}
