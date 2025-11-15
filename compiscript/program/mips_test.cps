// Archivo que prueba todas las funcionalidades del compilador

// =====================================================
// 1. OPERACIONES ARITMÉTICAS Y ASIGNACIONES
// Prueba: Precedencia de operadores, asignación de temporales
// =====================================================

let a: integer = 2 + 3 * 4;        // Precedencia: 2 + (3*4) = 14
let b: integer = 10 - a / 2;       // División: (10 - 14/2) = 3
let c: integer = (1 + 2) + (3 + 4); // Paréntesis: 3 + 7 = 10

print("Operaciones aritméticas: a=" + a + ", b=" + b + ", c=" + c);

// =====================================================
// 2. FUNCIONES SENCILLAS (SIN PARÁMETROS)
// Prueba: Prologo, epilogo, llamada simple, retorno
// =====================================================

function getFive(): integer {
    return 5;
}

function addOne(x: integer): integer {
    return x + 1;
}

let five: integer = getFive();      // Llamada sin parámetros
let six: integer = addOne(5);       // Llamada con parámetro
print("Funciones simples: five=" + five + ", six=" + six);

// =====================================================
// 3. LLAMADAS A FUNCIONES CON MÚLTIPLES PARÁMETROS
// Prueba: Paso de parámetros, stack frame, valores retorno
// =====================================================

function sum(a: integer, b: integer): integer {
    return a + b;
}

function multiply(a: integer, b: integer): integer {
    return a * b;
}

function compute(x: integer, y: integer): integer {
    let temp: integer = sum(x, y);      // Llamada interna
    return multiply(temp, 2);           // Otra llamada interna
}

let result1: integer = sum(3, 7);           // 3 + 7 = 10
let result2: integer = multiply(4, 5);      // 4 * 5 = 20
let result3: integer = compute(2, 3);       // ((2+3)*2) = 10
print("Múltiples parámetros: sum=" + result1 + ", mul=" + result2 + ", compute=" + result3);

// =====================================================
// 4. ESTRUCTURAS DE CONTROL: IF/ELSE
// Prueba: Saltos condicionales, ejecución de bloques
// =====================================================

function max(a: integer, b: integer): integer {
    if (a > b) {
        return a;
    } else {
        return b;
    }
}

let max1: integer = max(10, 7);      // 10
let max2: integer = max(3, 12);      // 12
print("If/else: max(10,7)=" + max1 + ", max(3,12)=" + max2);

// =====================================================
// 5. BUCLES WHILE
// Prueba: Etiquetas, saltos condicionales, iteración
// =====================================================

function factorial_iter(n: integer): integer {
    let result: integer = 1;
    let i: integer = 2;
    while (i <= n) {
        result = multiply(result, i);
        i = i + 1;
    }
    return result;
}

function sum_range(n: integer): integer {
    let total: integer = 0;
    let i: integer = 1;
    while (i <= n) {
        total = sum(total, i);
        i = i + 1;
    }
    return total;
}

let fact4: integer = factorial_iter(4);   // 4! = 24
let fact5: integer = factorial_iter(5);   // 5! = 120
let sum10: integer = sum_range(5);       // 1+2+3+4+5 = 15
print("While loops: 4!=" + fact4 + ", 5!=" + fact5 + ", sum(1..5)=" + sum10);

// =====================================================
// 6. RECURSIÓN SIMPLE
// Prueba: Stack management, llamadas recursivas
// =====================================================

function factorial_rec(n: integer): integer {
    if (n <= 1) {
        return 1;
    } else {
        return multiply(n, factorial_rec(n - 1));
    }
}

function fibonacci(n: integer): integer {
    if (n <= 1) {
        return n;
    } else {
        return sum(fibonacci(n - 1), fibonacci(n - 2));
    }
}

function count_digits(n: integer): integer {
    if (n < 10) {
        return 1;
    } else {
        return 1 + count_digits(n / 10);
    }
}

let fact4_rec: integer = factorial_rec(4);    // 24
let fib5: integer = fibonacci(5);             // 5
let fib6: integer = fibonacci(6);             // 8
let digits123: integer = count_digits(123);   // 3
let digits1000: integer = count_digits(1000); // 4
print("Funciones recursivas: 4!=" + fact4_rec + ", fib(5)=" + fib5 + ", fib(6)=" + fib6 + ", digits(123)=" + digits123);

// =====================================================
// 7. PROGRAMA PRINCIPAL Y VALIDACIÓN FINAL
// Prueba: Integración de todas las funcionalidades
// =====================================================

function main(): integer {
    // Test completo de todas las funcionalidades implementadas
    let total_tests: integer = 0;

    // Pruebas de aritmética (a=14, b=3, c=10)
    total_tests = sum(a, sum(b, c));  // 14 + 3 + 10 = 27

    // Pruebas de funciones simples
    total_tests = sum(total_tests, sum(five, six)); // +5 +6 = +11, total=38

    // Pruebas de llamadas múltiples
    total_tests = sum(total_tests, sum(result1, sum(result2, result3)));
    // +10 +20 +10 = +40, total=78

    // Pruebas de control de flujo
    total_tests = sum(total_tests, sum(max1, max2)); // +10 +12 = +22, total=100

    // Pruebas de bucles
    total_tests = sum(total_tests, sum(fact4, sum10)); // +24 +15 = +39, total=139

    // Pruebas de recursión
    total_tests = sum(total_tests, sum(fact4_rec, sum(fib5, fib6)));
    // +24 +5 +8 = +37, total=176

    // Pruebas adicionales de recursión
    total_tests = sum(total_tests, sum(digits123, digits1000));
    // +3 +4 = +7, total=183

    print("Tests totales: " + total_tests);
    return total_tests;
}

let final_result: integer = main();
print("Resultado final del compilador: " + final_result);

// =====================================================
// VALIDACIÓN ESPERADA:
// Si todas las funcionalidades están implementadas correctamente,
// el resultado debe ser 183.
// Verifica paso a paso:
//   27 (aritmética) + 11 (funciones) + 40 (llamadas) + 22 (if/else) + 39 (bucles) + 37 (recursión) + 7 (adicional) = 183
// =====================================================
