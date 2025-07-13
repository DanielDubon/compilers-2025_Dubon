# Driver.py

## Descripción General

`Driver.py` es el archivo principal en Python que conecta el **lexer** y el **parser** generados con ANTLR para la gramática **MiniLang**. 

Su propósito es **analizar archivos de entrada** y verificar si cumplen con las reglas sintácticas definidas en `MiniLang.g4`.

---

## Funcionamiento

1️. Lee un archivo de texto de entrada (por ejemplo `program_test.txt`).  
2️. Usa **MiniLangLexer** para dividir el texto en **tokens**.  
3️. Usa **MiniLangParser** para aplicar las reglas de la gramática, comenzando desde la regla inicial `prog`.  
4️. Si la entrada es **correcta**, el programa no imprime errores.  
5️. Si hay **errores de sintaxis**, se muestran en consola.

---

# MiniLang.g4

## Descripción

Este archivo define la **gramática** para el lenguaje MiniLang usando ANTLR.  

Especifica **reglas léxicas** (tokens) y **reglas sintácticas** (estructura del lenguaje) para reconocer un lenguaje simple de expresiones y asignaciones.

---


