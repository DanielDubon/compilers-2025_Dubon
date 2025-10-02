// Global Declarations
const MAX_VALUE: integer = 100;
let globalCounter: integer = 0;
let message: string = "Hello from global!";
let isActive: boolean = true;
let emptyVar; // Variable sin inicializador, su tipo se inferirá o será 'unknown'

// Function Declaration: calculateSum
// Con parámetros y retorno, y una variable local
function calculateSum(a: integer, b: integer): integer {
    let localResult: integer = a + b;
    return localResult; // Aún no implementamos 'return', pero la estructura estará
}

// Function Declaration: countdown
// Con un bucle while y llamadas a print
function countdown(start: integer): void {
    let current: integer = start;
    while (current > 0) {
        print("Counting down: " + current);
        current = current - 1;
    }
    print("Countdown finished!");
}

// Main logic starts here
print(message); // Uso de variable global y literal string

// Arithmetic expressions and assignments
let x: integer = 5;
let y: integer = 10;
let z: integer = (x + y) * 2 - 3; // (5+10)*2 - 3 = 15*2 - 3 = 30 - 3 = 27
print("Result of z: " + z);

// If-else statement
if (z > 20) { // Condición con expresión relacional (aún no implementada, pero el AST la tendrá)
    print("z is greater than 20.");
    let tempMsg: string = "Inside if block.";
    print(tempMsg);
} else {
    print("z is 20 or less.");
}

// Simple if statement
if (isActive) { // Condición con variable booleana
    print("System is active.");
}

// While loop
let loopVar: integer = 3;
while (loopVar > 0) { // Condición con expresión relacional
    print("Loop iteration: " + loopVar);
    loopVar = loopVar - 1;
}

// Function calls
let sumResult: integer = calculateSum(x, y); // calculateSum(5, 10) = 15
print("Sum result: " + sumResult);

countdown(2); // Llamada a la función countdown

// Uso de literal null
let myNull: null = null;
// print(myNull); // Descomentar para probar si 'print' maneja null o da error

// --- Ejemplos de errores semánticos (descomentar para probar la captura de errores) ---

// let x: integer = 1; // ERROR: Redeclaración de 'x'
// let invalidAssign: integer = "hello"; // ERROR: Tipo incompatible en asignación

print("Program finished.");
