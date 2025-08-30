// Global constants and variables
const PI: integer = 314;
let greeting: string = "Hello, Compiscript!";
let flag: boolean;
let numbers: integer[] = [1, 2, 3, 4, 5];
let matrix: integer[][] = [[1, 2], [3, 4]];

// Simple closure-style function (no nested type signatures)
function makeAdder(x: integer): integer {
  return x + 1;
}

let addFive: integer = (makeAdder(5));
print("5 + 1 = " + addFive);

// Control structures
if (addFive > 5) {
  print("Greater than 5");
} else {
  print("5 or less");
}

while (addFive < 10) {
  addFive = addFive + 1;
}

do {
  print("Result is now " + addFive);
  addFive = addFive - 1;
} while (addFive > 7);

for (let i: integer = 0; i < 3; i = i + 1) {
  print("Loop index: " + i);
}

foreach (n in numbers) {
  if (n == 3) {
    continue;
  }
  print("Number: " + n);
  if (n > 4) {
    break;
  }
}

// Switch-case structure
switch (addFive) {
  case 7:
    print("It's seven");
  case 6:
    print("It's six");
  default:
    print("Something else");
}

// Try-catch structure
try {
  let risky: integer = numbers[10];
  print("Risky access: " + risky);
} catch (err) {
  print("Caught an error: " + err);
}

// Class definition and usage
class Animal {
  let name: string;

  function constructor(name: string) {
    this.name = name;
  }

  function speak(): string {
    return this.name + " makes a sound.";
  }
}

class Dog : Animal {
  function speak(): string {
    return this.name + " barks.";
  }
}

let dog: Dog = new Dog("Rex");
print(dog.speak());

// Object property access and array indexing
let first: integer = numbers[0];
print("First number: " + first);

// Function returning an array
function getMultiples(n: integer): integer[] {
  let result: integer[] = [n * 1, n * 2, n * 3, n * 4, n * 5];
  return result;
}

let multiples: integer[] = getMultiples(2);
print("Multiples of 2: " + multiples[0] + ", " + multiples[1]);

// Recursion
function factorial(n: integer): integer {
  if (n <= 1) {
    return 1;
  }
  return n * factorial(n - 1);
}


// Aritmética
let a: integer = 2 + 3 * 4;
let bnum = 10 - a / 2;

// Lógicas
let c: boolean = true && (false || !false);

// Comparaciones
let d: boolean = a == 8;
let e: boolean = a < bnum;

// Asignación (inferencia y chequeo)
let x;        // desconocido
x = 5;        // infiere integer
// x = "hola";   // ERROR: tipo incompatible

const K: integer = 7;
// K = 8;     // ERROR: const no reasignable

// Arreglos
let v: integer[] = [1, 2, 3];
let y = v[0];               // ok
let s: string = "num: " + a; // concatenacion string+integer OK


function f(): integer { return 1; }
// function f(): integer { return 2; } //  ERRORRR

class A {
  let name: string;
  function constructor(name: string) { this.name = name; }
  function speak(): string { return this.name + " habla"; }
}

class B : A {
  function shout(): string { return this.name + "!!!"; }
}

let b: B = new B("Rex");
print(b.speak()); // OK (de A)
print(b.shout()); // OK (de B)


class A2 {
  function constructor(x: integer) {}
}

class B2 : A2 {}

//let b2: B2 = new B2(); // ERROR falta 1 arg


class A3 {
  function constructor(name: string) {}
}
class B3 : A3 {}

//let b3: B3 = new B3(123); // Error int en lugar de string

class A4 { let ok: integer; function constructor() { this.ok = 1; } }
class B4 : A4 {}

let b4: B4 = new B4();
//print(b4.missing); // Error

class A5 { function constructor() {} }
class B5 : A5 {}

let b5: B5 = new B5();
//b5.meow(); // Error


class A6 { function constructor() {} function ping(): integer { return 1; } }
class B6 : A6 {}

let b6: B6 = new B6();
//let m = b6.ping; // ERROR falta '()'


class A7 {
  function constructor() {}
  function dup(n: integer): integer { return n + n; }
}
class B7 : A7 {}

let b7: B7 = new B7();
//b7.dup();       // Error aridad 0/1
//b7.dup("hola"); // Error tipo string/integer


//this.name; // Error fuera de clase


let notObj: integer = 1 + 2;
// notObj.foo; // Error no objeto sin dato...

let arr: integer[] = [1,2,3];
//let _a = arr["0"]; // Error indice string
let notArr: integer = 123;
//let _b = notArr[0];   // Error indexar no-arreglo









// Funcion con retornos en todos los caminos
function calcularDescuento(total: integer): integer {
  if (total > 100) {
    return 10;
    //print("no llega"); // ERROR AQUI SI SE DESCOMENTA
  }
  return 0;
}

let subtotalCompra: integer = 150;
let descuentoAplicado: integer = calcularDescuento(subtotalCompra);
print("Descuento aplicado: " + descuentoAplicado);

// Clase simple con constructor y método
class Factura {
  let cliente: string;
  let monto: integer;

  function constructor(cliente: string, monto: integer) {
    this.cliente = cliente;
    this.monto = monto;
  }

  function resumen(): string {
    return "Cliente " + this.cliente + ", monto " + this.monto;
  }
}

let fac: Factura = new Factura("ACME S.A.", 250);
print(fac.resumen());

// foreach con arreglo de strings
let empleados: string[] = ["Ana", "Luis", "María"];
foreach (persona in empleados) {
  print("Empleado: " + persona);
}

// Llamada a método heredado + método propio para verificar lookup
class Vehiculo {
  let marca: string;
  function constructor(marca: string) { this.marca = marca; }
  function etiqueta(): string { return "Vehiculo " + this.marca; }
}

class Moto : Vehiculo {
  function rodar(): string { return this.marca + " en marcha"; }
}

let m: Moto = new Moto("Yamaha");
print(m.etiqueta()); // de Vehiculo
print(m.rodar());    // de Moto

// Ternario bien tipado
let umbral: integer = 50;
let estado: string = (subtotalCompra > umbral) ? "APROBADO" : "PENDIENTE";
print("Estado de compra: " + estado);

// Switch bien tipeado
switch (descuentoAplicado) {
  case 0:
    print("Sin descuento");
  case 10:
    print("Descuento estándar");
  default:
    print("Descuento desconocido");
}


let test: integer = 2;
switch (test) {
 // case false: print("no debería permitir"); // deberia chiar con incompatibilidad (si chio ggs)
  case 2: print("ok");
}









// ----- testt
var gv: integer = 10;
const G: integer = 1;

function outer(a: integer): void {
    var x: integer = 1;
    const c: integer = 5;

    function inner1(b: integer): void {
        print(a + x + b + gv + G);
        gv = gv + 1;  // ok
      //  c = 7;        //  error esperado que se intenta reasign const
    }

    function inner2(): void {
        x = x + 1;    // ok: captura y asigna
    }

    function inner3(): void {
        var x: integer = 0; // sombreado local, no captura x externo
        print(x + a);       // captura a
    }

    inner1(10);
    inner2();
    inner3();
}

function level1(): void {
    var a: integer = 1;
    function level2(): void {
        var b: integer = 2;
        function level3(): void {
            print(a + b); 
        }
        level3();
    }
    level2();
}


//test unreacheable
function deadasd(): integer {
  if (true) { return 1; }
  //let z = 3;  // aqui deberia de chiar que nunca llegara ya chio
  //return z;
}




// Program end
print("Program finished.");
