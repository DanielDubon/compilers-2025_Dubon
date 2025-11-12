// program/test_calls.cps
function sum(a: integer, b: integer): integer {
  return a + b;
}

function main(): integer {
  let r: integer = 0;
  r = sum(2, 3);
  return r;
}
