# Compiscript — Parser + Semantica + AST

## Requisitos
- Docker con la imagen `csp-image`
- Python 3.10+ con `antlr4-python3-runtime` instalado

## Estructura del proyecto
```
program/
  Driver.py
  CompiscriptLexer.py
  CompiscriptParser.py
  PrettyErrorListener.py
  SemanticListener.py
  ast_builder.py
  ast_nodes.py
  treeutils.py
  program.cps
  tests/
    test_compiscript.py
```

## Ejecutar el analisis (lexico + sintaxis + semantica + AST)

### Con Docker (desde la carpeta `program/`)
```bash
docker run --rm -ti --user $(id -u):$(id -g) -v "$PWD":/program csp-image bash

python3 Driver.py program.cps
```

Se generan estos archivos:
- Parse tree: `parse_tree.txt`, `parse_tree.dot`
- AST: `ast.txt`, `ast.dot`

Render a PNG con Graphviz:
```bash
dot -Tpng parse_tree.dot -o parse_tree.png
dot -Tpng ast.dot -o ast.png
```

### Flags opcionales del Driver
```bash
python3 Driver.py program.cps --ast-dump --ast-dot
```
Si no se pasan las flags, igual se generan `ast.txt`, `ast.dot`, `parse_tree.txt` y `parse_tree.dot`.

## Ejecutar tests

### Dentro del contenedor (ubicado en `/program`)
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```


## Notas
- Si Graphviz avisa que el grafo es grande, igual genera el PNG escalado.  
- Los archivos `ast.*` y `parse_tree.*` se sobreescriben en cada corrida.
