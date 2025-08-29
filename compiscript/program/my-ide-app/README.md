# IDE App
The implemented IDE App is a simple Integrated Development Environment (IDE) built with React and TypeScript. It allows users to write, compile, and manage their code efficiently. The application features a code editor, compilation output display, and a toolbar for various actions.

## Features

- **Code Editor**: A text area for users to write their code with syntax highlighting.
- **Compilation Output**: Displays the results of the compilation process, including errors and output.
- **Toolbar**: Contains buttons for compiling code, saving files, and other functionalities.
- **File Management**: Utility functions for saving and loading code files from the local filesystem.

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
This will launch the IDE in your default web browser.
