
# Compiscript IDE App
This is a modern Integrated Development Environment (IDE) for Compiscript, built with React and TypeScript. It allows users to write, compile, and manage Compiscript code efficiently. The application features a Sublime Text-style code editor with syntax highlighting, compilation output display, and a toolbar for actions.


## Features

- **Sublime Text-style Code Editor**: Write code with line numbers and syntax highlighting for keywords, numbers, strings, booleans (orange), and comments (verde).
- **Compilation Output**: Displays the results of the compilation process, including errors and output, with colorized error messages.
- **Toolbar**: Contains a button for compiling code.
- **Backend Integration**: Communicates with a Python/Flask backend that runs the Compiscript compiler and returns output/errors.


## Project Structure

```
my-ide-app
├── src
│   ├── components
│   │   ├── Editor.tsx
│   │   ├── CompilerOutput.tsx
│   │   └── Toolbar.tsx
│   ├── services
│   │   └── compilerService.ts
│   ├── utils
│   │   └── fileUtils.ts
│   ├── App.tsx
│   └── index.tsx
├── public
│   └── index.html
├── package.json
├── tsconfig.json
└── README.md
```


## Installation

1. Clone the repository:
   ```
   git clone <repository-url>
   ```
2. Navigate to the project directory:
   ```
   cd my-ide-app
   ```
3. Install the dependencies:
   ```
   npm install
   ```


## Usage

To start the application, run:
```
npm start
```
This will launch the IDE in your default web browser at http://localhost:3000.

Make sure the backend server (Flask, `server.py`) is running in the `compiscript/program` directory:
```
python3 server.py
```

## Syntax Highlighting Example

```js
let a = true; // boolean resaltado en naranja
let b = 123;  // número resaltado
let s = "texto"; // string resaltado
// comentario en verde
if (a) {
   print(b);
}
```
