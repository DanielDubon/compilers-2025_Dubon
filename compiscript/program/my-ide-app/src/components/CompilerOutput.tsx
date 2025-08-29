import React from 'react';

interface CompilerOutputProps {
  output: string;
  errors: string;
}

const CompilerOutput: React.FC<CompilerOutputProps> = ({ output, errors }) => (
  <div style={{ marginTop: '20px', background: '#fff', padding: '10px', borderRadius: '4px', minHeight: '60px' }}>
    <h3>Salida del compilador:</h3>
    {output && <pre>{output}</pre>}
    {errors && (
      <pre style={{ color: 'red' }}>
        {errors}
      </pre>
    )}
  </div>
);

export default CompilerOutput;