import React, { useState } from 'react';
import Editor from './components/Editor';
import Toolbar from './components/Toolbar';
import CompilerOutput from './components/CompilerOutput';
import { compileCode } from './services/compilerService';

const App: React.FC = () => {
  const [code, setCode] = useState<string>(
    `let x = 10;\nlet y = 20;\nlet z = x + y;`
  );
  const [output, setOutput] = useState<string>('');
  const [errors, setErrors] = useState<string>('');

  const handleCompile = async () => {
    setOutput('');
    setErrors('');
    try {
      const result = await compileCode(code);
      setOutput(result.output);
      setErrors(result.errors);
    } catch (e) {
      setErrors('Error de conexión con el backend.');
    }
  };

  return (
    <div style={{
      padding: '20px',
      maxWidth: 800,
      margin: '0 auto',
      background: '#282a36', // fondo sublime
      minHeight: '100vh',
      fontFamily: "'Fira Mono', 'Menlo', 'Monaco', 'Consolas', monospace"
    }}>
      <h2>Compiscript IDE</h2>
      <Toolbar onCompile={handleCompile} />
      <Editor code={code} onChange={setCode} />
      <CompilerOutput output={output} errors={errors} />
    </div>
  );
};

export default App;